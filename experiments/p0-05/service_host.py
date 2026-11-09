"""Test-owned service supervisor, deliberately independent of workflow process lifetime."""
import asyncio,os,subprocess
from pathlib import Path
import win32api,win32con,win32process,win32job
from bootstrap_agent import HERE,read,write,jsonl,ContractError
def alive(pid):
    try:
        handle=win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION,False,pid)
        try:return win32process.GetExitCodeProcess(handle)==259
        finally:handle.Close()
    except Exception:return False
class ServiceHost:
    def __init__(self,directory,name='agentA',bad_card=False):
        self.dir=Path(directory).resolve();self.name=name;self.bad_card=bad_card;self.job=None;self.process=None;self.endpoint=None;self.closed=False;self.pids=[]
        if not self.dir.is_relative_to(HERE/'evidence'):raise ContractError('SERVICE_PATH_DENIED')
        if name not in ('agentA','agentB'):raise ContractError('SERVICE_NAME_DENIED')
        self.dir.mkdir(parents=True,exist_ok=True)
    async def start(self):
        if os.name!='nt':raise ContractError('WINDOWS_NOT_VERIFIED')
        port=int(self.endpoint.rsplit(':',1)[1]) if self.endpoint else 0
        for file in ('launch-gate','ready.json'):
            target=self.dir/file
            if target.exists():target.unlink()
        self.job=win32job.CreateJobObject(None,'')
        info=win32job.QueryInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation)
        info['BasicLimitInformation']['LimitFlags']|=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation,info)
        command=[str(HERE/'.venv/Scripts/python.exe'),'-B','-X','utf8',str(HERE/'agent_service.py'),'--directory',str(self.dir),'--name',self.name,'--port',str(port)]
        if self.bad_card:command.append('--bad-card')
        env={k:os.environ[k] for k in ('SYSTEMROOT','WINDIR','TEMP','TMP') if k in os.environ};env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
        self.log=(self.dir/'server.log').open('ab')
        try:
            self.process=subprocess.Popen(command,cwd=HERE,env=env,stdin=subprocess.DEVNULL,stdout=self.log,stderr=self.log,creationflags=subprocess.CREATE_NO_WINDOW)
            win32job.AssignProcessToJobObject(self.job,int(self.process._handle));self.pids.append(self.process.pid)
            jsonl(self.dir/'process.jsonl',{'kind':'started','launcherPid':self.process.pid,'command':command,'jobKillOnClose':True})
            (self.dir/'launch-gate').write_text('supervised',encoding='ascii')
            for _ in range(1000):
                if (self.dir/'ready.json').exists():
                    ready=read(self.dir/'ready.json');self.endpoint=ready['endpoint'];self.pids.append(ready['pid'])
                    # Windows venv may launch a second interpreter. Verify its ownership too.
                    handle=win32api.OpenProcess(win32con.PROCESS_SET_QUOTA|win32con.PROCESS_TERMINATE|win32con.PROCESS_QUERY_INFORMATION,False,ready['pid'])
                    try:
                        if not win32job.IsProcessInJob(handle,self.job):win32job.AssignProcessToJobObject(self.job,handle)
                        assigned=win32job.IsProcessInJob(handle,self.job)
                    finally:handle.Close()
                    if not assigned:raise ContractError('SERVICE_JOB_OWNERSHIP_FAILED')
                    jsonl(self.dir/'process.jsonl',{'kind':'ready','actualServerInOwnedJob':assigned,**ready});return self
                if self.process.poll() is not None:raise ContractError('SERVICE_START_FAILED')
                await asyncio.sleep(.01)
            raise ContractError('SERVICE_START_TIMEOUT')
        except BaseException:await self.stop();raise
    async def stop(self):
        if self.job:
            win32job.TerminateJobObject(self.job,82);self.job.Close();self.job=None
        if self.process:await asyncio.to_thread(self.process.wait)
        if hasattr(self,'log'):self.log.close()
        jsonl(self.dir/'process.jsonl',{'kind':'stopped','pids':self.pids,'alive':[pid for pid in self.pids if alive(pid)]})
    async def close(self):
        if self.closed:return
        self.closed=True;await self.stop()
