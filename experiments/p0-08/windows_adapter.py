"""Fixed Windows process resolution. No command strings, user paths, or shell."""
import asyncio,hashlib,os,subprocess
from pathlib import Path
import win32job
from process_host import ProcessHost
from common import ContractError
HERE=Path(__file__).resolve().parent;P04=HERE.parent/'p0-04'
class LocalMCPHost(ProcessHost):
    def __init__(self,directory,launch):
        self.directory=Path(directory).resolve();self.launch=launch;self.p=None;self.job=None;self.closed=False
        if not self.directory.is_relative_to(HERE/'evidence'):raise ContractError('EVIDENCE_PATH_DENIED')
        self.directory.mkdir(parents=True,exist_ok=True)
    def start(self):
        if os.name!='nt':raise ContractError('WINDOWS_NOT_VERIFIED')
        if self.launch['executable']!=str(P04/'.venv/Scripts/python.exe') or self.launch['args']!=['-B','-X','utf8',str(P04/'synthetic_server.py')]:raise ContractError('SERVER_COMMAND_DENIED')
        wrapper=HERE/'mcp_server_entry.py'
        if self.launch.get('p006:wrapperSha256')!=hashlib.sha256(wrapper.read_bytes()).hexdigest():raise ContractError('SERVER_WRAPPER_DRIFT')
        mode=self.launch['mode']
        if mode not in ('normal','spawn-child'):raise ContractError('SERVER_MODE_DENIED')
        gate=self.directory/'launch-gate'
        if gate.exists():gate.unlink()
        self.stderr=(self.directory/'stderr.log').open('ab')
        self.job=win32job.CreateJobObject(None,'')
        info=win32job.QueryInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation)
        info['BasicLimitInformation']['LimitFlags']|=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation,info)
        env={k:os.environ[k] for k in ('SYSTEMROOT','WINDIR','TEMP','TMP') if k in os.environ};env.update(PYTHONNOUSERSITE='1',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
        command=[str(HERE.parent/'p0-06/.venv/Scripts/python.exe'),'-B','-X','utf8',str(wrapper),'--directory',str(self.directory),'--mode',mode]
        try:
            self.p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,cwd=HERE,env=env,creationflags=subprocess.CREATE_NO_WINDOW,bufsize=0)
            win32job.AssignProcessToJobObject(self.job,int(self.p._handle));self.record('started',pid=self.p.pid,command=command,jobKillOnClose=True,assigned=True,resolution='fixed p006 evidence-root shim')
            gate.write_text('owned',encoding='ascii')
        except BaseException:
            if self.p and self.p.poll() is None:self.p.kill();self.p.wait()
            if self.job:self.job.Close();self.job=None
            self.stderr.close();raise
