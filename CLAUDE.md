# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Use `python3` (no `python` alias on this machine). Run everything from the repo root: tests import `src.crossword.visualize` and `src.crossword.sandbox`, which only resolve from there.

```bash
pip install -e ".[dev]"                 # install package + pytest
python3 -m pytest tests/                # run all tests
python3 -m pytest tests/test_visualize.py::SandboxPageTests::test_typing_mode_is_wired_up   # single test
python3 -m unittest tests.test_visualize   # works without pytest installed (tests are unittest.TestCase)
./crossword                              # sandbox for words.md (or words.example.md), opened in the browser
PYTHONPATH=src python3 -m crossword.visualize -f words.md   # same, with any words file; re-reads it on every request
PYTHONPATH=src python3 -m crossword.visualize cross word sword   # words as args (schemas go to localStorage)
python3 -m build                         # build wheel/sdist into dist/ (needs `pip install build`)
```

There is no linter or formatter configured.

## Architecture

This branch is the sandbox only. The automatic generator (`crossword.py`, the `/generator` page and static HTML output) is kept on a local `with-generator` branch, which also has the upstream history. It is not published.

`src/crossword/visualize.py` holds the shared page shell (`page`, `STYLE`), the word sidebar (`render_sidebar`), words-file handling (`parse_words`, which skips `#` lines and `<!-- -->` comments, plus `add_words_to_file` / `remove_word_from_file`) and the server. `main` always serves: it runs a stdlib `http.server` on 127.0.0.1 and opens the browser, through `explorer.exe` on WSL and `webbrowser` elsewhere. `--serve` and `--sandbox` are hidden no-op aliases from when there were other modes. `GET /` serves `src/crossword/sandbox.py`'s page, and the old `/sandbox` URL redirects there.

All of the sandbox's controls sit in one sticky toolbar at the top (schema, word, grid and view groups, plus a Help popover). The sandbox page is a client-side-only grid: you click a word to drop it in, drag it, press H/V to turn it, add or remove edge rows/columns, paint black cells (B), and type new sandbox-only words by clicking an empty cell (they get their own list in the sidebar). Each word gets black cells at both ends. On screen, only cells walled in by letters are black. Every non-letter cell that the edge of the grid can reach without crossing a letter (`outsideSet`) is drawn grey, word-end and hand-painted black cells included. In paint mode, grey cells that were painted by hand get an outline. The black cells are numbered in reading order, and the status line shows how many there are. Words may touch the edge of the grid, so their end black cells can fall outside it (`blockSet` keeps only the cells inside the grid). Letters are the only thing that stops an edge row or column from being removed (`canShrink`). The page with a word sidebar also gets a "Hide words" toggle (`SIDE_TOGGLE_SCRIPT` in `visualize.py`, W in the sandbox), which lets the grid use the full page width and is remembered in `localStorage`.

The sandbox keeps several named schemas and clue definitions, saved through `POST /store` into `<words file>.sandbox.json` (e.g. `words.sandbox.json`, see `read_store`/`write_store`), or in `localStorage` when there is no words file. The add and remove forms POST to `/add` and `/remove`, which edit the words file and redirect back to `/`. The package has no runtime dependencies.

Some behaviors to keep in mind:
- The CLI lowercases and dedupes its words.
- `words.md`, `*.sandbox.json` and build artifacts (`dist/`, `*.egg-info/`, `__pycache__/`) are git-ignored, because the words file and schemas are personal. `words.example.md` is the tracked starter list, and `./crossword` falls back to it when `words.md` is missing.
