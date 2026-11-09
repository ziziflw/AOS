"""Owned loopback-only HTTP provider fixture. No inference, credentials or remote calls."""
import json,socket,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from boot import write

class Fixture:
    def __init__(self,directory):
        self.dir=Path(directory);self.dir.mkdir(parents=True,exist_ok=True);self.rows=[];self.lock=threading.Lock();self.active=0;self.peak=0
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                size=int(self.headers.get('Content-Length','0'))
                if size<=0 or size>32768:self.send_error(413);return
                body=json.loads(self.rfile.read(size));mode=body.get('model','').split('-')[-1]
                with owner.lock:
                    owner.active+=1;owner.peak=max(owner.peak,owner.active)
                    owner.rows.append({'sequence':len(owner.rows)+1,'path':self.path,'body':body,
                      'authorizationPresent':bool(self.headers.get('Authorization') or self.headers.get('x-api-key')),
                      'mode':mode,'receivedAt':time.time()});owner.save()
                try:
                    if mode=='delay':time.sleep(2.5)
                    if mode=='lost':time.sleep(.05)
                    if mode=='slow':time.sleep(.15)
                    if mode=='lost':self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
                    if mode in ('rate','error','secret'):
                        status=429 if mode=='rate' else 400
                        self.reply(status,{'type':'error','error':{'type':'rate_limit_error' if status==429 else 'invalid_request_error','message':'fixture rejection '+('fixture-secret-do-not-display' if mode=='secret' else '')}});return
                    text='离线 HTTP 合成响应'
                    if mode in ('json','badjson'):text=json.dumps({'answer':'离线结构化响应'} if mode=='json' else {'wrong':7},ensure_ascii=False)
                    if mode=='leak':text=self.headers.get('Authorization','').removeprefix('Bearer ') or self.headers.get('x-api-key','')
                    if self.path=='/v1/chat/completions':
                        res={'id':'chatcmpl-fixture','object':'chat.completion','created':1,'model':body['model'],
                             'choices':[{'index':0,'message':{'role':'assistant','content':text},'finish_reason':'stop'}]}
                        if mode!='missing':res['usage']={'prompt_tokens':12,'completion_tokens':7,'total_tokens':19}
                        if mode=='large':res['usage']={'prompt_tokens':900,'completion_tokens':100,'total_tokens':1000}
                    elif self.path=='/v1/messages':
                        res={'id':'msg_fixture','type':'message','role':'assistant','model':body['model'],
                             'content':[{'type':'text','text':text}],'stop_reason':'end_turn','stop_sequence':None,
                             'usage':{'input_tokens':12,'output_tokens':7}}
                        if mode=='missing':res.pop('usage')
                    else:self.reply(404,{'error':{'message':'fixture endpoint only','type':'invalid_request_error'}});return
                    self.reply(200,res)
                except (BrokenPipeError,ConnectionResetError,OSError):pass
                finally:
                    with owner.lock:owner.active-=1;owner.save()
            def reply(self,status,value):
                data=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True
        self.url='http://127.0.0.1:'+str(self.server.server_port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def save(self):write(self.dir/'http-ledger.json',{'synthetic':True,'requests':self.rows,'peakConcurrent':self.peak})
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(2)
