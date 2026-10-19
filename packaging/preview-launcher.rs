//! Native app entry point: relocatable bundle resources and a separate user profile.
//! No shell, Python installation discovery, cwd dependency or automatic control listener.
#![forbid(unsafe_code)]
use std::{
    env,
    ffi::OsStr,
    os::unix::process::CommandExt,
    path::PathBuf,
    process::{Command, ExitCode},
};

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let exe = env::current_exe()?;
    let macos = exe.parent().ok_or("launcher is not inside an app bundle")?;
    let resources = macos
        .parent()
        .ok_or("bundle Contents missing")?
        .join("Resources");
    let arch = match env::consts::ARCH {
        "aarch64" => "arm64",
        "x86_64" => "x86_64",
        _ => return Err("unsupported macOS architecture".into()),
    };
    let python = resources
        .join("Python")
        .join(arch)
        .join("python/bin/python3");
    let reader = resources.join("aaf/scripts/aaf_bridge.py");
    if !python.is_file() || !reader.is_file() {
        return Err(
            "bundled AAF reader/runtime missing; reinstall the complete preview app".into(),
        );
    }
    let args: Vec<_> = env::args_os().skip(1).collect();
    if args.first().is_some_and(|a| a == OsStr::new("--version")) {
        println!("SoundCraft AAF Preview 0.9.0-aaf.1-dev.2 (unofficial development build)");
        return Ok(());
    }
    let mut cmd = if args
        .first()
        .is_some_and(|a| a == OsStr::new("--reader-self-test"))
    {
        let mut c = Command::new(&python);
        c.arg("-I").arg("-B").arg(&reader).arg("--self-test");
        c
    } else {
        let mut c = Command::new(macos.join("SoundCraft-bin"));
        c.args(args);
        c
    };
    let home = PathBuf::from(env::var_os("HOME").ok_or("HOME is unavailable")?);
    cmd.env("SOUNDCRAFT_AAF_PYTHON", python)
        .env("SOUNDCRAFT_AAF_READER", reader)
        .env(
            "SOUNDCRAFT_CONFIG_DIR",
            home.join("Library/Application Support/SoundCraft AAF Preview Portable"),
        );
    Err(cmd.exec().into())
}
fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("SoundCraft AAF Preview: {e}");
            ExitCode::FAILURE
        }
    }
}
