# client.py
import os, sys, socket

DEF_DIR = "./downloads"

def http_get(host: str, port: int, path: str) -> bytes:
    if not path.startswith("/"):
        path = "/" + path
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(req)
    chunks = []
    while True:
        data = s.recv(4096)
        if not data:
            break
        chunks.append(data)
    s.close()
    return b"".join(chunks)

def main():
    # Allow 3-arg (default dir) or 4-arg usage
    if len(sys.argv) not in (4, 5):
        print("Usage:")
        print("  python3 client.py <host> <port> <url_path>")
        print("  python3 client.py <host> <port> <url_path> <download_dir>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    url_path = sys.argv[3]
    out_dir = sys.argv[4] if len(sys.argv) == 5 else DEF_DIR

    # Make '0.0.0.0' work like the example by mapping to localhost
    if host in ("0.0.0.0", "::", "::0"):
        host = "localhost"

    raw = http_get(host, port, url_path)

    # Split headers/body
    try:
        head, body = raw.split(b"\r\n\r\n", 1)
    except ValueError:
        print("Invalid HTTP response")
        sys.exit(1)

    # Parse status + headers
    lines = head.decode("iso-8859-1").split("\r\n")
    status = lines[0].split(" ", 2)
    code = int(status[1]) if len(status) > 1 and status[1].isdigit() else 0

    headers = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            headers[k.strip().lower()] = v.strip()

    if code == 301 and "location" in headers:
        # simple one-level follow for directory slash redirects
        loc = headers["location"]
        raw = http_get(host, port, loc)
        head, body = raw.split(b"\r\n\r\n", 1)
        lines = head.decode("iso-8859-1").split("\r\n")
        status = lines[0].split(" ", 2)
        code = int(status[1]) if len(status) > 1 and status[1].isdigit() else 0
        headers = {}
        for ln in lines[1:]:
            if ":" in ln:
                k, v = ln.split(":", 1)
                headers[k.strip().lower()] = v.strip()

    if code != 200:
        print(f"Server returned {code}.")
        ctype = headers.get("content-type", "")
        if "text/html" in ctype:
            print(body.decode("utf-8", errors="replace")[:800])
        sys.exit(1)

    ctype = headers.get("content-type", "").lower()

    # HTML/listing -> print to stdout; PNG/PDF -> save to file
    if ctype.startswith("text/html"):
        print(body.decode("utf-8", errors="replace"))
        return

    os.makedirs(out_dir, exist_ok=True)  # harmless if already exists
    filename = url_path.rsplit("/", 1)[-1] or "download.bin"
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "wb") as f:
        f.write(body)
    print(f"Saved to: {out_path}")

if __name__ == "__main__":
    main()