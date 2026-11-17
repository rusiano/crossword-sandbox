# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Use `python3` (no `python` alias on this machine). Run everything from the repo root: tests import `src.crossword.visualize` and `src.crossword.sandbox`, which only resolve from there.

```bash
pip install -e ".[dev]"                 # install package + pytest
python3 -m pytest tests/                # run all tests
python3 -m pytest tests/test_visualize.py::SandboxPageTests::test_typing_mode_is_wired_up   # single test
python3 -m unittest tests.test_visualize   # works without pytest installed (tests are unittest.TestCase)
./crossword                              # sandbox opened in the browser, schemas saved in schemas.json
PYTHONPATH=src python3 -m crossword.visualize --store other.json   # same, with any schemas file
PYTHONPATH=src python3 -m crossword.visualize   # no store file: schemas go to localStorage
python3 -m build                         # build wheel/sdist into dist/ (needs `pip install build`)
```

There is no linter or formatter configured.

## Architecture

This branch is the sandbox only. The automatic generator (`crossword.py`, the `/generator` page and static HTML output) is kept on a local `with-generator` branch, which also has the upstream history. It is not published.

`src/crossword/visualize.py` holds the shared page shell (`page`, `STYLE`) and the server. `main` always serves: it runs a stdlib `http.server` on 127.0.0.1 and opens the browser, through `explorer.exe` on WSL and `webbrowser` elsewhere. `--serve` and `--sandbox` are hidden no-op aliases from when there were other modes. `GET /` serves `src/crossword/sandbox.py`'s page, and the old `/sandbox` URL redirects there. Each `GET /` reloads `visualize` and `sandbox` (`render_page` in `serve`), so edits to the page's HTML/CSS/JS show on a browser refresh; if the reload fails (say, a half-saved file) the last version that loaded is served. Changes to the server code itself (`serve`, `Handler`, `main`) still need a restart.

All of the sandbox's controls sit in one sticky toolbar at the top (schema, word, grid and view groups, plus a Help popover). The sandbox page is a client-side-only grid: you drag a word, press H/V to turn it, add or remove edge rows/columns, paint black cells (B), and type new words by clicking an empty cell. There is no separate word pool: a schema's words are the ones in its grid, and the sidebar lists them (filled in by the script from `order`), so taking a word out of the grid also drops it from the list. The sidebar sits in a `.board-row` beside the board: its content is absolutely positioned (`.side-inner`), so the row's height comes from the board alone and the list scrolls within it. Each word gets black cells at both ends. On screen, the cells walled in by letters and the cells painted by hand are black. Every other non-letter cell that the edge of the grid can reach without crossing a letter or a hand-painted cell (`outsideSet`, where painted cells act as walls) is drawn grey, word-end black cells included; word-end cells there get a darker grey (`.end`) so the gaps between words stay visible. In paint mode, hand-painted cells get a light ring. The Grid group's All black toggle (A, the schema's `allBlack`, saved with it) is for full rectangular schemas: there is no outside, so every non-letter cell is black and counted. The black cells are numbered in reading order, and the status line shows how many there are, followed by their share of the schema's cells (black / (black + letter cells)), green up to 15%, orange up to 22%, red above. Words may touch the edge of the grid, so their end black cells can fall outside it (`blockSet` keeps only the cells inside the grid). Letters are the only thing that stops an edge row or column from being removed (`canShrink`). The toolbar's View group has four toggles, each with a key: Letters (L), Numbers (N, the numbers in the grid), Words (W, the word list) and Definitions (D, the clues panel). They live in the script's `view` and are remembered in `localStorage`, not in the schemas. The page always spans the full width (`page(..., wide=True)`); the grid and the word list beside it (or the grid alone) are centred together in `.board-row`.

The sandbox keeps several named schemas and clue definitions, saved through `POST /store` into the `--store` file (`schemas.json` for `./crossword`, see `read_store`/`write_store`), or in `localStorage` when there is none. Schemas saved by older versions may carry a `typed` list; the page drops it on the next save. The package has no runtime dependencies.

`schemas.json` and build artifacts (`dist/`, `*.egg-info/`, `__pycache__/`) are git-ignored, because the schemas are personal. `words.md` and `*.sandbox.json` stay ignored for checkouts from before the words file was dropped.
