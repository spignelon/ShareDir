import os
import io
import re
import socket
import zipfile
import base64
import mimetypes
import threading
import qrcode
from datetime import datetime, timezone
from flask import (
    Flask,
    send_file,
    request,
    abort,
    jsonify,
    render_template_string,
    redirect,
    Response,
    make_response,
)
from xkcdpass import xkcd_password as xp
from argparse import ArgumentParser
from time import time
from urllib.parse import quote
from werkzeug.utils import secure_filename

# Dictionary to store failed attempts
failed_attempts = {}
blacklist = {}

# Thresholds
MAX_FAILED_ATTEMPTS = 10
TIME_WINDOW = 60  # 1 minute
BLACKLIST_DURATION = 4 * 60 * 60  # 4 hours in seconds

# Server start time (set in main)
server_start_time = None
server_expire_seconds = None


def generate_passphrase(num_words):
    wordfile = xp.locate_wordfile()
    words = xp.generate_wordlist(wordfile=wordfile, min_length=3, max_length=8)
    return xp.generate_xkcdpassword(words, numwords=num_words, delimiter="-")


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def is_blacklisted(ip):
    if ip in blacklist:
        if time() < blacklist[ip]:
            return True
        else:
            del blacklist[ip]
    return False


def log_failed_attempt(ip):
    now = time()
    if ip not in failed_attempts:
        failed_attempts[ip] = []
    failed_attempts[ip] = [
        attempt for attempt in failed_attempts[ip] if now - attempt < TIME_WINDOW
    ]
    failed_attempts[ip].append(now)
    if len(failed_attempts[ip]) >= MAX_FAILED_ATTEMPTS:
        blacklist[ip] = now + BLACKLIST_DURATION
        del failed_attempts[ip]


def human_readable_size(size_bytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_file_info(filepath):
    stat = os.stat(filepath)
    size = human_readable_size(stat.st_size)
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M"
    )
    mime, _ = mimetypes.guess_type(filepath)
    if not mime:
        mime = "application/octet-stream"
    return {"size": size, "mtime": mtime, "mime": mime}


def generate_qr_base64(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    from qrcode.image.pure import PyPNGImage
    img = qr.make_image(image_factory=PyPNGImage)
    buf = io.BytesIO()
    img.save(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def parse_expire(value):
    """Parse expire string like '30m', '2h', '1d' into seconds."""
    m = re.match(r"^(\d+)\s*([smhd])$", value.strip().lower())
    if not m:
        raise ValueError(
            f"Invalid expire format '{value}'. Use e.g. 30m, 2h, 1d"
        )
    num = int(m.group(1))
    unit = m.group(2)
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return num * multipliers[unit]


def serve_file_with_range(filepath):
    """Serve a file supporting HTTP Range requests for video seeking."""
    file_size = os.path.getsize(filepath)
    range_header = request.headers.get("Range")

    mime, _ = mimetypes.guess_type(filepath)
    if not mime:
        mime = "application/octet-stream"

    if range_header:
        # Parse range header: bytes=start-end
        m = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if m:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else file_size - 1
            end = min(end, file_size - 1)
            if start > end or start >= file_size:
                resp = Response("Range not satisfiable", status=416)
                resp.headers["Content-Range"] = f"bytes */{file_size}"
                return resp
            length = end - start + 1

            def generate():
                with open(filepath, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(65536, remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            resp = Response(generate(), status=206, mimetype=mime)
            resp.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            resp.headers["Content-Length"] = str(length)
            resp.headers["Accept-Ranges"] = "bytes"
            return resp

    # No range requested — full file
    resp = make_response(send_file(filepath, mimetype=mime))
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Content-Length"] = str(file_size)
    return resp


def create_http_server(path, passphrase, allow_upload=False):
    app = Flask(__name__)
    is_file = os.path.isfile(path)

    app.jinja_env.filters["encode_path"] = lambda p: "/".join(
        quote(segment, safe="") for segment in p.split("/")
    )

    def check_auth():
        ip = request.remote_addr
        if is_blacklisted(ip):
            abort(
                Response(
                    jsonify(
                        error="Too many failed attempts. You are blacklisted for 4 hours."
                    ).get_data(as_text=True),
                    status=403,
                    mimetype="application/json",
                )
            )
        if passphrase is not None:
            if request.args.get("passphrase") != passphrase:
                if request.args.get("passphrase") is not None:
                    log_failed_attempt(ip)
                    print(
                        "Incorrect passphrase from",
                        ip,
                    )
                abort(403)

    def safe_path(req_path):
        abs_path = os.path.join(path, req_path)
        real_shared = os.path.realpath(path)
        real_abs = os.path.realpath(abs_path)
        if not (
            real_abs == real_shared or real_abs.startswith(real_shared + os.sep)
        ):
            abort(403)
        return abs_path

    def passphrase_qs():
        return f"?passphrase={passphrase}" if passphrase is not None else ""

    @app.before_request
    def check_expiry():
        if server_expire_seconds is not None and server_start_time is not None:
            elapsed = time() - server_start_time
            if elapsed >= server_expire_seconds:
                remaining = "0s"
                print("Server expired. Shutting down.")
                os._exit(0)

    @app.after_request
    def access_log(response):
        ip = request.remote_addr
        method = request.method
        req_path = request.full_path.rstrip("?")
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        status = response.status_code
        print(f"[{ts}] {ip} {method} {req_path} -> {status}")
        return response

    @app.route("/__qr__")
    def qr_page():
        check_auth()
        url = request.url_root.rstrip("/") + "/" + passphrase_qs()
        qr_b64 = generate_qr_base64(url)
        return render_template_string(
            QR_TEMPLATE, qr_b64=qr_b64, url=url, passphrase_param=passphrase_qs()
        )

    @app.route("/__upload__", methods=["POST"])
    def upload():
        if not allow_upload:
            abort(404)
        check_auth()
        upload_path = request.form.get("upload_path", "")
        if is_file:
            abort(400)
        dest_dir = safe_path(upload_path)
        if not os.path.isdir(dest_dir):
            abort(400)
        uploaded = request.files.getlist("files")
        if not uploaded:
            abort(400)
        for f in uploaded:
            if f.filename:
                filename = secure_filename(f.filename)
                if not filename:
                    continue
                f.save(os.path.join(dest_dir, filename))
        redir = "/" + upload_path if upload_path else "/"
        return redirect(redir + passphrase_qs())

    @app.route("/__zip__/<path:req_path>")
    @app.route("/__zip__/", defaults={"req_path": ""})
    def zip_download(req_path):
        check_auth()
        if is_file:
            abort(404)
        abs_path = safe_path(req_path)
        if not os.path.isdir(abs_path):
            abort(404)

        def generate():
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(abs_path):
                    real_shared = os.path.realpath(path)
                    real_root = os.path.realpath(root)
                    if not (
                        real_root == real_shared
                        or real_root.startswith(real_shared + os.sep)
                    ):
                        continue
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        arcname = os.path.relpath(fpath, abs_path)
                        zf.write(fpath, arcname)
            buf.seek(0)
            yield buf.read()

        dirname = os.path.basename(abs_path.rstrip("/")) or "download"
        return Response(
            generate(),
            mimetype="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{dirname}.zip"'
            },
        )

    @app.route("/", defaults={"req_path": ""})
    @app.route("/<path:req_path>")
    def dir_listing(req_path):
        check_auth()

        if is_file:
            if req_path and req_path != os.path.basename(path):
                return jsonify({"error": "Path not found"}), 404
            return serve_file_with_range(path)

        abs_path = safe_path(req_path)
        if not os.path.exists(abs_path):
            return jsonify({"error": "Path not found"}), 404
        if os.path.isfile(abs_path):
            return serve_file_with_range(abs_path)

        items = os.listdir(abs_path)
        directories = sorted(
            [item for item in items if os.path.isdir(os.path.join(abs_path, item))]
        )
        file_names = sorted(
            [item for item in items if os.path.isfile(os.path.join(abs_path, item))]
        )
        files_info = []
        for fname in file_names:
            fpath = os.path.join(abs_path, fname)
            info = get_file_info(fpath)
            files_info.append(
                {
                    "name": fname,
                    "size": info["size"],
                    "mtime": info["mtime"],
                    "mime": info["mime"],
                }
            )

        pp = passphrase_qs()

        return render_template_string(
            LISTING_TEMPLATE,
            req_path=req_path,
            directories=directories,
            files=files_info,
            passphrase_param=pp,
            allow_upload=allow_upload,
        )

    return app


# ── Templates ────────────────────────────────────────────────────────

QR_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QR Code - ShareDir</title>
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           display: flex; flex-direction: column; align-items: center; justify-content: center;
           min-height: 100vh; margin: 0; background: #181818; color: #e0e0e0; }
    .light-mode { background: #f5f7fa; color: #333; }
    img { max-width: 350px; margin: 20px; border-radius: 12px; }
    .url-box { word-break: break-all; max-width: 550px; text-align: center;
               padding: 14px 18px; background: #242424; border-radius: 10px; margin: 10px;
               border: 1px solid #333; }
    .light-mode .url-box { background: #fff; border-color: #ddd; }
    a { color: #58a6ff; }
    .light-mode a { color: #2980b9; }
    .back { margin-top: 20px; font-size: 15px; }
</style>
</head>
<body>
<script>if(localStorage.getItem('dark-mode')!=='disabled'){}else{document.body.classList.add('light-mode');}</script>
<h1>Scan to Access</h1>
<img src="data:image/png;base64,{{ qr_b64 }}" alt="QR Code">
<div class="url-box"><a href="{{ url }}">{{ url }}</a></div>
<a class="back" href="/{{ passphrase_param }}">← Back to files</a>
</body>
</html>
"""

LISTING_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShareDir{% if req_path %} - {{ req_path }}{% endif %}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #181818; color: #e0e0e0; padding: 20px;
               transition: background .2s, color .2s; }

        /* ── Light mode (opt-in) ── */
        .light-mode { background: #f5f7fa; color: #333; }

        .header { display: flex; align-items: center; justify-content: space-between;
                   background: #242424; color: #e0e0e0; padding: 12px 18px;
                   border-radius: 10px; margin-bottom: 16px; border: 1px solid #333; }
        .light-mode .header { background: #3498db; color: #fff; border-color: #3498db; }
        .header h1 { font-size: 1.2em; }
        .header-buttons { display: flex; gap: 8px; align-items: center; }
        .header-buttons button, .header-buttons a {
            background: rgba(255,255,255,0.1); color: #e0e0e0; border: none; padding: 8px 12px;
            border-radius: 6px; cursor: pointer; text-decoration: none; font-size: 14px; }
        .light-mode .header-buttons button, .light-mode .header-buttons a {
            background: rgba(255,255,255,0.25); color: #fff; }
        .header-buttons button:hover, .header-buttons a:hover { background: rgba(255,255,255,0.2); }

        .search-box { width: 100%; padding: 10px 14px; font-size: 15px;
                       border: 1px solid #333; border-radius: 8px; margin-bottom: 14px;
                       outline: none; background: #242424; color: #e0e0e0; }
        .search-box:focus { border-color: #58a6ff; }
        .light-mode .search-box { background: #fff; border-color: #ddd; color: #333; }
        .light-mode .search-box:focus { border-color: #3498db; }

        table { width: 100%; border-collapse: collapse; background: #242424;
                border-radius: 10px; overflow: hidden; border: 1px solid #333; }
        .light-mode table { background: #fff; border-color: #e0e0e0;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
        th { background: #1e1e1e; text-align: left; padding: 10px 14px; font-size: 13px;
             text-transform: uppercase; color: #888; border-bottom: 1px solid #333; }
        .light-mode th { background: #f0f0f0; color: #666; border-bottom-color: #e0e0e0; }
        td { padding: 10px 14px; border-top: 1px solid #2a2a2a; font-size: 15px; vertical-align: middle; }
        .light-mode td { border-top-color: #f0f0f0; }
        tr:hover { background: #2a2a2a; }
        .light-mode tr:hover { background: #f9fbfd; }

        .name-cell { display: flex; align-items: center; gap: 8px; }
        .icon { font-size: 18px; flex-shrink: 0; }

        a { text-decoration: none; color: #58a6ff; }
        a:hover { text-decoration: underline; }
        .light-mode a { color: #2980b9; }

        a.folder-link { color: #3fb950; font-weight: 600; }
        .light-mode a.folder-link { color: #27ae60; }

        .meta { color: #888; font-size: 13px; }

        .dl-btn { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px;
                  background: #1f6feb; color: #fff; border-radius: 5px; font-size: 12px;
                  text-decoration: none; white-space: nowrap; }
        .dl-btn:hover { background: #388bfd; text-decoration: none; }
        .dl-btn.zip { background: #8957e5; }
        .dl-btn.zip:hover { background: #a371f7; }
        .light-mode .dl-btn { background: #3498db; }
        .light-mode .dl-btn:hover { background: #217dbb; }
        .light-mode .dl-btn.zip { background: #8e44ad; }
        .light-mode .dl-btn.zip:hover { background: #6c3483; }

        .upload-area { margin: 16px 0; padding: 20px; background: #242424;
                        border: 2px dashed #444; border-radius: 10px; text-align: center;
                        transition: border-color .2s, background .2s; }
        .upload-area.dragover { border-color: #58a6ff; background: #1a2a3a; }
        .light-mode .upload-area { background: #fff; border-color: #ccc; }
        .light-mode .upload-area.dragover { border-color: #3498db; background: #eef6fc; }
        .upload-area input[type=file] { margin: 8px 0; }
        .upload-btn { padding: 8px 20px; background: #238636; color: #fff; border: none;
                      border-radius: 6px; cursor: pointer; font-size: 14px; }
        .upload-btn:hover { background: #2ea043; }
        .light-mode .upload-btn { background: #27ae60; }
        .light-mode .upload-btn:hover { background: #1e8449; }
        .progress-bar-container { width: 100%; background: #333; border-radius: 6px;
                                   margin-top: 10px; height: 24px; display: none; overflow: hidden; }
        .light-mode .progress-bar-container { background: #e0e0e0; }
        .progress-bar { height: 100%; background: #238636; border-radius: 6px;
                        transition: width 0.3s; width: 0%; display: flex;
                        align-items: center; justify-content: center;
                        font-size: 12px; color: #fff; font-weight: bold; }

        @media (max-width: 700px) {
            .hide-sm { display: none; }
            td, th { padding: 8px 6px; }
        }
    </style>
</head>
<body>
<script>
    // Default to dark mode. Only go light if user explicitly chose it.
    if (localStorage.getItem('dark-mode') === 'disabled') {
        document.body.classList.add('light-mode');
    }
</script>

<div class="header">
    <h1>📂 {% if req_path %}{{ req_path }}{% else %}Home{% endif %}</h1>
    <div class="header-buttons">
        {% if req_path %}
        <a href="/{{ passphrase_param }}" title="Home">🏠</a>
        {% endif %}
        <a href="/__zip__/{{ req_path }}{{ passphrase_param }}" title="Download folder as ZIP" class="dl-btn zip">📦 ZIP</a>
        <a href="/__qr__{{ passphrase_param }}" title="Show QR Code">📱 QR</a>
        <button id="dark-mode-toggle" title="Toggle dark/light mode">🌙</button>
    </div>
</div>

<input type="text" class="search-box" id="searchBox" placeholder="🔍 Search files and folders..." autocomplete="off">

{% if allow_upload %}
<div class="upload-area" id="uploadArea">
    <form id="uploadForm" method="POST" action="/__upload__{{ passphrase_param }}" enctype="multipart/form-data">
        <input type="hidden" name="upload_path" value="{{ req_path }}">
        <p><strong>Upload files</strong> — drag & drop or click to select</p>
        <input type="file" name="files" id="fileInput" multiple>
        <br>
        <button type="submit" class="upload-btn">⬆ Upload</button>
    </form>
    <div class="progress-bar-container" id="progressContainer">
        <div class="progress-bar" id="progressBar">0%</div>
    </div>
</div>
{% endif %}

<table id="listing">
<thead>
    <tr>
        <th>Name</th>
        <th class="hide-sm">Size</th>
        <th class="hide-sm">Modified</th>
        <th class="hide-sm">Type</th>
        <th></th>
    </tr>
</thead>
<tbody>
{% for directory in directories %}
    <tr class="item-row">
        <td><div class="name-cell"><span class="icon">📁</span>
            <a class="folder-link" href="{{ ('/' + req_path + '/' + directory if req_path else '/' + directory) | encode_path }}{{ passphrase_param }}">{{ directory }}</a>
        </div></td>
        <td class="meta hide-sm">—</td>
        <td class="meta hide-sm">—</td>
        <td class="meta hide-sm">Folder</td>
        <td><a class="dl-btn zip" href="/__zip__/{{ (req_path + '/' + directory if req_path else directory) | encode_path }}{{ passphrase_param }}" title="Download as ZIP">📦 ZIP</a></td>
    </tr>
{% endfor %}
{% for file in files %}
    <tr class="item-row">
        <td><div class="name-cell"><span class="icon">📄</span>
            <a href="{{ ('/' + req_path + '/' + file.name if req_path else '/' + file.name) | encode_path }}{{ passphrase_param }}">{{ file.name }}</a>
        </div></td>
        <td class="meta hide-sm">{{ file.size }}</td>
        <td class="meta hide-sm">{{ file.mtime }}</td>
        <td class="meta hide-sm">{{ file.mime }}</td>
        <td><a class="dl-btn" href="{{ ('/' + req_path + '/' + file.name if req_path else '/' + file.name) | encode_path }}{{ passphrase_param }}" download title="Download">⬇ DL</a></td>
    </tr>
{% endfor %}
</tbody>
</table>

<script>
    // Dark/light mode toggle (defaults dark)
    const toggle = document.getElementById('dark-mode-toggle');
    function updateToggleIcon() {
        toggle.textContent = document.body.classList.contains('light-mode') ? '☀️' : '🌙';
    }
    updateToggleIcon();
    toggle.addEventListener('click', () => {
        document.body.classList.toggle('light-mode');
        localStorage.setItem('dark-mode', document.body.classList.contains('light-mode') ? 'disabled' : 'enabled');
        updateToggleIcon();
    });

    // Search / filter
    const search = document.getElementById('searchBox');
    search.addEventListener('input', () => {
        const q = search.value.toLowerCase();
        document.querySelectorAll('.item-row').forEach(row => {
            const name = row.querySelector('.name-cell').textContent.toLowerCase();
            row.style.display = name.includes(q) ? '' : 'none';
        });
    });

    {% if allow_upload %}
    // Upload with progress bar
    const form = document.getElementById('uploadForm');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // Drag & drop visual feedback
    uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
    uploadArea.addEventListener('dragleave', () => { uploadArea.classList.remove('dragover'); });
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        fileInput.files = e.dataTransfer.files;
    });

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const xhr = new XMLHttpRequest();
        progressContainer.style.display = 'block';
        xhr.upload.addEventListener('progress', (ev) => {
            if (ev.lengthComputable) {
                const pct = Math.round((ev.loaded / ev.total) * 100);
                progressBar.style.width = pct + '%';
                progressBar.textContent = pct + '%';
            }
        });
        xhr.addEventListener('load', () => {
            progressBar.style.width = '100%';
            progressBar.textContent = 'Done!';
            setTimeout(() => { window.location.reload(); }, 500);
        });
        xhr.addEventListener('error', () => {
            progressBar.textContent = 'Error!';
            progressBar.style.background = '#da3633';
        });
        xhr.open('POST', form.action);
        xhr.send(formData);
    });
    {% endif %}
</script>
</body>
</html>
"""


def display_qr_code(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii()


def main():
    global server_start_time, server_expire_seconds

    parser = ArgumentParser(description="Share a directory or file over HTTP.")
    parser.add_argument(
        "path",
        help="Path to the directory or file to be shared (relative or absolute).",
    )
    parser.add_argument(
        "-p",
        "--passphrase-length",
        type=int,
        default=4,
        help="Number of words in the passphrase (default: 4).",
    )
    parser.add_argument(
        "--no-passphrase",
        action="store_true",
        help="Disable passphrase protection (not recommended on public networks).",
    )
    parser.add_argument(
        "-P",
        "--port",
        type=int,
        default=44447,
        help="Port to run the HTTP server on (default: 44447).",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=1,
        help="Number of server workers (default: 1).",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Allow file uploads via the web interface.",
    )
    parser.add_argument(
        "--expire",
        type=str,
        default=None,
        help="Auto-shutdown after duration, e.g. 30m, 2h, 1d.",
    )
    args = parser.parse_args()

    shared_path = os.path.abspath(args.path)
    if not os.path.exists(shared_path):
        print(f"The provided path '{shared_path}' does not exist.")
        exit(1)

    if args.expire:
        try:
            server_expire_seconds = parse_expire(args.expire)
        except ValueError as e:
            print(str(e))
            exit(1)
        print(f"Server will expire after {args.expire}.")

    if args.no_passphrase:
        passphrase = None
        print("Passphrase protection disabled.")
    else:
        passphrase = generate_passphrase(args.passphrase_length)
        print(f"Generated passphrase: {passphrase}")

    ip_address = get_lan_ip()
    http_port = args.port
    if passphrase is not None:
        url = f"http://{ip_address}:{http_port}/?passphrase={passphrase}"
    else:
        url = f"http://{ip_address}:{http_port}/"
    print(f"Access URL: {url}")

    display_qr_code(url)

    app = create_http_server(shared_path, passphrase, allow_upload=args.upload)

    server_start_time = time()

    # Schedule shutdown if expire is set
    if server_expire_seconds is not None:
        def expire_timer():
            import time as t
            t.sleep(server_expire_seconds)
            print(f"\nServer expired after {args.expire}. Shutting down.")
            os._exit(0)

        timer = threading.Thread(target=expire_timer, daemon=True)
        timer.start()

    from waitress import serve

    num_threads = args.workers * 4
    print(
        f"Starting server on 0.0.0.0:{http_port} with {args.workers} workers ({num_threads} threads)..."
    )
    serve(app, host="0.0.0.0", port=http_port, threads=num_threads)


if __name__ == "__main__":
    main()
