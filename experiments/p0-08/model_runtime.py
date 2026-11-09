"""C1 profile extension only: admission/settlement, original scheduler and SQLite authority."""
import math,time
from copy import deepcopy
from boot import ContractError,OutcomeError
from integration import BoundRuntime
from model_profile import MODELS

class ModelRuntime(BoundRuntime):
    def _validate_environment(self):
        # D2 validates unchanged original bindings. Model services are fixed process-owned HTTP fixtures.
        original=self.c.w['environmentRequirements']
        try:
            self.c.w['environmentRequirements']=[r for r in original if r['slot'] not in MODELS]
            super()._validate_environment()
        finally:self.c.w['environmentRequirements']=original
        for r in original:
            if r['slot'] in MODELS:
                if r['permissions']!=['synthetic:model-http']:raise ContractError('MODEL_PERMISSION_DENIED')
                b=self.environment['services'].get(r['slot']);ad=self.c.adapters[(r['adapter']['id'],r['adapter']['version'])]
                if not b or b['adapter']!=r['adapter'] or b['target']!=ad['capability']['selector']:raise ContractError('MODEL_BINDING_MISMATCH')
                if self.environment['connections'].get(b['connectionRef'])!={'transport':'cli','programRef':'program:aos-p08-executor','environmentRefs':[]}:raise ContractError('MODEL_CONNECTION_DENIED')
                if self.environment['credentials'].get(b['credentialRef'])!={'vaultAlias':'aos:p08:owned-fixture','status':'configured'}:raise ContractError('MODEL_CREDENTIAL_BINDING_DENIED')
    def _reserve(self,key):
        if self.spec(key)['typeId'] not in MODELS:return super()._reserve(key)
        n=self.spec(key);cfg=n['config'];_,inputs=self._dependencies(key)
        # Offline admission ceiling; not represented as a universal supplier tokenizer.
        if len(inputs['in'].encode('utf-8'))+128>cfg['maxInputTokens']:raise OutcomeError('MODEL_INPUT_ADMISSION_LIMIT')
        amount=cfg['maxInputTokens']+cfg['maxOutputTokens'];money=cfg['maxCallCostMinor']
        if math.ceil(amount/100)>money:raise OutcomeError('MODEL_CALL_COST_CEILING_INSUFFICIENT')
        u=self._state['usage'];w=self.c.w['executionPolicy']['budget'];local=n['policy']['budget']
        costs=self._state.get('modelCosts',{'estimatedMinor':0,'reservedMinor':0})
        if amount>local.get('maxTokens',0) or u['spentTokens']+u['reservedTokens']+amount>w.get('maxTokens',0):raise OutcomeError('TOKEN_BUDGET_EXCEEDED')
        if money>local.get('maxCostMinor',0) or costs['estimatedMinor']+costs['reservedMinor']+money>w.get('maxCostMinor',0):raise OutcomeError('COST_BUDGET_EXCEEDED')
        if w.get('currency')!='CNY' or local.get('currency')!='CNY':raise OutcomeError('CURRENCY_UNSUPPORTED')
        return amount
    def _change(self,kind,fn=None,**details):
        key=details.get('key')
        if kind=='node-dispatched' and key and self.spec(key)['typeId'] in MODELS:
            prior=fn
            def with_reservation(s):
                prior(s);n=s['nodes'][key];a=n['attempts'][-1]
                money=self.spec(key)['config']['maxCallCostMinor'];a['reservedCostMinor']=money
                s.setdefault('modelCosts',{'estimatedMinor':0,'reservedMinor':0,'currency':'CNY','pricing':'synthetic-1-minor-per-100-tokens','invoiceVerified':False})['reservedMinor']+=money
            fn=with_reservation
        return super()._change(kind,fn,**details)
    def _validate_usage(self,key,out):
        if self.spec(key)['typeId'] not in MODELS:return super()._validate_usage(key,out)
        cfg=self.spec(key)['config'];u=out.model_usage
        if u and (u['inputTokens']>cfg['maxInputTokens'] or u['outputTokens']>cfg['maxOutputTokens']):raise ContractError('MODEL_USAGE_CEILING_BREACH')
    def _terminal(self,key,state,*,outputs=None,result=None,error=None,usage_tokens=0,usage_cost=0):
        n=self._state['nodes'][key]
        if self.spec(key)['typeId'] not in MODELS or not n['attempts']:
            return super()._terminal(key,state,outputs=outputs,result=result,error=error,usage_tokens=usage_tokens,usage_cost=usage_cost)
        attempt=n['attempts'][-1]
        if attempt['state'] not in ('running','cancel-requested'):raise ContractError('MODEL_ATTEMPT_ALREADY_SETTLED')
        observation=self.registry.d1.observations.get(attempt['id'],{})
        actual=observation.get('usage');cfg=self.spec(key)['config']
        valid=actual is not None and actual['inputTokens']<=cfg['maxInputTokens'] and actual['outputTokens']<=cfg['maxOutputTokens']
        confirmed=sum(actual.values()) if actual else 0
        cost=math.ceil(confirmed/100) if actual else 0
        if state=='cancelled':state='unknown'
        def finish(s):
            record=s['nodes'][key];a=record['attempts'][-1];u=s['usage'];costs=s['modelCosts']
            record.update(state=state,phase=state)
            if outputs is not None:record['outputs']=deepcopy(outputs)
            if result is not None:record['result']=deepcopy(result)
            if error is not None:record['error']=deepcopy(error)
            a.update(state=state,finishedAt=time.time(),usageTokens=confirmed,modelUsage=actual,
                     consumption='confirmed-fixture' if valid else 'unverified',invoiceVerified=False,
                     heldTokens=0 if valid else a['reservedTokens'],heldCostMinor=0 if valid else a['reservedCostMinor'])
            if error:a['error']=deepcopy(error)
            # Missing usage keeps the entire reservation. No zero-consumption inference.
            if valid:
                u['reservedTokens']-=a['reservedTokens'];costs['reservedMinor']-=a['reservedCostMinor']
            u['spentTokens']+=confirmed
            costs['estimatedMinor']+=cost
            record['modelUsage']=actual;record['estimatedCostMinor']=cost if actual else None
        self._change('node-terminal',finish,key=key,old=n['state'],state=state,attemptId=attempt['id'],error=error)
