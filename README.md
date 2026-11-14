# Crossword Sandbox

A browser page for laying out crosswords by hand. You start from a list of words, drop them into a grid, then drag and turn them, paint black cells, write clues and keep several named layouts. Everything is saved next to your word list.

It is pure Python (3.8 or newer) with no dependencies. A small local server hosts the page and saves your work.

## Quick start

```bash
git clone https://github.com/rusiano/crossword-sandbox.git
cd crossword-sandbox
cp words.example.md words.md    # then put your own words in words.md
./crossword                     # opens the sandbox in your browser
```

`words.md` is git-ignored, so your word list and layouts stay on your machine. If there is no `words.md`, `./crossword` uses `words.example.md`.

You can also install it as a package:

```bash
pip install -e .
python -m crossword.visualize -f words.md
```

The server runs on `127.0.0.1:8000` (change it with `--port`). Press Ctrl+C to stop it. The words file is re-read on every request, so you can edit it while the server is running. Words passed as arguments (`./crossword cross word sword`) are listed in the sandbox but saved nowhere.

## Words file

A words file can be `.txt` or `.md`. Put one word per line, or separate words with spaces or commas. Lines starting with `#`, `<!-- -->` comments and list markers (`-`, `1.`) are ignored. Words are lowercased, and apostrophes and hyphens are dropped.

You can add and remove words from the sidebar, and the changes are written back to the file.

## Using the sandbox

- Click a word in the list to drop it into the grid, then drag it or move it with the arrow keys.
- Press **H** / **V** to turn a word across or down, **Del** to take it out and **Esc** to deselect it.
- Click an empty cell and type a new word that exists only in this layout. **Tab** turns it and **Enter** keeps it.
- Press **B** to paint black cells. The +/− buttons around the grid add or remove rows and columns.
- **L** toggles letters, **N** toggles numbers and clues, and **W** toggles the word list. Click a numbered word to write its clue.
- Keep several named schemas with New, Duplicate, Rename and Delete.

Every word gets a black cell at each end. Black cells that are walled in by letters are drawn black. Empty cells the grid edge can reach without crossing a letter are drawn grey, as outside the puzzle. The status line counts the black cells.

Schemas and clues are saved next to the words file, so `words.md` saves to `words.sandbox.json`. When the words come only from arguments, they are kept in the browser's `localStorage`. The Help popover in the toolbar lists every shortcut.

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/
python -m unittest tests.test_visualize    # without pytest
```

Run the tests from the repository root, because they import `src.crossword`.
