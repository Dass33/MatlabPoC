use axum::{
    extract::Path,
    http::{header, StatusCode},
    response::{IntoResponse, Response},
};

/// Serve embedded static files from the `static/` directory.
/// Files are read from the filesystem at runtime (debug) or can be embedded at compile time.
pub async fn serve(Path(path): Path<String>) -> Response {
    let safe_path = path.trim_start_matches('/');
    let file_path = std::path::Path::new("static").join(safe_path);

    match std::fs::read(&file_path) {
        Ok(bytes) => {
            let mime = mime_guess::from_path(&file_path).first_or_octet_stream();
            (
                [(header::CONTENT_TYPE, mime.to_string())],
                bytes,
            ).into_response()
        }
        Err(_) => (StatusCode::NOT_FOUND, format!("Not found: {safe_path}")).into_response(),
    }
}
