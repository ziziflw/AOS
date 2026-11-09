#![windows_subsystem="windows"]
use std::{env,fs,io,path::Path,process::Command};
fn unpack(src:&Path,dst:&Path)->io::Result<()> {
 fs::create_dir_all(dst)?;
 for entry in fs::read_dir(src)? {let e=entry?;let target=dst.join(e.file_name());
 if e.file_type()?.is_dir(){unpack(&e.path(),&target)?;}else{fs::copy(e.path(),target)?;}}
 Ok(())
}
fn main()->io::Result<()> {
 let exe=env::current_exe()?;let source=exe.parent().unwrap().join("app");
 let home=std::path::PathBuf::from(env::var_os("LOCALAPPDATA").ok_or(io::ErrorKind::NotFound)?).join("AOS-Demo");
 fs::create_dir_all(&home)?; let dst=home.join("v0.1.1");
 if !dst.exists(){let temp=home.join(format!("install-{}",std::process::id()));unpack(&source,&temp)?;if let Err(e)=fs::rename(&temp,&dst){if !dst.exists(){return Err(e);}}}
 let root=dst.join("experiments/p0-08");let session=root.join("evidence/session-desktop");
 Command::new(dst.join("workbench.exe")).arg(&root).arg(session).current_dir(&root).spawn()?.wait()?; Ok(())
}
