//! Lifecycle/permission boundary only. Never reads or writes workflow SQLite.
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{collections::VecDeque, fs::{self, File, OpenOptions}, io::{Read, Write}, os::windows::{io::AsRawHandle, process::CommandExt}, path::PathBuf, process::{Child, Command, Stdio}, sync::mpsc::{self, Receiver,SyncSender}, time::{Duration, Instant}};
use windows_sys::Win32::{Foundation::{CloseHandle, HANDLE}, System::{JobObjects::*, Threading::{OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION}}};
pub const LIMIT: usize = 262144;
pub const VERSION: &str = "aos-local/0.1";
#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Request { pub v: String, pub kind: String, pub id: String, pub op: String, pub body: Value }
pub fn error(id: &str, code: &str) -> Value { json!({"v":VERSION,"kind":"response","id":id,"ok":false,"error":{"code":code,"retryable":false}}) }
pub fn ok(id: &str, result: Value) -> Value { json!({"v":VERSION,"kind":"response","id":id,"ok":true,"result":result}) }
struct Job(HANDLE);
unsafe impl Send for Job {}
impl Job {
    fn new() -> Result<Self, String> { unsafe {
        let h=CreateJobObjectW(std::ptr::null(), std::ptr::null());
        if h.is_null() { return Err("JOB_CREATE_FAILED".into()); }
        let j=Job(h); let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION=std::mem::zeroed();
        info.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        if SetInformationJobObject(h, JobObjectExtendedLimitInformation, &info as *const _ as _, std::mem::size_of_val(&info) as u32)==0 {return Err("JOB_CONFIG_FAILED".into());} Ok(j)
    }}
    fn assign(&self, c:&Child) -> Result<(),String> { if unsafe {AssignProcessToJobObject(self.0,c.as_raw_handle() as HANDLE)}==0 { Err("JOB_ASSIGN_FAILED".into()) } else {Ok(())} }
    fn contains(&self,pid:u32)->bool {unsafe {let h=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,0,pid);if h.is_null(){return false;} let mut b=0;let r=IsProcessInJob(h,self.0,&mut b);CloseHandle(h);r!=0&&b!=0}}
    fn terminate(&self) {unsafe {TerminateJobObject(self.0,76);}}
    fn active(&self)->Option<u32> {unsafe {let mut info:JOBOBJECT_BASIC_ACCOUNTING_INFORMATION=std::mem::zeroed();
        if QueryInformationJobObject(self.0,JobObjectBasicAccountingInformation,&mut info as *mut _ as _,std::mem::size_of_val(&info) as u32,std::ptr::null_mut())==0 {None}else{Some(info.ActiveProcesses)}
    }}
    fn wait_empty(&self)->Option<u32> {let deadline=Instant::now()+Duration::from_secs(3);loop {let active=self.active();if active==Some(0)||Instant::now()>=deadline{return active;}std::thread::sleep(Duration::from_millis(10));}}
}
impl Drop for Job {fn drop(&mut self) {unsafe {CloseHandle(self.0);}}}
type FrameWrite=(Vec<u8>,SyncSender<Result<(),String>>);
struct Worker {child:Child, writes:SyncSender<FrameWrite>, replies:Receiver<Result<Value,String>>, job:Job}
pub struct Host {pub root:PathBuf, pub session:PathBuf, pub role:String, pub fault:String, worker:Option<Worker>, pub pending:VecDeque<Value>, pub test_faults:bool}
impl Host {
    pub fn new(root:PathBuf, session:PathBuf, role:String, fault:String, test_faults:bool)->Result<Self,String> {
        let root=root.canonicalize().map_err(|_|"ROOT_MISSING")?;
        fs::create_dir_all(&session).map_err(|_|"SESSION_CREATE")?;
        let session=session.canonicalize().map_err(|_|"SESSION_MISSING")?;
        if !session.starts_with(root.join("evidence")) {return Err("SESSION_OUTSIDE_EXPERIMENT".into());}
        if !["viewer","operator","approver"].contains(&role.as_str()) {return Err("ROLE_INVALID".into());}
        Ok(Self{root,session,role,fault,worker:None,pending:VecDeque::new(),test_faults})
    }
    fn trace(&self, value:Value) { if let Ok(mut f)=OpenOptions::new().create(true).append(true).open(self.session.join("host-trace.jsonl")) {let _=writeln!(f,"{}",value);} }
    fn allowed(&self,op:&str)->bool {
        match op {"health"|"status"|"events"|"approvals"=>true,
            "load"|"create"|"recover"|"cancel"=>self.role!="viewer",
            "approve"=>self.role=="approver",
            "host.start"|"host.stop"=>self.role!="viewer",
            "host.crash-worker"=>self.test_faults&&self.role!="viewer",_=>false}
    }
    fn start(&mut self)->Result<Value,String> {
        if let Some(w)=self.worker.as_mut() {
            if w.child.try_wait().map_err(|_|"PROCESS_QUERY")?.is_none(){return Ok(json!({"alreadyStarted":true,"pid":w.child.id()}));}
            return Err("EXECUTOR_EXITED_RESTART_REQUIRED".into());
        }
        let gate=self.session.join("worker-gate");let _=fs::remove_file(&gate);
        let stderr=File::options().create(true).append(true).open(self.session.join("worker-stderr.log")).map_err(|_|"STDERR_CREATE")?;
        let job=Job::new()?;
        let mut cmd=Command::new(self.root.join(".venv/Scripts/python.exe"));
        cmd.args(["-B","-X","utf8"]).arg(self.root.join("executor.py")).arg("--session").arg(&self.session).arg("--fault").arg(&self.fault)
            .current_dir(&self.root).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::from(stderr)).creation_flags(0x08000000);
        let keep=["SYSTEMROOT","WINDIR","TEMP","TMP","PATH"];
        let env:Vec<_>=keep.iter().filter_map(|k|std::env::var(k).ok().map(|v|(*k,v))).collect();
        cmd.env_clear().envs(env).env("PYTHONNOUSERSITE","1").env("PYTHONDONTWRITEBYTECODE","1").env("PYTHONUTF8","1");
        let mut child=cmd.spawn().map_err(|_|"EXECUTOR_SPAWN_FAILED")?;
        if let Err(e)=job.assign(&child) {let _=child.kill();let _=child.wait();return Err(e);}
        self.trace(json!({"kind":"spawn","launcherPid":child.id(),"ownedJob":true}));
        let mut input=child.stdin.take().unwrap();let mut output=child.stdout.take().unwrap();
        let (writes,write_rx)=mpsc::sync_channel::<FrameWrite>(1);
        std::thread::spawn(move||{while let Ok((bytes,ack))=write_rx.recv(){
            let result=input.write_all(&(bytes.len() as u32).to_be_bytes()).and_then(|_|input.write_all(&bytes)).and_then(|_|input.flush()).map_err(|_|"EXECUTOR_DISCONNECTED".to_string());
            let failed=result.is_err();let _=ack.send(result);if failed{break;}
        }});
        let (tx,rx)=mpsc::sync_channel(512);
        std::thread::spawn(move||loop {
            let result=(||{let mut n=[0;4];output.read_exact(&mut n).map_err(|_|"EXECUTOR_DISCONNECTED")?;
                let size=u32::from_be_bytes(n) as usize;if size==0||size>LIMIT{return Err("FRAME_SIZE".to_string());}
                let mut b=vec![0;size];output.read_exact(&mut b).map_err(|_|"FRAME_TRUNCATED")?;
                serde_json::from_slice::<Value>(&b).map_err(|_|"FRAME_JSON".to_string())})();
            let stop=result.is_err();if tx.send(result).is_err()||stop{break;}
        });
        self.worker=Some(Worker{child,writes,replies:rx,job});
        fs::write(gate,b"owned").map_err(|_|"GATE_CREATE")?;
        let ready=self.worker.as_ref().unwrap().replies.recv_timeout(Duration::from_secs(5));
        match ready {
            Ok(Ok(v)) if v["kind"]=="ready"&&v["v"]==VERSION=>{
                let pid=v["pid"].as_u64().ok_or("READY_INVALID")? as u32;
                if !self.worker.as_ref().unwrap().job.contains(pid) {self.force_stop();return Err("ACTUAL_EXECUTOR_NOT_OWNED".into());}
                self.trace(json!({"kind":"ready","actualPid":pid,"actualInJob":true}));Ok(v)
            },
            _=>{self.force_stop();Err("EXECUTOR_START_FAILED_OR_TIMEOUT".into())}
        }
    }
    fn call(&mut self,r:&Request)->Result<Value,String> {
        let w=self.worker.as_mut().ok_or("EXECUTOR_NOT_STARTED")?;
        let bytes=serde_json::to_vec(r).map_err(|_|"SERIALIZE")?;
        if bytes.len()>LIMIT{return Err("FRAME_SIZE".into());}
        let (ack,write_ack)=mpsc::sync_channel(1);
        w.writes.try_send((bytes,ack)).map_err(|_|"WRITE_QUEUE_FULL_OR_CLOSED")?;
        write_ack.recv_timeout(Duration::from_secs(3)).map_err(|_|"WRITE_TIMEOUT_OR_DISCONNECT")??;
        let deadline=Instant::now()+Duration::from_secs(20);
        loop {
            let timeout=deadline.checked_duration_since(Instant::now()).ok_or("RESPONSE_TIMEOUT")?;
            let v=w.replies.recv_timeout(timeout).map_err(|_|"RESPONSE_TIMEOUT_OR_DISCONNECT")??;
            if v["v"]!=VERSION{return Err("RESPONSE_VERSION".into());}
            if v["kind"]=="event" {if self.pending.len()>=512{self.pending.pop_front();}self.pending.push_back(v);continue;}
            if v["kind"]=="response"&&v["id"]==r.id{return Ok(v);}
            self.pending.push_back(json!({"v":VERSION,"kind":"transport-warning","code":"UNMATCHED_RESPONSE","id":v["id"]}));
        }
    }
    pub fn dispatch(&mut self,r:Request)->Value {
        if r.v!=VERSION||r.kind!="request"||r.id.is_empty()||r.id.len()>64||!r.id.bytes().all(|b|b.is_ascii_alphanumeric()||b==b'-'||b==b'_') {return error(&r.id,"INVALID_ENVELOPE");}
        if !self.allowed(&r.op) {return error(&r.id,if ["host.start","host.stop","host.crash-worker","load","create","recover","cancel","approve"].contains(&r.op.as_str()) {"PERMISSION_DENIED"}else{"UNKNOWN_COMMAND"});}
        let result=match r.op.as_str() {
            "host.start"=>{if r.body!=json!({}){Err("INVALID_BODY".into())}else{self.start()}},
            "host.crash-worker"=>{if r.body!=json!({}){Err("INVALID_BODY".into())}else if self.force_stop(){Ok(json!({"localProcessStopped":true,"remoteTaskStopped":"unconfirmed"}))}else{Err("OWNED_PROCESSES_NOT_STOPPED".into())}},
            "host.stop"=>{let request=Request{v:VERSION.into(),kind:"request".into(),id:r.id.clone(),op:"shutdown".into(),body:r.body.clone()};
                let result=self.call(&request);if result.as_ref().is_ok_and(|v|v["ok"]==true) && !self.force_stop() {return error(&r.id,"OWNED_PROCESSES_NOT_STOPPED");}return match result {Ok(v)=>v,Err(e)=>error(&r.id,&e)};},
            _=>return match self.call(&r) {Ok(v)=>v,Err(e)=>{self.trace(json!({"kind":"transport-error","code":e}));error(&r.id,&e)}}
        };match result {Ok(v)=>ok(&r.id,v),Err(e)=>error(&r.id,&e)}
    }
    pub fn force_stop(&mut self)->bool {if let Some(mut w)=self.worker.take(){w.job.terminate();let _=w.child.wait();let active=w.job.wait_empty();self.trace(json!({"kind":"owned-job-stopped","launcherPid":w.child.id(),"exitCode":w.child.try_wait().ok().flatten().and_then(|s|s.code()),"activeAfterStop":active,"remoteState":"unconfirmed"}));return active==Some(0);}true}
}
impl Drop for Host {fn drop(&mut self){if self.worker.is_some(){
    let r=Request{v:VERSION.into(),kind:"request".into(),id:"host-drop".into(),op:"shutdown".into(),body:json!({"mode":"suspend"})};
    let reply=self.call(&r);self.trace(json!({"kind":"normal-host-exit-coordination","acknowledged":reply.is_ok_and(|v|v["ok"]==true)}));
}self.force_stop();}}
