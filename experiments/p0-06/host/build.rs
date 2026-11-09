fn main() {
    #[cfg(feature = "window")]
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&["host_request","window_report"])
    )).expect("Tauri build");
}
