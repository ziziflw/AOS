use aos_p006_host::{Host,Request,error,LIMIT};
use std::{sync::{Arc,Mutex},path::PathBuf,fs::OpenOptions,io::Write};
use serde_json::{json,Value};
use tauri::{Manager,State,WebviewWindow};
struct Bridge {host:Arc<Mutex<Host>>,session:PathBuf,selftest:bool}
#[tauri::command]
async fn host_request(window:WebviewWindow,state:State<'_,Bridge>,request:Value)->Result<Value,String> {
    if window.label()!="main" {return Err("WINDOW_DENIED".into());}
    if request.to_string().len()>LIMIT {return Ok(error("","FRAME_SIZE"));}
    let r:Request=serde_json::from_value(request).map_err(|_|"INVALID_ENVELOPE")?;
    let op=r.op.clone();let id=r.id.clone();let h=state.host.clone();let path=state.session.join("window-bridge.jsonl");
    tauri::async_runtime::spawn_blocking(move || {
        let mut host=h.lock().map_err(|_|"HOST_LOCK")?;let reply=host.dispatch(r);
        if let Ok(mut f)=OpenOptions::new().create(true).append(true).open(path) {let _=writeln!(f,"{}",json!({"window":"main","op":op,"id":id,"response":reply}));}
        Ok(reply)
    }).await.map_err(|_|"BRIDGE_JOIN".to_string())?
}
#[tauri::command]
fn window_report(window:WebviewWindow,state:State<'_,Bridge>,report:Value)->Result<(),String> {
    if window.label()!="main"||report.to_string().len()>65536 {return Err("REPORT_DENIED".into());}
    std::fs::write(state.session.join("window-report.json"),serde_json::to_vec_pretty(&report).unwrap()).map_err(|_|"REPORT_WRITE".to_string())?;
    if state.selftest {window.app_handle().exit(0);}Ok(())
}
fn main() {
    let args:Vec<_>=std::env::args().collect();
    if args.len()<3 {eprintln!("host-window ROOT SESSION [selftest]");return;}
    let session=PathBuf::from(&args[2]);let test=args.get(3).is_some_and(|s|s=="selftest");
    let host=Host::new(PathBuf::from(&args[1]),session.clone(),"approver".into(),"normal".into(),false).expect("configuration");
    tauri::Builder::default().manage(Bridge{host:Arc::new(Mutex::new(host)),session,selftest:test})
        .invoke_handler(tauri::generate_handler![host_request,window_report])
        .setup(move|app|{let profile=app.state::<Bridge>().session.join("webview-profile");tauri::WebviewWindowBuilder::new(app,"main",tauri::WebviewUrl::default()).title("AOS P0-06 — Windows IPC experiment").inner_size(760.,660.).data_directory(profile).initialization_script(if test {"window.__AOS_SELFTEST__=true;"}else{"window.__AOS_SELFTEST__=false;"}).build()?;Ok(())})
        .build(tauri::generate_context!()).expect("Tauri initialization")
        .run(|app,event|{if matches!(event,tauri::RunEvent::Exit){let state=app.state::<Bridge>();if let Ok(mut host)=state.host.lock(){
            let r=Request{v:"aos-local/0.1".into(),kind:"request".into(),id:"window-exit".into(),op:"host.stop".into(),body:json!({"mode":"suspend"})};let _=host.dispatch(r);host.force_stop();
        };}});
}
