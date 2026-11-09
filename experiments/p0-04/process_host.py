"""Windows-only ownership boundary. No process-name scans or shell commands."""
import asyncio,json,os,subprocess,time
from pathlib import Path
from bootstrap import HERE,ContractError
import win32job,win32api,win32con,win32process

def alive(pid):
    try:
        h=win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION,False,pid)
        try: return win32process.GetExitCodeProcess(h)==259
        finally: h.Close()
    except Exception: return False

class ProcessHost:
    def __init__(self,directory,launch):
        self.directory=Path(directory).resolve(); self.launch=launch; self.p=None; self.job=None; self.closed=False
        if not self.directory.is_relative_to(HERE/'evidence'): raise ContractError('EVIDENCE_PATH_DENIED')
        self.directory.mkdir(parents=True,exist_ok=True)
    def record(self,kind,**body):
        with (self.directory/'process.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps({'kind':kind,'time':time.time(),**body},ensure_ascii=False)+'\n')
    def start(self):
        if os.name!='nt': raise ContractError('WINDOWS_NOT_VERIFIED')
        executable=Path(self.launch['executable']).resolve(); args=self.launch['args']
        expected=HERE/'.venv/Scripts/python.exe'
        if executable!=expected.resolve() or not executable.is_file(): raise ContractError('SERVER_PROGRAM_MISSING_OR_DENIED')
        if args[:3]!=['-B','-X','utf8'] or Path(args[3]).resolve()!=HERE/'synthetic_server.py': raise ContractError('SERVER_COMMAND_DENIED')
        # No user-supplied shell text; only one known server, bounded fault modes and its evidence directory.
        if len(args)!=4: raise ContractError('SERVER_ARGUMENTS_DENIED')
        mode=self.launch['mode']
        if mode not in {'normal','slow-init','spawn-child','init-exit','stdout-pollution','call-exit','lost-response','effect-delay','ignore-cancel','bad-output','bad-version','schema-drift'}:
            raise ContractError('SERVER_MODE_DENIED')
        gate=self.directory/'launch-gate'
        if gate.exists(): gate.unlink()  # this experiment's single owned marker only
        env={k:os.environ[k] for k in ('SYSTEMROOT','WINDIR','TEMP','TMP') if k in os.environ}
        env.update(PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
        self.stderr=(self.directory/'stderr.log').open('ab')
        try:
            self.job=win32job.CreateJobObject(None,'')
            info=win32job.QueryInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation)
            info['BasicLimitInformation']['LimitFlags']|=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation,info)
            command=[str(executable),*args,'--directory',str(self.directory),'--mode',mode]
            self.p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,cwd=HERE,
                                    env=env,creationflags=subprocess.CREATE_NO_WINDOW,bufsize=0)
            win32job.AssignProcessToJobObject(self.job,int(self.p._handle))
            self.record('started',pid=self.p.pid,command=command,jobKillOnClose=True,assigned=True)
            gate.write_text('owned',encoding='ascii')
        except BaseException:
            if self.p and self.p.poll() is None: self.p.kill(); self.p.wait()
            if self.job: self.job.Close(); self.job=None
            self.stderr.close(); raise
    def kill_owned(self,reason):
        if self.job:
            self.record('job-terminated',pid=self.p.pid,reason=reason)
            win32job.TerminateJobObject(self.job,71)
    async def close(self):
        if self.closed: self.record('duplicate-close'); return
        self.closed=True
        if self.p:
            try: self.p.stdin.close()
            except (OSError,ValueError): pass
            try: await asyncio.wait_for(asyncio.to_thread(self.p.wait),.3)
            except TimeoutError: self.kill_owned('graceful-close-timeout'); await asyncio.to_thread(self.p.wait)
            # Also close inherited members if the direct process exited first.
            if self.job: self.job.Close(); self.job=None
            self.record('closed',pid=self.p.pid,returnCode=self.p.returncode,alive=alive(self.p.pid))
            self.p.stdout.close()
        if hasattr(self,'stderr'): self.stderr.close()
