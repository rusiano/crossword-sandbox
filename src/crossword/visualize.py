import re
from html import escape


# A word is a run of letters, optionally joined by apostrophes or hyphens
WORD_RE = re.compile(r"[^\W\d_]+(?:['-][^\W\d_]+)*")


def parse_words(text):
    """Extract words from .txt or .md content.

    Skips HTML comments and lines starting with '#' (Markdown headings or
    plain comments). List markers, numbering and formatting are ignored, and
    words may be separated by newlines, spaces or commas. Apostrophes and
    hyphens are dropped ("don't" -> "dont"). Returns lowercase words with
    duplicates removed, in order of appearance.
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    words = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for match in WORD_RE.findall(line):
            words.append(re.sub(r"['-]", "", match).lower())
    return list(dict.fromkeys(words))


def read_words(path):
    """Read words from a .txt or .md file"""
    with open(path, encoding="utf-8") as f:
        return parse_words(f.read())


def add_words_to_file(path, text):
    """Append the words in text to a words file as "- word" lines.

    Words already in the file are skipped. Returns the words added.
    """
    with open(path, encoding="utf-8") as f:
        content = f.read()
    existing = set(parse_words(content))
    new = [w for w in parse_words(text) if w not in existing]
    if new:
        with open(path, "a", encoding="utf-8") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            f.write("".join(f"- {w}\n" for w in new))
    return new


def remove_word_from_file(path, word):
    """Remove every occurrence of word from a words file.

    Comments and headings are left alone. A line that held only this word
    is dropped; otherwise just the word is cut out of the line.
    """
    def same(match):
        return re.sub(r"['-]", "", match.group()).lower() == word

    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)

    out = []
    in_comment = False
    for line in lines:
        # Track <!-- --> blocks so words inside comments are never touched
        rest = line
        if in_comment:
            if "-->" not in rest:
                out.append(line)
                continue
            in_comment = False
            rest = rest.split("-->", 1)[1]
        if "<!--" in rest and "-->" not in rest.split("<!--", 1)[1]:
            in_comment = True
        if line.lstrip().startswith(("#", "<!--")) or not any(same(m) for m in WORD_RE.finditer(line)):
            out.append(line)
            continue

        kept = WORD_RE.sub(lambda m: "" if same(m) else m.group(), line)
        if not WORD_RE.search(kept):
            continue
        # Tidy separators left behind ("a, , b" -> "a, b")
        kept = re.sub(r"[ \t]*,[ \t]*(?:,[ \t]*)+", ", ", kept)
        kept = re.sub(r"^(\s*(?:[-*+]|\d+\.)?\s*),\s*", r"\1", kept)
        kept = re.sub(r"[ \t]*,?[ \t]*(\r?\n)?$", r"\1", kept)
        out.append(kept)

    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(out))


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
main.wide { max-width: 1200px; }
.with-side { display: flex; flex-wrap: wrap; gap: 32px; align-items: flex-start; }
.with-side > .content { flex: 1 1 480px; min-width: 0; }
.side { flex: 0 0 240px; border-left: 1px solid #ddd; padding-left: 24px; }
.side h2 { font-size: 1rem; margin: 0 0 8px; letter-spacing: 0.05em; }
.side .add { display: flex; gap: 6px; margin: 0 0 12px; }
.side .add input { flex: 1; min-width: 0; padding: 6px 8px; font: inherit;
                   border: 1px solid var(--ink); border-radius: 6px; }
.side .add button { padding: 6px 12px; font: inherit; font-size: 0.9rem; cursor: pointer;
                    border: 1px solid var(--ink); border-radius: 6px;
                    background: var(--ink); color: var(--paper); }
.side ul { list-style: none; margin: 0; padding: 0; }
.side li { display: flex; justify-content: space-between; align-items: center;
           padding: 4px 0; border-bottom: 1px solid #eee;
           font-weight: 600; text-transform: uppercase; }
.side li form { margin: 0; }
.side li button { border: 0; background: none; color: var(--muted); cursor: pointer;
                  font-size: 1.1rem; line-height: 1; padding: 0 4px; }
.side li button:hover { color: #b00020; }
.side .hint { color: var(--muted); font-size: 0.8rem; margin: 8px 0 0; }
.title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px;
             margin: 0 0 16px; }
.title-row h1 { margin: 0; }
.side-toggle { padding: 4px 12px; font: inherit; font-size: 0.85rem; cursor: pointer;
               border: 1px solid var(--ink); border-radius: 6px;
               background: var(--paper); color: var(--ink); }
main.side-hidden { max-width: none; }
main.side-hidden .side { display: none; }
@media (max-width: 760px) { .side { flex-basis: 100%; border-left: 0; padding-left: 0; } }
@media print { body { padding: 0; } .side, .side-toggle { display: none; } }
"""


def page(body, title="Crossword", sidebar=""):
    """Wrap body HTML in the standalone page shell"""
    main_class = ""
    heading = f"<h1>{escape(title)}</h1>"
    toggle_script = ""
    if sidebar:
        main_class = ' class="wide"'
        heading = f"""<div class="title-row">{heading}
<button type="button" class="side-toggle" id="side-toggle" aria-controls="side" aria-expanded="true">Hide words</button>
</div>"""
        body = f"""<div class="with-side">
<div class="content">
{body}</div>
{sidebar}
</div>"""
        toggle_script = SIDE_TOGGLE_SCRIPT
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
{heading}
{body}
</main>
{toggle_script}
</body>
</html>
"""


# Hides the word sidebar so the grid gets the whole page. The choice is
# remembered per browser.
SIDE_TOGGLE_SCRIPT = """<script>
(() => {
  const KEY = "crossword-side-hidden";
  const main = document.querySelector("main"), button = document.getElementById("side-toggle");
  let hidden = false;
  try { hidden = localStorage.getItem(KEY) === "1"; } catch (e) {}
  function show() {
    main.classList.toggle("side-hidden", hidden);
    button.textContent = hidden ? "Show words" : "Hide words";
    button.setAttribute("aria-expanded", !hidden);
  }
  button.addEventListener("click", () => {
    hidden = !hidden;
    try { localStorage.setItem(KEY, hidden ? "1" : "0"); } catch (e) {}
    show();
  });
  show();
})();
</script>"""


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


def render_sidebar(words, editable=False, extra=""):
    """Word list shown beside the sandbox grid.

    The words are buttons, wired up by the sandbox script. When editable, it
    has a form to add words and a remove button per word; both POST to the
    server, which updates the words file. extra is raw HTML shown under the
    list.
    """
    items = []
    for word in sorted(words):
        remove = ""
        if editable:
            remove = f"""<form method="post" action="/remove">
<input type="hidden" name="word" value="{escape(word)}">
<button title="Remove {escape(word)}" aria-label="Remove {escape(word)}">&times;</button></form>"""
        items.append(f'<li data-word="{escape(word)}"><button type="button" class="pick">{escape(word)}</button>{remove}</li>')

    add = ""
    if editable:
        add = """<form class="add" method="post" action="/add">
<input name="word" placeholder="Add words" aria-label="Add words" autocomplete="off" autofocus required>
<button>Add</button></form>"""
    hint = '<p class="hint">Separate several words with spaces or commas. Changes are saved to the words file.</p>' if editable else ""
    return f"""<aside class="side" id="side">
<h2>WORDS ({len(words)})</h2>
{add}
<ul>{''.join(items)}</ul>
{extra}
{hint}
</aside>"""


def serve(get_words, port=8000, title="Crossword", open_browser=True, words_file=None):
    """Serve the sandbox on http://127.0.0.1:port.

    get_words is called on every request, so a words file is re-read each time.
    With words_file, the page can add and remove words, saving them there, and
    its schemas are saved next to it.
    """
    from .sandbox import read_store, render_sandbox_page, store_path_for, write_store

    store_path = store_path_for(words_file) if words_file else None

    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse

    class Handler(BaseHTTPRequestHandler):
        def send_html(self, html):
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def read_words(self):
            try:
                return get_words()
            except OSError as e:
                print(f"Could not read words: {e}")
                return []

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
                store = read_store(store_path) if store_path else None
                self.send_html(render_sandbox_page(self.read_words(), title=title,
                                                   editable=words_file is not None, store=store))
                return
            if url.path == "/sandbox":
                # The sandbox used to live here; keep old bookmarks working
                self.send_response(301)
                self.send_header("Location", "/")
                self.end_headers()
                return
            self.send_error(404)

        def do_POST(self):
            url = urlparse(self.path)
            if url.path == "/store" and store_path:
                self.save_store()
                return
            if url.path not in ("/add", "/remove") or words_file is None:
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", 0))
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            word = form.get("word", [""])[0]
            try:
                if url.path == "/add":
                    added = add_words_to_file(words_file, word)
                    print(f"Added: {', '.join(added) or '(nothing new)'}")
                else:
                    remove_word_from_file(words_file, word)
                    print(f"Removed: {word}")
            except OSError as e:
                print(f"Could not update {words_file}: {e}")
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

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
    parser.add_argument("words", nargs="*", help="words to list in the sandbox")
    parser.add_argument("-f", "--file", help="read words from a .txt or .md file (re-read on every request)")
    parser.add_argument("--title", default="Crossword", help="page title")
    parser.add_argument("--port", type=int, default=8000, help="port to serve on (default: 8000)")
    # Serving is the only mode now; these used to switch it on
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--sandbox", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    def get_words():
        words = list(args.words)
        if args.file:
            words += read_words(args.file)
        # Convert words to lowercase and remove duplicates while preserving order
        return list(dict.fromkeys([word.lower() for word in words]))

    serve(get_words, port=args.port, title=args.title, words_file=args.file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
