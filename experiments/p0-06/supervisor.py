"""Experiment-owned external Agent analogue; independent from the Rust/engine Job."""
from pathlib import Path
import sys,os,asyncio,subprocess
import win32job
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'p0-05'));sys.path.insert(0,str(HERE.parent/'p0-03'))
from service_host import ServiceHost,alive
from common import ContractError,read,write
class ExternalAgent(ServiceHost):
    def __init__(self,directory,name='agentA'):
        self.dir=Path(directory).resolve();self.name=name;self.bad_card=False;self.job=None;self.process=None;self.endpoint=None;self.closed=False;self.pids=[]
        if not self.dir.is_relative_to(HERE/'evidence'):raise ContractError('SERVICE_PATH_DENIED')
        if name!='agentA':raise ContractError('SERVICE_NAME_DENIED')
        self.dir.mkdir(parents=True,exist_ok=True)
    async def start(self):
        self.job=win32job.CreateJobObject(None,'')
        info=win32job.QueryInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation);info['BasicLimitInformation']['LimitFlags']|=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation,info)
        command=[str(HERE/'.venv/Scripts/python.exe'),'-B','-X','utf8',str(HERE/'agent_server_entry.py'),'--directory',str(self.dir),'--name',self.name,'--port','0']
        self.log=(self.dir/'server.log').open('ab');env={k:os.environ[k] for k in ('SYSTEMROOT','WINDIR','TEMP','TMP') if k in os.environ}
        env.update(PYTHONUTF8='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
        try:
            self.process=subprocess.Popen(command,stdout=self.log,stderr=self.log,stdin=subprocess.DEVNULL,env=env,cwd=HERE,creationflags=subprocess.CREATE_NO_WINDOW)
            win32job.AssignProcessToJobObject(self.job,int(self.process._handle));self.pids.append(self.process.pid)
            from bootstrap_agent import jsonl
            jsonl(self.dir/'process.jsonl',{'kind':'started','launcherPid':self.process.pid,'command':command,'jobKillOnClose':True})
            (self.dir/'launch-gate').write_text('external test supervisor',encoding='ascii')
            for _ in range(800):
                if (self.dir/'ready.json').exists():
                    ready=read(self.dir/'ready.json');self.endpoint=ready['endpoint'];self.pids.append(ready['pid'])
                    import win32api,win32con
                    h=win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION,False,ready['pid'])
                    try:assigned=win32job.IsProcessInJob(h,self.job)
                    finally:h.Close()
                    if not assigned:raise ContractError('EXTERNAL_AGENT_NOT_OWNED')
                    jsonl(self.dir/'process.jsonl',{'kind':'ready','actualInJob':True,**ready});return self
                if self.process.poll() is not None:raise ContractError('SERVICE_START_FAILED')
                await asyncio.sleep(.01)
            raise ContractError('SERVICE_START_TIMEOUT')
        except BaseException:await self.stop();raise
