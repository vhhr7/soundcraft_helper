#![deny(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::unimplemented,
    clippy::todo,
    clippy::unreachable
)]
use soundcraft_interchange::{Plan, build_session};
use std::{
    error::Error,
    fs::{self, OpenOptions},
    io::Read,
    path::Path,
};

fn run() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    let (Some(input), Some(output)) = (args.first(), args.get(1)) else {
        return Err("usage: plan-to-session PLAN.json NEW_OUTPUT_DIRECTORY".into());
    };
    if args.len() != 2 {
        return Err("expected exactly two arguments".into());
    }
    let mut text = String::new();
    fs::File::open(input)?
        .take(32 * 1024 * 1024 + 1)
        .read_to_string(&mut text)?;
    if text.len() > 32 * 1024 * 1024 {
        return Err("plan exceeds 32 MiB".into());
    }
    let plan: Plan = serde_json::from_str(&text)?;
    // Verify local files independently of the reader. Cap bytes before allocation.
    for m in &plan.sources {
        let path = Path::new(&m.path);
        if !path.is_absolute() {
            return Err("plan media paths must be absolute".into());
        }
        let meta = fs::metadata(path)?;
        if !meta.is_file() || meta.len() > 512 * 1024 * 1024 {
            return Err(format!("invalid/oversized media: {}", path.display()).into());
        }
        let mut bytes = Vec::new();
        fs::File::open(path)?
            .take(512 * 1024 * 1024 + 1)
            .read_to_end(&mut bytes)?;
        if bytes.len() > 512 * 1024 * 1024 {
            return Err("media exceeds byte limit".into());
        }
        let info = soundcraft_audio_io::probe(&bytes, Some("wav"))?;
        if info.format != soundcraft_audio_io::FileFormat::Wav
            || (info.channels, info.sample_rate, info.frames)
                != (m.channels, m.sample_rate, m.frames)
        {
            return Err(format!("media changed or metadata mismatch: {}", path.display()).into());
        }
    }
    let imported = build_session(plan)?;
    let out = Path::new(output);
    // New directory only: never overwrite a session or any of its original media.
    fs::create_dir(out)?;
    let publish = || -> Result<(), Box<dyn Error>> {
        let audio_dir = out.join("Audio Files");
        fs::create_dir(&audio_dir)?;
        let mut session = imported.session;
        for source in &mut session.sources {
            let rel = format!("Audio Files/source-{}.wav", source.id.0);
            let mut dest = OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(out.join(&rel))?;
            let mut src = fs::File::open(&source.path)?;
            std::io::copy(&mut src, &mut dest)?;
            dest.sync_all()?;
            source.path = rel;
        }
        fs::write(
            out.join("import-report.json"),
            serde_json::to_vec_pretty(&imported.report)?,
        )?;
        fs::write(out.join("session.scraft"), session.to_json()?)?;
        Ok(())
    };
    if let Err(e) = publish() {
        // Leave the new incomplete directory for diagnosis; no valid session is published first.
        return Err(format!("incomplete output {}: {e}", out.display()).into());
    }
    println!("{}", out.join("session.scraft").display());
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}
