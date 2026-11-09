use aos_p007_host::{Host,Request,LIMIT,error};
use std::{io::{self,BufRead,Read,Write},path::PathBuf};
fn main() {
    let args:Vec<_>=std::env::args().collect();
    if args.len()!=6 {eprintln!("Usage: host-probe ROOT SESSION ROLE FAULT test|normal");std::process::exit(2);}
    let mut h=Host::new(PathBuf::from(&args[1]),PathBuf::from(&args[2]),args[3].clone(),args[4].clone(),args[5]=="test").expect("fixed local configuration");
    // Test-driver ingress is JSONL; the actual Rust/executor boundary uses 4-byte framing.
    let mut input=io::stdin().lock();let mut out=io::stdout().lock();
    loop {let mut b=Vec::new();let n=input.by_ref().take((LIMIT+2) as u64).read_until(b'\n',&mut b).unwrap_or(0);if n==0{break;}
        let v=if b.len()>LIMIT {error("","FRAME_SIZE")}else{match serde_json::from_slice::<Request>(&b) {Ok(r)=>h.dispatch(r),Err(_)=>error("","INVALID_JSON_OR_ENVELOPE")}};
        while let Some(e)=h.pending.pop_front(){writeln!(out,"{}",e).unwrap();}
        writeln!(out,"{}",v).unwrap();out.flush().unwrap();if b.len()>LIMIT{break;}
    }
}
