from html import escape


STYLE = """
:root { --ink: #1a1a1a; --paper: #ffffff; --block: #1a1a1a; --muted: #666; }
body { margin: 0; padding: 24px 16px; background: var(--paper); color: var(--ink);
       font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 960px; margin: 0 auto; }
h1 { font-size: 1.4rem; margin: 0 0 16px; }
.clues { display: flex; flex-wrap: wrap; gap: 32px; }
.clues h2 { font-size: 1rem; margin: 0 0 8px; letter-spacing: 0.05em; }
.clues ol { list-style: none; margin: 0; padding: 0; }
.clues li { margin: 2px 0; }
.clues .n { display: inline-block; min-width: 1.8em; font-weight: 600; }
main.wide { max-width: none; }
/* The sidebar takes the height of whatever sits beside it and scrolls its
   own list: its content is taken out of the flow, so it can't stretch the row */
.side { flex: 0 0 220px; position: relative; min-height: 12rem;
        border-left: 1px solid #ddd; padding-left: 24px; }
.side-inner { position: absolute; inset: 0 0 0 24px; display: flex; flex-direction: column; }
.side h2 { font-size: 1rem; margin: 0 0 8px; letter-spacing: 0.05em; }
.side ul { list-style: none; margin: 0; padding: 0 8px 0 0; flex: 0 1 auto; min-height: 0; overflow-y: auto; }
.side li { display: flex; justify-content: space-between; align-items: center;
           padding: 4px 0; border-bottom: 1px solid #eee;
           font-weight: 600; text-transform: uppercase; }
.side li button { border: 0; background: none; color: var(--muted); cursor: pointer;
                  font-size: 1.1rem; line-height: 1; padding: 0 4px; }
.side li button:hover { color: #b00020; }
.side .hint { color: var(--muted); font-size: 0.8rem; margin: 8px 0 0; }
main.side-hidden .side { display: none; }
@media (max-width: 760px) {
  .side { flex-basis: 100%; min-height: 0; border-left: 0; padding-left: 0; }
  .side-inner { position: static; }
  .side ul { max-height: 40vh; }
}
@media print { body { padding: 0; } .side { display: none; } }
"""


def page(body, title="Crossword", wide=False):
    """Wrap body HTML in the standalone page shell. A wide page spans the whole window."""
    main_class = ' class="wide"' if wide else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{STYLE}</style>
</head>
<body>
<main{main_class}>
<h1>{escape(title)}</h1>
{body}
</main>
</body>
</html>
"""


def open_in_browser(target):
    """Open an HTML file path or http URL in the default browser (via Windows on WSL)"""
    import os
    import shutil
    import subprocess
    import webbrowser

    is_url = target.startswith(("http://", "https://"))
    if not is_url:
        target = os.path.abspath(target)

    if shutil.which("wslpath") and shutil.which("explorer.exe"):
        if not is_url:
            target = subprocess.run(["wslpath", "-w", target], capture_output=True, text=True).stdout.strip()
        # explorer.exe exits non-zero even on success, so don't check it
        subprocess.run(["explorer.exe", target])
    else:
        webbrowser.open(target if is_url else f"file://{target}")


def serve(port=8000, title="Crossword", open_browser=True, store_path=None):
    """Serve the sandbox on http://127.0.0.1:port.

    With store_path, the page's schemas are saved in that JSON file; without
    it, the page keeps them in the browser's localStorage.
    """
    from .sandbox import read_store, write_store

    import importlib
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse

    reload_lock = threading.Lock()

    def render_page():
        """Build the page from the code on disk, so a refresh shows edits to the page
        (changes to the server itself still need a restart)"""
        from . import sandbox, visualize
        with reload_lock:
            try:
                # sandbox takes page() from visualize, so reload visualize first
                importlib.reload(visualize)
                importlib.reload(sandbox)
            except Exception as e:
                print(f"Could not reload the page code, serving the last version that loaded: {e!r}")
            store = read_store(store_path) if store_path else None
            return sandbox.render_sandbox_page(title=title, store=store)

    class Handler(BaseHTTPRequestHandler):
        def send_html(self, html):
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def save_store(self):
            """Save the sandbox schemas the page sends as JSON"""
            length = int(self.headers.get("Content-Length", 0))
            try:
                write_store(store_path, json.loads(self.rfile.read(length).decode("utf-8")))
            except ValueError as e:
                self.send_error(400, str(e))
                return
            except OSError as e:
                print(f"Could not save {store_path}: {e}")
                self.send_error(500)
                return
            self.send_response(204)
            self.end_headers()

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/":
                self.send_html(render_page())
                return
            if url.path == "/sandbox":
                # The sandbox used to live here; keep old bookmarks working
                self.send_response(301)
                self.send_header("Location", "/")
                self.end_headers()
                return
            self.send_error(404)

        def do_POST(self):
            if urlparse(self.path).path == "/store" and store_path:
                self.save_store()
                return
            self.send_error(404)

    # Threaded, so an idle connection (browsers open spare ones) can't block every other request
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{server.server_port}/"
    print(f"Serving crossword sandbox at {url} (Ctrl+C to stop)")
    if store_path:
        print(f"Sandbox schemas are saved in {store_path}")
    if open_browser:
        open_in_browser(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m crossword.visualize",
        description="Serve the crossword sandbox locally, to lay out a crossword by hand.",
    )
    parser.add_argument("-s", "--store", metavar="FILE",
                        help="JSON file to save the schemas in (default: the browser's localStorage)")
    parser.add_argument("--title", default="Crossword", help="page title")
    parser.add_argument("--port", type=int, default=8000, help="port to serve on (default: 8000)")
    # Serving is the only mode now; these used to switch it on
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--sandbox", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    serve(port=args.port, title=args.title, store_path=args.store)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
