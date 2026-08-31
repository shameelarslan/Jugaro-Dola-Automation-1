// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{AppHandle, Manager};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

const SIDECAR_EXE: &str = "WaqasAutomationServer.exe";

struct SidecarState {
    child: Mutex<Option<Child>>,
}

/// Chromium that ships inside the installer. Exported so Playwright (and the
/// app's own browser_factory) picks it up instead of demanding a system browser.
fn bundled_browsers_dir(resource_dir: &Path) -> Option<PathBuf> {
    for candidate in [
        resource_dir.join("resources/ms-playwright"),
        resource_dir.join("ms-playwright"),
    ] {
        if candidate.is_dir() {
            return Some(candidate);
        }
    }
    None
}

/// Locates the frozen Python backend that the installer ships.
fn bundled_sidecar(resource_dir: &Path, exe_dir: &Path) -> Option<PathBuf> {
    for candidate in [
        resource_dir.join("resources/server").join(SIDECAR_EXE),
        resource_dir.join("server").join(SIDECAR_EXE),
        exe_dir.join("resources/server").join(SIDECAR_EXE),
        exe_dir.join("server").join(SIDECAR_EXE),
        exe_dir.join(SIDECAR_EXE),
    ] {
        if candidate.is_file() {
            return Some(candidate);
        }
    }
    None
}

/// Development fallback: run app/server.py with whatever Python is installed.
fn dev_server_script(exe_dir: &Path) -> Option<(PathBuf, PathBuf)> {
    let candidates = [
        PathBuf::from("app/server.py"),
        PathBuf::from("../app/server.py"),
        exe_dir.join("app/server.py"),
        exe_dir.join("../app/server.py"),
    ];

    for candidate in candidates.iter() {
        if candidate.exists() {
            if let Ok(script) = candidate.canonicalize() {
                // project root = parent of the `app` folder
                let workdir = script
                    .parent()
                    .and_then(|app_folder| app_folder.parent())
                    .map(|root| root.to_path_buf())
                    .unwrap_or_else(|| PathBuf::from("."));
                return Some((script, workdir));
            }
        }
    }
    None
}

fn python_candidates() -> Vec<String> {
    let mut candidates: Vec<String> = Vec::new();
    if cfg!(target_os = "windows") {
        if let Ok(local_appdata) = std::env::var("LOCALAPPDATA") {
            for series in ["314", "313", "312", "311"] {
                let path = format!(
                    "{}\\Programs\\Python\\Python{}\\python.exe",
                    local_appdata, series
                );
                if Path::new(&path).exists() {
                    candidates.push(path);
                }
            }
        }
    }
    candidates.extend(["python".into(), "py".into(), "python3".into()]);
    candidates
}

fn spawn_sidecar(app: &AppHandle) -> Option<Child> {
    let resource_dir = app.path().resource_dir().unwrap_or_else(|_| PathBuf::from("."));
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));

    let browsers_dir = bundled_browsers_dir(&resource_dir);

    // 1. Preferred: the self-contained backend bundled with the installer.
    if let Some(sidecar) = bundled_sidecar(&resource_dir, &exe_dir) {
        let workdir = sidecar.parent().map(|p| p.to_path_buf()).unwrap_or(exe_dir.clone());
        let mut command = Command::new(&sidecar);
        command.current_dir(&workdir);
        if let Some(ref browsers) = browsers_dir {
            command.env("PLAYWRIGHT_BROWSERS_PATH", browsers);
        }
        #[cfg(target_os = "windows")]
        command.creation_flags(CREATE_NO_WINDOW);

        match command.spawn() {
            Ok(child) => {
                println!(
                    "Backend started from bundled sidecar (PID {}): {:?}",
                    child.id(),
                    sidecar
                );
                return Some(child);
            }
            Err(err) => eprintln!("Bundled sidecar failed to start ({:?}): {}", sidecar, err),
        }
    }

    // 2. Development fallback: system Python running the source tree.
    let Some((script, workdir)) = dev_server_script(&exe_dir) else {
        eprintln!("No bundled sidecar and no app/server.py found — backend not started.");
        return None;
    };

    for candidate in python_candidates() {
        let mut command = Command::new(&candidate);
        command.arg(&script).current_dir(&workdir);
        if let Some(ref browsers) = browsers_dir {
            command.env("PLAYWRIGHT_BROWSERS_PATH", browsers);
        }
        #[cfg(target_os = "windows")]
        command.creation_flags(CREATE_NO_WINDOW);

        if let Ok(child) = command.spawn() {
            println!(
                "Backend started via '{}' (PID {}) running {:?}",
                candidate,
                child.id(),
                script
            );
            return Some(child);
        }
    }

    eprintln!("Could not start the Python backend with any known interpreter.");
    None
}

fn main() {
    tauri::Builder::default()
        .manage(SidecarState {
            child: Mutex::new(None),
        })
        .setup(|app| {
            let child = spawn_sidecar(app.handle());
            if let Ok(mut lock) = app.state::<SidecarState>().child.lock() {
                *lock = child;
            }

            if let Some(window) = app.get_webview_window("main") {
                let _ = window.maximize();
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Kill the backend on exit so no orphan process keeps port 8765.
                {
                    let state = window.state::<SidecarState>();
                    if let Ok(mut lock) = state.child.lock() {
                        if let Some(mut child) = lock.take() {
                            let _ = child.kill();
                            let _ = child.wait();
                            println!("Backend process closed.");
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
