import os
import socket
import mimetypes

# ensure common types exist even in slim images
mimetypes.init()
mimetypes.add_type("application/pdf", ".pdf")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("text/html; charset=utf-8", ".html")

import sys
from urllib.parse import unquote, quote
import datetime
from typing import Optional

PORT = int(os.environ.get("PORT", "8000"))
ALLOWED_EXTENSIONS = {".html", ".png", ".pdf"}


def html_escape(s: str) -> str:
    """Minimal HTML escape for text content."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def file_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def find_file_recursive(root_dir: str, filename: str) -> Optional[str]:
    """Search for a file recursively in root_dir. Returns absolute path or None."""
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if filename in filenames:
            return os.path.join(dirpath, filename)
    return None


def respond(conn, status, headers, body):
    head = [f"HTTP/1.1 {status}".encode()]
    for k, v in headers.items():
        head.append(f"{k}: {v}".encode())
    head.append(b"")
    head.append(b"")
    conn.sendall(b"\r\n".join(head) + body)


def _is_subpath(child: str, parent: str) -> bool:
    child_real = os.path.realpath(child)
    parent_real = os.path.realpath(parent)
    try:
        return os.path.commonpath([child_real, parent_real]) == parent_real
    except ValueError:
        return False


def _minimal_listing_html(req_path: str, abs_dir: str) -> bytes:
    try:
        entries = sorted(os.listdir(abs_dir))
    except OSError:
        return b"<html><body><h1>Forbidden</h1></body></html>"

    esc_path = html_escape(req_path)

    lines = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<link rel='preconnect' href='https://fonts.googleapis.com'>",
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>",
        "<link href='https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400;700&display=swap' rel='stylesheet'>",
        "<link href='https://fonts.googleapis.com/css2?family=Snowburst+One&display=swap' rel='stylesheet'>",
        f"<title>Content of {esc_path}</title>",
        "<style>",
        # winter palette
        ":root{--bg:#E9F3FF;--card:#F8FBFF;--text:#1F2A44;--muted:#5F7390;--link:#2B6CB0;--row:#EAF3FF;--border:#D8E8FF}",
        "*{box-sizing:border-box}",
        "body{margin:0; padding:28px 16px;background:linear-gradient(180deg,#ECF5FF 0%, var(--bg) 100%);color:var(--text);"
        "     font:14px/1.5 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif}",
        "header{max-width:960px;margin:0 auto 12px;position:relative;z-index:1}",
        "h1{margin:0 0 8px;font-size:20px;font-weight:600}",
        "main{max-width:960px;margin:0 auto;background:var(--card);border-radius:14px;"
        "     padding:8px;box-shadow:0 8px 24px rgba(16,46,86,.18);position:relative;z-index:1}",
        "table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden}",
        "thead th{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--border);"
        "         text-align:left;font-weight:600;color:var(--muted);padding:12px 14px}",
        "tbody tr{background:var(--row)}",
        "tbody tr:nth-child(even){background:transparent}",
        "td{padding:10px 14px;border-bottom:1px solid var(--border)}",
        "a{color:var(--link);text-decoration:none}",
        "a:hover{text-decoration:underline}",
        "tr.dir td:first-child a::before{content:'📁  '}",
        "tr.file td:first-child a::before{content:'📄  '}",
        "tr.up   td:first-child a::before{content:'⬆  '}",
        "td:nth-child(2),td:nth-child(3){color:var(--muted);white-space:nowrap}",
        "@media (max-width: 640px){ thead th:nth-child(3), td:nth-child(3){display:none} }",
        ".parent-link{margin-bottom:8px; margin-top:8px; display:block;font-weight:600}",
        ".title-lab{font-family:'Snowburst One', cursive; color:#E8F4FF; font-size:64px; margin-bottom:16px; margin-top:4px;"
        "            text-shadow:0 2px 0 rgba(43,108,176,.22), 0 6px 16px rgba(0,40,80,.25)}",
        ".center-title{display:flex; text-align:center; align-items:center; justify-content:center;}",

        # snow layer behind content
        "#snow{position:fixed; inset:0; pointer-events:none; overflow:hidden; z-index:0}",
        ".snowflake{position:absolute; top:-10px; left:0; animation:sway var(--swayDur) ease-in-out infinite alternate}",
        ".flake{display:block; color:#fff; opacity:.92; filter:drop-shadow(0 0 4px rgba(255,255,255,.7));"
        "       font-size:var(--size); animation:fall var(--dur) linear infinite;}",
        "@keyframes fall{to{transform:translateY(110vh)}}",
        "@keyframes sway{from{transform:translateX(0)} to{transform:translateX(var(--sway))}}",
        "</style>",
        "</head>",
        "<body>",
        "<div id='snow' aria-hidden='true'></div>",
        "<header>",
        "<div class='center-title'>",
        "<h1 class='title-lab'>Catalina&#x27;s 1st PR LAB</h1>",
        "</div>",
        f"<h2>Content of {esc_path}</h2>",
        "</header>",
        "<main>",
    ]

    # Parent directory link
    if req_path != "/":
        parent = req_path.rstrip("/").rsplit("/", 1)[0]
        parent = "/" if not parent else parent + "/"
        lines.append(f'<a class="parent-link" href="{quote(parent)}">⬆ Parent directory</a>')

    # Table
    lines.extend([
        "<table>",
        "<thead><tr><th>Name</th><th>Size</th><th>Last modified</th></tr></thead>",
        "<tbody>"
    ])

    for name in entries:
        full = os.path.join(abs_dir, name)
        is_dir = os.path.isdir(full)
        href = quote(name) + ("/" if is_dir else "")
        row_class = "dir" if is_dir else "file"
        size = "—" if is_dir else file_size(os.path.getsize(full))
        ts = os.path.getmtime(full)
        mtime = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        safe_name = html_escape(name)
        display_name = safe_name + ("/" if is_dir else "")
        lines.append(
            f'<tr class="{row_class}">'
            f'<td><a href="{href}">{display_name}</a></td>'
            f"<td>{size}</td><td>{mtime}</td>"
            f"</tr>"
        )

    # Close table/main and add snow script
    lines.extend([
        "</tbody></table>",
        "</main>",
        "<script>",
        "(function(){",
        "  const snow = document.getElementById('snow');",
        "  if(!snow) return;",
        "  const COUNT = 90;",
        "  const SYM = ['❅','❆','✼','✻','✽','✾'];",
        "  for(let i=0;i<COUNT;i++){",
        "    const wrap = document.createElement('div'); wrap.className='snowflake';",
        "    const inner = document.createElement('span'); inner.className='flake';",
        "    inner.textContent = SYM[Math.floor(Math.random()*SYM.length)];",
        "    const size = (Math.random()*0.9 + 0.6) * 16;",
        "    const dur = (Math.random()*8 + 8) + 's';",
        "    const swayDur = (Math.random()*4 + 3) + 's';",
        "    const left = Math.random()*100 + 'vw';",
        "    const delay = (-Math.random()*12) + 's';",
        "    const sway = (Math.random()*40 - 20) + 'px';",
        "    wrap.style.left = left;",
        "    wrap.style.animationDuration = swayDur;",
        "    wrap.style.setProperty('--sway', sway);",
        "    inner.style.setProperty('--dur', dur);",
        "    inner.style.setProperty('--size', size + 'px');",
        "    inner.style.animationDelay = delay;",
        "    wrap.appendChild(inner); snow.appendChild(wrap);",
        "  }",
        "})();",
        "</script>",
        "</body></html>"
    ])

    return "\n".join(lines).encode("utf-8")


def _respond_301(conn, location: str):
    body = (f"<html><body>Moved: <a href=\"{location}\">{location}</a></body></html>").encode("utf-8")
    respond(conn, "301 Moved Permanently",
            {"Location": location,
             "Content-Type": "text/html; charset=utf-8",
             "Content-Length": str(len(body)),
             "Connection": "close"},
            body)


def _respond_404(conn):
    body = b"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href='https://fonts.googleapis.com/css2?family=Snowburst+One&display=swap' rel='stylesheet'>
            <title>404 Not Found</title>
            <style>
                :root{--bg:#E9F3FF;--card:#F8FBFF;--text:#1F2A44;--muted:#5F7390;--link:#2B6CB0;}
                body{
                    margin:0; padding:0; display:flex; justify-content:center; align-items:center;
                    height:100vh; background:linear-gradient(180deg,#ECF5FF 0%, var(--bg) 100%);
                    color:var(--text); font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                }
                .container{max-width:600px; text-align:center; background:var(--card); padding:24px 28px; border-radius:16px;
                           box-shadow:0 8px 24px rgba(16,46,86,.18)}
                h1{font-size:64px; margin:0 0 12px; font-family:'Snowburst One', cursive; color:#E8F4FF;
                   text-shadow:0 2px 0 rgba(43,108,176,.22), 0 6px 16px rgba(0,40,80,.25)}
                p{font-size:18px; color:var(--muted); margin:6px 0}
                a{color:var(--link); text-decoration:none; font-weight:600}
                a:hover{text-decoration:underline}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>404</h1>
                <p>Oops! The page you are looking for does not exist.</p>
                <p>Go back to the <a href="/">homepage</a></p>
            </div>
        </body>
        </html>
        """
    respond(conn, "404 Not Found",
            {"Content-Type": "text/html; charset=utf-8",
             "Content-Length": str(len(body)),
             "Connection": "close"},
            body)


def main():
    if len(sys.argv) != 2:
        print("Usage: python server.py <directory>")
        sys.exit(1)

    root_dir = sys.argv[1]
    if not os.path.isdir(root_dir):
        print(f"Error: Directory '{root_dir}' does not exist.")
        sys.exit(1)

    root_dir = os.path.abspath(root_dir)
    content_dir = root_dir  # Always serve the root directory

    print(f"Serving directory: {content_dir}")

    # creates new tcp socket with IPv4 and TCP
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # allows restart without "Address already in use"
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PORT))

    # handles one client at a time (Lab 1 requirement)
    s.listen(1)
    print(f"Server running on http://0.0.0.0:{PORT}")
    print(f"Access locally: http://localhost:{PORT}")
    print(f"Press Ctrl+C to stop")

    while True:
        conn, addr = s.accept()
        print(f"Connection from {addr}")
        try:
            data = conn.recv(4096)
            line = data.split(b"\r\n", 1)[0].decode(errors="replace")
            print(f"Request: {line}")
            parts = line.split()
            if len(parts) != 3:
                respond(conn, "400 Bad Request",
                        {"Content-Type": "text/plain", "Connection": "close"},
                        b"Bad Request")
                continue

            method, target, version = parts
            if method != "GET":
                respond(conn, "405 Method Not Allowed",
                        {"Allow": "GET", "Content-Type": "text/plain", "Connection": "close"},
                        b"Only GET is allowed")
                continue

            # ensure URL path starts with "/"
            if not target.startswith("/"):
                target = "/"

            # decode URL encoded characters
            target = unquote(target)
            # map URL to relative path under root
            requested_rel = "" if target == "/" else target.lstrip("/")
            requested_abs = os.path.realpath(os.path.join(content_dir, requested_rel))

            # 1) reject traversal
            if not _is_subpath(requested_abs, content_dir):
                _respond_404(conn)
                continue

            # 2) if it's a directory
            if os.path.isdir(requested_abs):
                # enforce trailing slash for directories
                if not target.endswith("/"):
                    _respond_301(conn, target + "/")
                    continue

                # always show listing
                body = _minimal_listing_html(target, requested_abs)
                respond(conn, "200 OK",
                        {"Content-Type": "text/html; charset=utf-8",
                         "Content-Length": str(len(body)),
                         "Connection": "close"},
                        body)
                continue

            # 3) regular file flow
            if not os.path.isfile(requested_abs):
                filename = os.path.basename(requested_rel)
                found_path = find_file_recursive(content_dir, filename)
                if found_path:
                    requested_abs = found_path
                    print(f"Found file via recursive search: {found_path}")
                else:
                    _respond_404(conn)
                    continue

            ext = os.path.splitext(requested_abs)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                _respond_404(conn)
                continue

            mime_type, _ = mimetypes.guess_type(requested_abs)
            if mime_type is None:
                _respond_404(conn)
                continue

            try:
                with open(requested_abs, "rb") as f:
                    body = f.read()
                respond(conn, "200 OK",
                        {"Content-Type": mime_type,
                         "Content-Length": str(len(body)),
                         "Connection": "close"},
                        body)
                print(f"Served: {requested_rel} ({mime_type})")
            except OSError:
                respond(conn, "500 Internal Server Error",
                        {"Content-Type": "text/plain", "Connection": "close"},
                        b"Internal Server Error")

        except Exception as e:
            print(f"Error handling request: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    main()