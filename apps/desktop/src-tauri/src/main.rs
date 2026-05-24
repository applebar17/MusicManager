#[tauri::command]
fn pick_music_folder() -> Result<Option<String>, String> {
    pick_music_folder_impl()
}

#[cfg(target_os = "macos")]
fn pick_music_folder_impl() -> Result<Option<String>, String> {
    use std::process::Command;

    let output = Command::new("osascript")
        .arg("-e")
        .arg(r#"POSIX path of (choose folder with prompt "Select music folder")"#)
        .output()
        .map_err(|error| format!("Could not open folder picker: {error}"))?;

    if output.status.success() {
        let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
        return Ok((!path.is_empty()).then_some(path));
    }

    let stderr = String::from_utf8_lossy(&output.stderr);
    if stderr.contains("User canceled") || stderr.contains("-128") {
        return Ok(None);
    }

    Err(format!("Folder picker failed: {}", stderr.trim()))
}

#[cfg(not(target_os = "macos"))]
fn pick_music_folder_impl() -> Result<Option<String>, String> {
    Err("Native folder browsing is not available on this platform yet.".to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![pick_music_folder])
        .run(tauri::generate_context!())
        .expect("failed to run Music Manager");
}
