"""D1 uses official SDKs for HTTP, serialization, parsed objects and typed errors."""
import asyncio,json
from dataclasses import dataclass
import openai,anthropic,httpx2
from boot import ContractError,OutcomeError
from model_profile import MODELS
from mocks import Result

@dataclass
class ModelResult(Result):
    model_usage:dict|None=None

class ModelAdapter:
    def __init__(self,fixture,vault,alias):self.fixture,self.vault,self.alias=fixture,vault,alias;self.observations={}
    async def invoke(self,ctx):
        cap=MODELS[ctx.node['typeId']];c=ctx.node['config'];key=self.vault.resolve(self.alias)
        # Only this process-created server is reachable. No caller-provided base URL, proxy or redirects.
        client_args={'api_key':key,'base_url':self.fixture.url+('/v1' if cap['provider']=='openai' else ''),'max_retries':0,'timeout':1.2,
          'http_client':httpx2.AsyncClient(trust_env=False,follow_redirects=False)}
        cls=openai.AsyncOpenAI if cap['provider']=='openai' else anthropic.AsyncAnthropic
        async def call():
            async with cls(**client_args) as client:
                args={'model':c['model'],'messages':[{'role':'user','content':ctx.inputs['in']}]}
                if cap['provider']=='openai':
                    args.update(max_completion_tokens=c['maxOutputTokens'],temperature=c['temperature'])
                    if cap['structured']:args['response_format']={'type':'json_schema','json_schema':{'name':'answer','strict':True,'schema':{'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False}}}
                    r=await client.chat.completions.create(**args);text=r.choices[0].message.content
                    u=r.usage;usage={'inputTokens':u.prompt_tokens,'outputTokens':u.completion_tokens} if u else None
                else:
                    args['max_tokens']=c['maxOutputTokens']
                    if cap['structured']:args['output_config']={'format':{'type':'json_schema','schema':{'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False}}}
                    r=await client.messages.create(**args);text=''.join(v.text for v in r.content if v.type=='text')
                    u=r.usage;usage={'inputTokens':u.input_tokens,'outputTokens':u.output_tokens} if u else None
                if usage and any(type(v) is not int or v<0 for v in usage.values()):raise ContractError('MODEL_USAGE_INVALID')
                # Keep actual usage even if subsequent output/schema validation fails.
                self.observations[ctx.attempt_id]={'usage':usage,'responseReceived':True}
                if key in text or 'fixture-secret-' in text:raise ContractError('MODEL_SECRET_OUTPUT_REJECTED')
                try:value=json.loads(text) if cap['structured'] else text
                except (ValueError,TypeError):raise ContractError('MODEL_JSON_INVALID') from None
                return ModelResult({'out':value},usage_tokens=sum(usage.values()) if usage else 0,model_usage=usage)
        task=asyncio.create_task(call());cancel=asyncio.create_task(ctx.cancel.wait())
        try:
            done,_=await asyncio.wait([task,cancel],return_when=asyncio.FIRST_COMPLETED)
            if cancel in done:
                task.cancel();await asyncio.gather(task,return_exceptions=True)
                raise OutcomeError('MODEL_CANCEL_REMOTE_UNCONFIRMED',side_effect='unknown')
            return await task
        except (openai.APIStatusError,anthropic.APIStatusError) as exc:
            status=exc.status_code
            # Explicit fixture 4xx has no usage; reserve conservatively, never serialize SDK body/headers.
            raise OutcomeError('MODEL_RATE_LIMIT' if status==429 else 'MODEL_HTTP_'+str(status),side_effect='not-started') from None
        except (openai.APIConnectionError,anthropic.APIConnectionError):
            raise OutcomeError('MODEL_TRANSPORT_RESULT_UNKNOWN',side_effect='unknown') from None
        except asyncio.CancelledError:
            raise OutcomeError('MODEL_INTERRUPTED_RESULT_UNKNOWN',side_effect='unknown') from None
        except (ContractError,OutcomeError):raise
        except Exception:
            raise OutcomeError('MODEL_RESPONSE_INVALID',side_effect='unknown') from None
        finally:
            cancel.cancel()
            if not task.done():task.cancel()
            await asyncio.gather(task,cancel,return_exceptions=True)
