// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Child};
use std::sync::Mutex;
use std::path::Path;
use tauri::Manager;

struct SidecarState {
    child: Mutex<Option<Child>>,
}

fn main() {
    // Spawn Python Sidecar API Server on startup
    let mut sidecar_child = None;
    // Find valid Python executable
    let mut py_candidates = vec!["python", "py", "python3"];
    if cfg!(target_os = "windows") {
        if let Ok(local_appdata) = std::env::var("LOCALAPPDATA") {
            let p314 = format!("{}\\Programs\\Python\\Python314\\python.exe", local_appdata);
            if Path::new(&p314).exists() {
                py_candidates.insert(0, Box::leak(p314.into_boxed_str()));
            }
            let p313 = format!("{}\\Programs\\Python\\Python313\\python.exe", local_appdata);
            if Path::new(&p313).exists() {
                py_candidates.insert(1, Box::leak(p313.into_boxed_str()));
            }
            let p312 = format!("{}\\Programs\\Python\\Python312\\python.exe", local_appdata);
            if Path::new(&p312).exists() {
                py_candidates.insert(2, Box::leak(p312.into_boxed_str()));
            }
        }
    }

    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| Path::new(".").to_path_buf());

    let path_candidates = vec![
        Path::new("app/server.py").to_path_buf(),
        Path::new("../app/server.py").to_path_buf(),
        exe_dir.join("app/server.py"),
        exe_dir.join("../app/server.py"),
    ];

    let mut resolved_script = None;
    let mut resolved_workdir = Path::new(".").to_path_buf();

    for cand in &path_candidates {
        if cand.exists() {
            if let Ok(canon) = cand.canonicalize() {
                // The parent of 'app' folder is the project root
                if let Some(app_folder) = canon.parent() {
                    if let Some(root_folder) = app_folder.parent() {
                        resolved_workdir = root_folder.to_path_buf();
                    } else {
                        resolved_workdir = app_folder.to_path_buf();
                    }
                }
                resolved_script = Some(canon);
                break;
            }
        }
    }

    let final_script = resolved_script.unwrap_or_else(|| Path::new("app/server.py").to_path_buf());

    for candidate in &py_candidates {
        if let Ok(child) = Command::new(candidate)
            .arg(&final_script)
            .current_dir(&resolved_workdir)
            .spawn()
        {
            println!("🚀 Python Sidecar API Server spawned cleanly (PID: {}) using '{}' at '{:?}' in '{:?}'", child.id(), candidate, final_script, resolved_workdir);
            sidecar_child = Some(child);
            break;
        }
    }

    if sidecar_child.is_none() {
        eprintln!("⚠️ Could not spawn Python sidecar using candidates: {:?}", py_candidates);
    }

    tauri::Builder::default()
        .manage(SidecarState {
            child: Mutex::new(sidecar_child),
        })
        .setup(|app| {
            // Maximize window on startup for full-screen experience
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.maximize();
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Kill Python sidecar on exit
                let state = window.state::<SidecarState>();
                if let Ok(mut lock) = state.child.lock() {
                    if let Some(mut child) = lock.take() {
                        let _ = child.kill();
                        println!("Closed Python sidecar process.");
                    }
                };
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
