import json
import os

from .visualize import page


def empty_store():
    return {"current": None, "schemas": []}


def read_store(path):
    """Read saved sandbox schemas, or an empty store if the file is missing or unreadable"""
    try:
        with open(path, encoding="utf-8") as f:
            store = json.load(f)
    except (OSError, ValueError):
        return empty_store()
    if not isinstance(store, dict) or not isinstance(store.get("schemas"), list):
        return empty_store()
    return store


def write_store(path, store):
    """Save sandbox schemas, replacing the file in one step so a crash can't leave half of it"""
    if not isinstance(store, dict) or not isinstance(store.get("schemas"), list):
        raise ValueError("expected {'current': ..., 'schemas': [...]}")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


SANDBOX_STYLE = r"""
<style>
.toolbar { position: sticky; top: 0; z-index: 5; display: flex; flex-wrap: wrap; gap: 6px 0;
           align-items: center; margin: 0 0 12px; padding: 6px 0; background: var(--paper);
           border-bottom: 1px solid #ddd; }
.toolbar .group { display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
                  padding: 0 12px; border-left: 1px solid #ddd; }
.toolbar .group:first-child { padding-left: 0; border-left: 0; }
.toolbar .group.end { margin-left: auto; border-left: 0; padding-right: 0; position: relative; }
.toolbar .label { color: var(--muted); font-size: 0.7rem; letter-spacing: 0.05em; text-transform: uppercase; }
.toolbar button, .toolbar select, .toolbar a, .toolbar summary { font: inherit; font-size: 0.85rem; }
.toolbar button, .toolbar a, .toolbar summary { padding: 4px 10px; border: 1px solid var(--ink);
                  border-radius: 6px; background: var(--paper); color: var(--ink); cursor: pointer;
                  text-decoration: none; }
.toolbar button:disabled { opacity: 0.35; cursor: default; }
.toolbar button[aria-pressed="true"] { background: var(--ink); color: var(--paper); }
.toolbar button.danger:hover:not(:disabled) { border-color: #b00020; color: #b00020; }
.toolbar select { padding: 3px 6px; border: 1px solid var(--ink); border-radius: 6px;
                  background: var(--paper); color: var(--ink); max-width: 14em; }
.toolbar .saved { color: var(--muted); font-size: 0.75rem; }
.toolbar kbd { font: inherit; font-size: 0.7rem; padding: 0 4px; border: 1px solid currentColor;
               border-radius: 3px; opacity: 0.6; }
.toolbar .help summary { list-style: none; }
.toolbar .help summary::-webkit-details-marker { display: none; }
.toolbar .help[open] summary { background: var(--ink); color: var(--paper); }
.toolbar .help p { position: absolute; right: 0; top: calc(100% + 6px); width: min(28rem, 85vw);
                   margin: 0; padding: 10px 12px; font-size: 0.85rem; line-height: 1.5;
                   background: var(--paper); border: 1px solid var(--ink); border-radius: 6px;
                   box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12); }
.toolbar .help kbd { font-size: 0.75rem; }
.sandbox-status { color: var(--muted); font-size: 0.85rem; margin: 0 0 12px; }
.sandbox-status .ratio { font-weight: 600; }
.sandbox-status .ratio.good { color: #2e7d32; }
.sandbox-status .ratio.fair { color: #c46a00; }
.sandbox-status .ratio.poor { color: #b00020; }
/* The grid and the word list beside it (or the grid alone) sit in the middle of the page */
.board-row { display: flex; gap: 24px; justify-content: center; }
.board-row .board-wrap { flex: 0 1 auto; min-width: 0; overflow: auto; }
.board-frame { display: grid; gap: 6px; width: max-content;
               grid-template-areas: ". top ." "left board right" ". bottom ."; }
.board-frame .board { grid-area: board; }
.edge { display: flex; gap: 4px; justify-content: center; align-items: center; }
.edge.top { grid-area: top; } .edge.bottom { grid-area: bottom; }
.edge.left, .edge.right { flex-direction: column; }
.edge.left { grid-area: left; } .edge.right { grid-area: right; }
.edge button { width: 1.8rem; height: 1.8rem; padding: 0; font: inherit; font-size: 1rem; line-height: 1;
               border: 1px solid #bbb; border-radius: 6px; background: var(--paper);
               color: var(--ink); cursor: pointer; }
.edge button:hover:not(:disabled) { border-color: var(--ink); }
.edge button:disabled { opacity: 0.3; cursor: default; }
.board { display: grid; gap: 1px; padding: 1px; background: #b8b8b8; width: max-content;
         touch-action: none; user-select: none; -webkit-user-select: none; }
.board div { position: relative; width: 2.2rem; height: 2.2rem; background: #dcdcdc; display: flex;
             align-items: center; justify-content: center; font-size: 1.15rem;
             font-weight: 600; text-transform: uppercase; }
.board div.filled { background: var(--paper); cursor: grab; box-shadow: inset 0 0 0 1px var(--ink); }
.board div.cross { background: #e6f0ff; }
.board div.sel { background: #ffe9a8; }
.board div.sel.cross { background: #ffd966; }
.board div.block { background: var(--block); }
/* Outside cells sharing a side with a letter: they delimit a word */
.board div.end { background: #b0b0b0; }
.board div .count { color: var(--paper); font-size: 0.7rem; font-weight: 400; }
/* While painting, the black cells added by hand get a light ring, to tell them from the others */
.board.painting div.painted { box-shadow: inset 0 0 0 3px #bdbdbd; }
.board div.clash { background: #ffd6dc; color: #b00020; }
.board div.typing { background: #d8f5d0; box-shadow: inset 0 0 0 2px #2e7d32; }
.board div.cursor { box-shadow: inset 0 0 0 2px #2e7d32; animation: blink 1s steps(1) infinite; }
@keyframes blink { 50% { box-shadow: none; } }
.board div .num { position: absolute; top: 1px; left: 2px; font-size: 0.6rem;
                  font-weight: 400; line-height: 1; }
.board.dragging div.filled { cursor: grabbing; }
#clues { margin-top: 20px; }
#clues[hidden] { display: none; }
#clues section { flex: 1 1 260px; min-width: 0; }
#clues li { display: flex; gap: 6px; align-items: baseline; padding: 2px 4px; margin: 0 -4px;
            border-radius: 4px; cursor: pointer; }
#clues li:hover, #clues li:focus-visible { background: #f2f2f2; outline: none; }
#clues li.selected { background: #ffe9a8; }
#clues li .n { flex: none; }
#clues .word { font-weight: 400; }
#clues li.has-def .word { font-weight: 700; }
#clues .def { color: var(--ink); }
#clues .add-def { color: var(--muted); font-size: 0.8rem; }
#clues input { flex: 1; min-width: 0; padding: 3px 6px; font: inherit;
               border: 1px solid var(--ink); border-radius: 4px; }
#clues h2 button { margin-left: 8px; padding: 1px 8px; font: inherit; font-size: 0.75rem;
                   font-weight: 400; letter-spacing: 0; border: 1px solid #ccc; border-radius: 4px;
                   background: var(--paper); color: var(--ink); cursor: pointer; }
#clues h2 button:hover { border-color: var(--ink); }
.board.painting div, .board.painting div.filled { cursor: crosshair; }
.side button.pick { border: 0; background: none; padding: 0; font: inherit; color: inherit;
                    text-transform: inherit; cursor: pointer; text-align: left; }
.side button.pick:hover { text-decoration: underline; }
.side li.selected button.pick { background: #ffe9a8; }
.side .hint[hidden] { display: none; }
</style>
"""

# Each schema holds rows, cols, placed (word -> {x, y, dir}), order (stacking
# order, last on top), blocks (black cells added by hand, as "row,col") and
# allBlack (every empty cell is black, as in a full rectangular schema).
# Its words are the ones typed into its grid, and the sidebar lists them.
# Definitions (word -> text) sit beside the schemas, shared by all of them.
# The schemas are saved on the server when it has a store file (STORE is the
# saved data), otherwise in localStorage (STORE is null). While a word is
# being typed, typing is {r, c, dir, text}.
SANDBOX_SCRIPT = r"""
<script>
// Wait for the whole page, so every element the script looks up exists
document.addEventListener("DOMContentLoaded", () => {
const DEFAULT_SIZE = 15;
const KEY = "crossword-sandbox-schemas";
const SERVER = __STORE__ !== null;
const board = document.getElementById("board");
const status = document.getElementById("status");
const schemaSelect = document.getElementById("schema");
const savedNote = document.getElementById("saved");
const wordList = document.getElementById("word-list");
const MIN_LINES = 2, MAX_LINES = 60;
let rows, cols, placed, order, manual, allBlack, current;
let selected = null, drag = null, typing = null, lastDir = "across", painting = false, paint = null;
// What is shown is a per-browser preference, not part of a schema
const VIEW_KEY = "crossword-sandbox-view";
let view = {letters: true, numbers: false, words: true, definitions: false};
try {
  const saved = JSON.parse(localStorage.getItem(VIEW_KEY) || "{}");
  // Earlier versions kept the word list's state under its own key, and showed
  // the definitions together with the numbers
  if (!("words" in saved)) saved.words = localStorage.getItem("crossword-side-hidden") !== "1";
  if (!("definitions" in saved)) saved.definitions = Boolean(saved.numbers);
  Object.assign(view, saved);
} catch (e) {}
const VIEWS = ["letters", "numbers", "words", "definitions"];

function toggleView(name) {
  view[name] = !view[name];
  try { localStorage.setItem(VIEW_KEY, JSON.stringify(view)); } catch (e) {}
  render();
}

// --- Schemas and saving ---

function newSchema(name, from) {
  from = from || {};
  return {
    id: "s" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
    name,
    rows: from.rows || from.size || DEFAULT_SIZE, cols: from.cols || from.size || DEFAULT_SIZE,
    placed: from.placed || {}, order: from.order || [], blocks: from.blocks || [],
    allBlack: Boolean(from.allBlack),
  };
}

let store = __STORE__;
if (!SERVER) {
  try { store = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) {}
}
if (!store || !Array.isArray(store.schemas)) store = {current: null, schemas: []};
if (!store.definitions || typeof store.definitions !== "object") store.definitions = {};
const firstVisit = !store.schemas.length;
if (firstVisit) {
  // Bring over the single layout earlier versions kept in this browser
  let old = null;
  try { old = JSON.parse(localStorage.getItem("crossword-sandbox") || "null"); } catch (e) {}
  store.schemas.push(newSchema("Schema 1", old));
}

// A schema made just now (or brought over) is saved straight away
let lastSaved = firstVisit ? null : JSON.stringify(store), timer = null;

function setSaved(text) { savedNote.textContent = text; }

function persist() {
  timer = null;
  const body = JSON.stringify(store);
  if (!SERVER) {
    try { localStorage.setItem(KEY, body); lastSaved = body; setSaved("Saved in this browser"); }
    catch (e) { setSaved("Could not save"); }
    return;
  }
  fetch("/store", {method: "POST", headers: {"Content-Type": "application/json"}, body})
    .then(r => {
      if (!r.ok) throw new Error(r.status);
      lastSaved = body;
      setSaved("Saved");
    })
    .catch(() => { setSaved("Not saved, retrying…"); timer = setTimeout(persist, 3000); });
}

// Write the current schema back into the store and save it shortly after
function save() {
  Object.assign(current, {rows, cols, placed, order, blocks: [...manual], allBlack});
  // Earlier versions also kept a list of typed words, now just the words in the grid
  delete current.typed;
  store.current = current.id;
  if (JSON.stringify(store) === lastSaved) return;
  setSaved("Saving…");
  clearTimeout(timer);
  timer = setTimeout(persist, 400);
}

// Leaving the page must not lose the last change
window.addEventListener("pagehide", () => {
  if (!timer) return;
  clearTimeout(timer);
  timer = null;
  if (SERVER) navigator.sendBeacon("/store", new Blob([JSON.stringify(store)], {type: "application/json"}));
  else persist();
});

function loadSchema(schema) {
  current = schema;
  rows = schema.rows || DEFAULT_SIZE;
  cols = schema.cols || DEFAULT_SIZE;
  placed = {};
  order = [];
  for (const w of schema.order || []) {
    if (schema.placed && schema.placed[w]) {
      placed[w] = {...schema.placed[w]};
      order.push(w);
    }
  }
  manual = new Set((schema.blocks || []).filter(k => {
    const [r, c] = k.split(",").map(Number);
    return r >= 0 && r < rows && c >= 0 && c < cols;
  }));
  allBlack = Boolean(schema.allBlack);
  selected = null;
  typing = null;
  buildBoard();
  // Pull back inside any word that sticks out of the grid
  order.forEach(makeRoom);
  renderSchemas();
  render();
}

function renderSchemas() {
  schemaSelect.replaceChildren(...store.schemas.map(s => {
    const option = document.createElement("option");
    option.value = s.id;
    option.textContent = s.name;
    option.selected = s === current;
    return option;
  }));
  document.getElementById("schema-delete").disabled = store.schemas.length < 2;
}

function askName(message, name) {
  const answer = prompt(message, name);
  return answer && answer.trim() ? answer.trim() : null;
}

function nextName() {
  for (let n = store.schemas.length + 1; ; n++) {
    if (!store.schemas.some(s => s.name === `Schema ${n}`)) return `Schema ${n}`;
  }
}

// --- Grid geometry ---

function cellsOf(w) {
  const p = placed[w], out = [];
  for (let i = 0; i < w.length; i++) {
    out.push(p.dir === "across" ? [p.y, p.x + i] : [p.y + i, p.x]);
  }
  return out;
}

// The black cells just before and after a word. A word may touch the edge of
// the grid, and then its black cell there falls outside the grid.
function blocksOf(w) {
  const p = placed[w];
  return p.dir === "across"
    ? [[p.y, p.x - 1], [p.y, p.x + w.length]]
    : [[p.y - 1, p.x], [p.y + w.length, p.x]];
}

const manualCells = () => [...manual].map(k => k.split(",").map(Number));
const inGrid = ([r, c]) => r >= 0 && r < rows && c >= 0 && c < cols;

// Every black cell inside the grid: the ones at word ends and the ones added by hand
function blockSet() {
  const cells = [...order.flatMap(blocksOf), ...manualCells()].filter(inGrid);
  return new Set(cells.map(([r, c]) => r * cols + c));
}

// Keep a word inside the grid. The grid must already be long enough (see makeRoom).
function clamp(w) {
  const p = placed[w], across = p.dir === "across";
  p.x = Math.max(0, Math.min(p.x, across ? cols - w.length : cols - 1));
  p.y = Math.max(0, Math.min(p.y, across ? rows - 1 : rows - w.length));
}

// Grow the grid where a word would stick out of it. Growing at the top or
// left shifts every word, so the word itself stays put on screen.
function makeRoom(w) {
  const p = placed[w];
  if (p.x < 0 || p.y < 0) grow(p.dir === "across" ? "left" : "top");
  // Measure the far end only now, as growing at the top or left moved the word
  while (cellsOf(w).some(([r]) => r >= rows)) grow("bottom");
  while (cellsOf(w).some(([, c]) => c >= cols)) grow("right");
  clamp(w);
}

// Cells outside the schema: an empty cell (no letter) on the edge of the grid
// is outside, and so is any empty cell sharing a full side (not just a corner)
// with an outside cell. Only letters stop it; black cells, word-end and
// hand-painted alike, are empty cells here.
function outsideSet(map) {
  const seen = new Set(), stack = [];
  const visit = (r, c) => {
    const k = r * cols + c;
    if (r < 0 || r >= rows || c < 0 || c >= cols || seen.has(k) || map.has(k)) return;
    seen.add(k);
    stack.push([r, c]);
  };
  for (let r = 0; r < rows; r++) { visit(r, 0); visit(r, cols - 1); }
  for (let c = 0; c < cols; c++) { visit(0, c); visit(rows - 1, c); }
  while (stack.length) {
    const [r, c] = stack.pop();
    visit(r - 1, c); visit(r + 1, c); visit(r, c - 1); visit(r, c + 1);
  }
  return seen;
}

// Words covering each cell, bottom to top
function coverage() {
  const map = new Map();
  for (const w of order) {
    cellsOf(w).forEach(([r, c], i) => {
      const k = r * cols + c;
      if (!map.has(k)) map.set(k, []);
      map.get(k).push({word: w, letter: w[i]});
    });
  }
  return map;
}

function buildBoard() {
  board.style.gridTemplateColumns = `repeat(${cols}, auto)`;
  board.replaceChildren(...Array.from({length: rows * cols}, () => document.createElement("div")));
}

// Move everything on the board, used when a row or column comes or goes on the top or left
function shift(dx, dy) {
  for (const w of order) { placed[w].x += dx; placed[w].y += dy; }
  manual = new Set(manualCells().map(([r, c]) => `${r + dy},${c + dx}`));
}

// An edge row or column can go when no letter is on it (it is all grey). Black
// cells on it go with it.
function canShrink(edge) {
  const horizontal = edge === "top" || edge === "bottom";
  if ((horizontal ? rows : cols) <= MIN_LINES) return false;
  const line = {top: 0, bottom: rows - 1, left: 0, right: cols - 1}[edge];
  return order.flatMap(cellsOf).every(([r, c]) => (horizontal ? r : c) !== line);
}

function grow(edge) {
  if (edge === "top" || edge === "bottom") rows++; else cols++;
  if (edge === "top") shift(0, 1);
  if (edge === "left") shift(1, 0);
  buildBoard();
}

// Add (delta 1) or remove (delta -1) a row or column on one side
function resize(edge, delta) {
  const horizontal = edge === "top" || edge === "bottom";
  if (delta > 0) {
    if ((horizontal ? rows : cols) < MAX_LINES) grow(edge);
  } else if (canShrink(edge)) {
    if (horizontal) rows--; else cols--;
    if (edge === "top") shift(0, -1);
    if (edge === "left") shift(-1, 0);
    manual = new Set([...manual].filter(k => inGrid(k.split(",").map(Number))));
    buildBoard();
  }
  render();
}

// --- Drawing ---

// Crossword numbers for word start cells in reading order (words starting on
// the same cell share one)
function numbering() {
  const starts = [...new Set(order.map(w => placed[w].y * cols + placed[w].x))].sort((a, b) => a - b);
  const numbers = new Map(starts.map((k, i) => [k, i + 1]));
  const clues = {across: [], down: []};
  for (const w of order) clues[placed[w].dir].push([numbers.get(placed[w].y * cols + placed[w].x), w]);
  for (const list of Object.values(clues)) list.sort((a, b) => a[0] - b[0] || a[1].localeCompare(b[1]));
  return {numbers, clues};
}

// The definition being edited: {word, draft, focus}
let editing = null, cluesShown = "", rebuilding = false;

function setDefinition(w, text) {
  text = text.trim();
  if (text) store.definitions[w] = text; else delete store.definitions[w];
  editing = null;
  render();
}

function startEditing(w) {
  editing = {word: w, draft: store.definitions[w] || "", focus: true};
  render();
}

function renderClues(clues) {
  const box = document.getElementById("clues");
  const input = box.querySelector("input");
  if (editing && input) editing.draft = input.value;
  // Only rebuild when something shown changed, so an open definition box survives other redraws
  const shown = JSON.stringify([view, clues, store.definitions, editing && editing.word, selected]);
  if (shown === cluesShown) return;
  cluesShown = shown;
  box.hidden = !view.definitions || !order.length;
  if (box.hidden) return;
  const hadFocus = input && document.activeElement === input;
  let newInput = null;
  rebuilding = true;
  box.replaceChildren(...["across", "down"].map(dir => {
    const section = document.createElement("section");
    const heading = document.createElement("h2");
    heading.textContent = dir.toUpperCase();
    // Copies this direction's definitions as one line: "1. def - 3. def"
    const copy = document.createElement("button");
    copy.type = "button";
    copy.textContent = "Copy";
    copy.title = `Copy the ${dir} definitions as one line`;
    copy.addEventListener("click", () => {
      const text = clues[dir].filter(([, w]) => store.definitions[w])
        .map(([n, w]) => `${n}. ${store.definitions[w]}`).join(" - ");
      navigator.clipboard.writeText(text).then(
        () => { copy.textContent = "Copied"; },
        () => { copy.textContent = "Copy failed"; });
      setTimeout(() => { copy.textContent = "Copy"; }, 1500);
    });
    heading.append(copy);
    const list = document.createElement("ol");
    for (const [n, w] of clues[dir]) {
      const def = store.definitions[w];
      const li = document.createElement("li");
      li.dataset.word = w;
      li.tabIndex = 0;
      li.title = def ? "Edit the definition" : "Add a definition";
      li.classList.toggle("has-def", Boolean(def));
      li.classList.toggle("selected", w === selected);
      const num = document.createElement("span");
      num.className = "n";
      num.textContent = `${n}.`;
      const word = document.createElement("span");
      word.className = "word";
      word.textContent = view.letters ? w.toUpperCase() : `(${w.length})`;
      li.append(num, word);
      if (editing && editing.word === w) {
        newInput = document.createElement("input");
        newInput.value = editing.draft;
        newInput.placeholder = `Definition of ${w.toUpperCase()}`;
        newInput.setAttribute("aria-label", newInput.placeholder);
        newInput.addEventListener("keydown", e => {
          if (e.key === "Enter") { e.preventDefault(); setDefinition(w, newInput.value); }
          if (e.key === "Escape") { e.preventDefault(); editing = null; render(); }
        });
        newInput.addEventListener("blur", () => { if (!rebuilding && editing) setDefinition(w, newInput.value); });
        li.append(newInput);
      } else if (def) {
        const text = document.createElement("span");
        text.className = "def";
        text.textContent = def;
        li.append(text);
      } else {
        const hint = document.createElement("span");
        hint.className = "add-def";
        hint.textContent = "add definition";
        li.append(hint);
      }
      list.append(li);
    }
    section.append(heading, list);
    return section;
  }));
  rebuilding = false;
  if (newInput && (hadFocus || editing.focus)) {
    editing.focus = false;
    newInput.focus();
    newInput.setSelectionRange(newInput.value.length, newInput.value.length);
  }
}

// The sidebar lists the words in this schema's grid
function renderWordList() {
  const words = [...order].sort();
  document.getElementById("word-count").textContent = words.length;
  document.getElementById("words-empty").hidden = words.length > 0;
  wordList.replaceChildren(...words.map(w => {
    const li = document.createElement("li");
    li.dataset.word = w;
    const pick = document.createElement("button");
    pick.type = "button";
    pick.className = "pick";
    pick.textContent = w;
    const forget = document.createElement("button");
    forget.type = "button";
    forget.className = "forget";
    forget.title = `Take ${w} out of the schema`;
    forget.setAttribute("aria-label", forget.title);
    forget.textContent = "×";
    li.append(pick, forget);
    return li;
  }));
}

function render() {
  const map = coverage(), blocks = blockSet(), {numbers, clues} = numbering();
  const hand = new Set(manualCells().filter(inGrid).map(([r, c]) => r * cols + c));
  // A full schema has no outside: every empty cell is black and counted
  const outside = allBlack ? new Set() : outsideSet(map);
  // Cells painted by hand are always black, even outside
  for (const k of hand) outside.delete(k);
  // Outside cells sharing a full side with a letter delimit a word, so they get a darker grey
  const touchesLetter = k => {
    const r = Math.floor(k / cols), c = k % cols;
    return [[r - 1, c], [r + 1, c], [r, c - 1], [r, c + 1]]
      .some(([nr, nc]) => inGrid([nr, nc]) && map.has(nr * cols + nc));
  };
  const ends = new Set([...outside].filter(touchesLetter));
  const selCells = new Set(selected ? cellsOf(selected).map(([r, c]) => r * cols + c) : []);
  // Letters being typed, drawn over whatever is underneath
  const typingCells = new Map();
  let cursor = -1;
  if (typing) {
    const at = i => typing.dir === "across" ? [typing.r, typing.c + i] : [typing.r + i, typing.c];
    [...typing.text].forEach((ch, i) => { const [r, c] = at(i); typingCells.set(r * cols + c, ch); });
    const [r, c] = at(typing.text.length);
    if (r < rows && c < cols) cursor = r * cols + c;
  }
  let clashes = 0, black = 0;
  board.childNodes.forEach((cell, k) => {
    if (typingCells.has(k) || k === cursor) {
      cell.textContent = typingCells.get(k) || "";
      cell.className = typingCells.has(k) ? "typing" : "cursor";
      return;
    }
    const here = map.get(k) || [];
    const letters = new Set(here.map(h => h.letter));
    // A letter on a black cell breaks the word, so it clashes too
    const clash = letters.size > 1 || (here.length > 0 && blocks.has(k));
    if (clash) clashes++;
    const mine = here.find(h => h.word === selected);
    cell.textContent = here.length && view.letters ? (mine || here[here.length - 1]).letter : "";
    if (view.numbers && numbers.has(k)) {
      const num = document.createElement("span");
      num.className = "num";
      num.textContent = numbers.get(k);
      cell.prepend(num);
    }
    // Black cells are numbered in reading order, so they can be counted
    if (!here.length && !outside.has(k)) {
      const count = document.createElement("span");
      count.className = "count";
      count.textContent = ++black;
      cell.append(count);
    }
    cell.className = [
      here.length ? "filled" : outside.has(k) ? "" : "block",
      !here.length && outside.has(k) && ends.has(k) ? "end" : "",
      painting && !here.length && hand.has(k) ? "painted" : "",
      here.length > 1 && !clash ? "cross" : "",
      clash ? "clash" : "",
      selCells.has(k) ? "sel" : "",
    ].join(" ").trim();
  });
  renderWordList();
  renderClues(clues);
  for (const name of VIEWS) document.getElementById(name).setAttribute("aria-pressed", view[name]);
  document.querySelector("main").classList.toggle("side-hidden", !view.words);
  wordList.querySelectorAll("li[data-word]").forEach(li => {
    li.classList.toggle("selected", li.dataset.word === selected);
  });
  for (const id of ["across", "down", "remove"]) document.getElementById(id).disabled = !selected;
  const paintButton = document.getElementById("paint");
  paintButton.setAttribute("aria-pressed", painting);
  document.getElementById("all-black").setAttribute("aria-pressed", allBlack);
  board.classList.toggle("painting", painting);
  document.querySelectorAll(".edge button").forEach(btn => {
    const lines = btn.dataset.edge === "top" || btn.dataset.edge === "bottom" ? rows : cols;
    btn.disabled = btn.dataset.delta === "1" ? lines >= MAX_LINES : !canShrink(btn.dataset.edge);
  });
  save();
  if (painting) {
    status.textContent = "Black cells: click or drag over empty cells to add or remove them · B or Esc to stop";
  } else if (typing) {
    status.textContent = typing.text
      ? `Typing ${typing.dir}: ${typing.text.toUpperCase()} · ` +
        "Enter keeps it, Tab turns it, Backspace deletes a letter, Esc cancels"
      : `Cell picked (${typing.dir}) · type a word, or click one in the list to put it here. ` +
        "Tab turns, Esc cancels";
  } else {
    // Share of black cells among the schema's cells (letters and black cells):
    // up to 15% is good, up to 22% is acceptable, more is too many
    const share = black + map.size ? black / (black + map.size) * 100 : 0;
    const ratio = document.createElement("span");
    ratio.className = "ratio " + (share <= 15 ? "good" : share <= 22 ? "fair" : "poor");
    ratio.title = "Black cells out of all the cells of the schema (letters and black cells)";
    ratio.textContent = `${share.toFixed(1)}% black`;
    status.replaceChildren(
      `${rows} × ${cols} grid · ${order.length} word${order.length === 1 ? "" : "s"}` +
      ` · ${black} black cell${black === 1 ? "" : "s"} · `,
      ratio,
      (clashes ? ` · ${clashes} clashing cell${clashes > 1 ? "s" : ""}` : "") +
      (selected ? ` · selected: ${selected.toUpperCase()} (${placed[selected].dir})` : ""));
  }
}

// --- Editing ---

function select(w) {
  selected = w;
  if (w) { order = order.filter(o => o !== w); order.push(w); }
  render();
}

// Put a word at a given cell (a word already on the board moves there)
function placeAt(w, r, c, dir) {
  if (!(w in placed)) order.push(w);
  placed[w] = {x: c, y: r, dir};
  makeRoom(w);
  select(w);
}

// Take a word out of the schema, and so out of the word list
function removeFromBoard(w) {
  delete placed[w];
  order = order.filter(o => o !== w);
  if (selected === w) selected = null;
  render();
}

function turn(dir) {
  if (!selected) return;
  placed[selected].dir = dir;
  makeRoom(selected);
  render();
}

function move(dx, dy) {
  if (!selected) return;
  placed[selected].x += dx;
  placed[selected].y += dy;
  clamp(selected);
  render();
}

function setPainting(on) {
  finishTyping();
  painting = on;
  if (on) selected = null;
  render();
}

function toggleAllBlack() {
  allBlack = !allBlack;
  render();
}

function paintCell(r, c) {
  // Black cells only go on empty cells
  if (coverage().has(r * cols + c)) return;
  const k = `${r},${c}`;
  if (paint) manual.add(k); else manual.delete(k);
  render();
}

function startTyping(r, c) {
  typing = {r, c, dir: lastDir, text: ""};
  selected = null;
  render();
}

// Turn the typed letters into a word on the board. A word that is already
// on the board moves here instead of appearing twice.
function finishTyping() {
  if (!typing) return;
  const {r, c, dir, text} = typing;
  typing = null;
  if (!text) { render(); return; }
  placeAt(text, r, c, dir);
}

function typeKey(e) {
  const fits = (dir, len) => dir === "across" ? typing.c + len <= cols : typing.r + len <= rows;
  if (e.key === "Enter") finishTyping();
  else if (e.key === "Escape") { typing = null; render(); }
  else if (e.key === "Backspace") { typing.text = typing.text.slice(0, -1); render(); }
  else if (e.key === "Tab") {
    const dir = typing.dir === "across" ? "down" : "across";
    if (fits(dir, typing.text.length)) { typing.dir = lastDir = dir; render(); }
  } else if (/^\p{L}$/u.test(e.key)) {
    if (fits(typing.dir, typing.text.length + 1)) { typing.text += e.key.toLowerCase(); render(); }
  } else return;
  e.preventDefault();
}

// --- Events ---

function cellAt(e) {
  const rect = board.getBoundingClientRect();
  const c = Math.floor((e.clientX - rect.left) / rect.width * cols);
  const r = Math.floor((e.clientY - rect.top) / rect.height * rows);
  return [Math.max(0, Math.min(r, rows - 1)), Math.max(0, Math.min(c, cols - 1))];
}

board.addEventListener("pointerdown", e => {
  const [r, c] = cellAt(e);
  if (painting) {
    // The first cell decides whether this stroke adds or removes black cells
    if (coverage().has(r * cols + c)) return;
    paint = !manual.has(`${r},${c}`);
    board.setPointerCapture(e.pointerId);
    paintCell(r, c);
    return;
  }
  finishTyping();
  const here = (coverage().get(r * cols + c) || []).map(h => h.word);
  // An empty cell starts a new word typed from there
  if (!here.length) { startTyping(r, c); return; }
  // Keep the selected word if it is under the pointer, else take the top one
  const w = here.includes(selected) ? selected : here[here.length - 1];
  const p = placed[w];
  drag = {word: w, dr: r - p.y, dc: c - p.x, moved: false, wasSelected: w === selected, here};
  board.setPointerCapture(e.pointerId);
  board.classList.add("dragging");
  select(w);
});

board.addEventListener("pointermove", e => {
  if (paint !== null) { paintCell(...cellAt(e)); return; }
  if (!drag) return;
  const [r, c] = cellAt(e);
  const p = placed[drag.word];
  const x = c - drag.dc, y = r - drag.dr;
  if (x === p.x && y === p.y) return;
  p.x = x; p.y = y;
  clamp(drag.word);
  drag.moved = true;
  render();
});

function endDrag() {
  paint = null;
  if (!drag) return;
  // Clicking an intersection again without dragging switches to the other word
  if (!drag.moved && drag.wasSelected && drag.here.length > 1) {
    const i = drag.here.indexOf(drag.word);
    select(drag.here[(i + 1) % drag.here.length]);
  }
  drag = null;
  board.classList.remove("dragging");
}
board.addEventListener("pointerup", endDrag);
board.addEventListener("pointercancel", endDrag);

document.addEventListener("keydown", e => {
  if (e.target.closest("input, textarea, select") || e.ctrlKey || e.metaKey || e.altKey) return;
  if (typing) { typeKey(e); return; }
  const name = VIEWS.find(n => n[0] === e.key.toLowerCase());
  if (name) { e.preventDefault(); toggleView(name); return; }
  if (e.key.toLowerCase() === "b" || (painting && e.key === "Escape")) {
    e.preventDefault();
    setPainting(!painting);
    return;
  }
  if (e.key.toLowerCase() === "a") { e.preventDefault(); toggleAllBlack(); return; }
  const keys = {
    h: () => turn("across"), v: () => turn("down"),
    ArrowLeft: () => move(-1, 0), ArrowRight: () => move(1, 0),
    ArrowUp: () => move(0, -1), ArrowDown: () => move(0, 1),
    Delete: () => removeFromBoard(selected),
    Backspace: () => removeFromBoard(selected),
    Escape: () => select(null),
  };
  const action = keys[e.key.length === 1 ? e.key.toLowerCase() : e.key];
  if (!action || (!selected && e.key !== "Escape")) return;
  e.preventDefault();
  action();
});

// Word list clicks: select a word, move it to a picked cell, or take it out
wordList.addEventListener("click", e => {
  const li = e.target.closest("li[data-word]");
  if (!li) return;
  const w = li.dataset.word;
  if (e.target.closest("button.forget")) { removeFromBoard(w); return; }
  if (!e.target.closest("button.pick")) return;
  if (painting) setPainting(false);
  // A cell picked on the board with nothing typed yet is where the word goes
  if (typing && !typing.text) {
    const {r, c, dir} = typing;
    typing = null;
    placeAt(w, r, c, dir);
    return;
  }
  finishTyping();
  select(selected === w ? null : w);
});

// Clicking a clue selects its word and opens its definition for editing
function openClue(li) {
  const w = li.dataset.word;
  if (editing && editing.word === w) return;
  finishTyping();
  if (painting) painting = false;
  selected = w;
  order = order.filter(o => o !== w);
  order.push(w);
  startEditing(w);
}
document.getElementById("clues").addEventListener("click", e => {
  const li = e.target.closest("li[data-word]");
  if (li && !e.target.closest("input")) openClue(li);
});
document.getElementById("clues").addEventListener("keydown", e => {
  const li = e.target.closest("li[data-word]");
  if (li && e.target === li && e.key === "Enter") { e.preventDefault(); openClue(li); }
});

document.getElementById("across").onclick = () => turn("across");
document.getElementById("down").onclick = () => turn("down");
document.getElementById("remove").onclick = () => selected && removeFromBoard(selected);
document.getElementById("paint").onclick = () => setPainting(!painting);
document.getElementById("all-black").onclick = toggleAllBlack;
for (const name of VIEWS) document.getElementById(name).onclick = () => toggleView(name);
document.getElementById("clear").onclick = () => {
  if ((order.length || manual.size) && !confirm("Remove every word and black cell from the grid?")) return;
  placed = {}; order = []; manual = new Set(); selected = null; typing = null;
  render();
};
// The help popover closes on any click outside it
const help = document.querySelector(".toolbar .help");
document.addEventListener("click", e => { if (help.open && !help.contains(e.target)) help.open = false; });
document.querySelectorAll(".edge button").forEach(btn => {
  btn.addEventListener("click", () => { finishTyping(); resize(btn.dataset.edge, Number(btn.dataset.delta)); });
});

schemaSelect.addEventListener("change", () => {
  finishTyping();
  save();
  loadSchema(store.schemas.find(s => s.id === schemaSelect.value));
});
document.getElementById("schema-new").onclick = () => {
  const name = askName("Name of the new schema:", nextName());
  if (!name) return;
  finishTyping();
  save();
  const schema = newSchema(name);
  store.schemas.push(schema);
  loadSchema(schema);
};
document.getElementById("schema-copy").onclick = () => {
  const name = askName("Name of the copy:", `${current.name} copy`);
  if (!name) return;
  finishTyping();
  save();
  const schema = newSchema(name, JSON.parse(JSON.stringify({rows, cols, placed, order, blocks: [...manual], allBlack})));
  store.schemas.push(schema);
  loadSchema(schema);
};
document.getElementById("schema-rename").onclick = () => {
  const name = askName("New name:", current.name);
  if (!name) return;
  current.name = name;
  renderSchemas();
  save();
};
document.getElementById("schema-delete").onclick = () => {
  if (store.schemas.length < 2 || !confirm(`Delete the schema "${current.name}"?`)) return;
  const i = store.schemas.indexOf(current);
  store.schemas.splice(i, 1);
  loadSchema(store.schemas[Math.max(0, i - 1)]);
};

setSaved(SERVER ? "Saved" : "Saved in this browser");
loadSchema(store.schemas.find(s => s.id === store.current) || store.schemas[0]);
});
</script>
"""


def render_sandbox_page(title="Crossword", store=None):
    """Render the sandbox page served at /.

    Words are typed into the grid, where they can be dragged around, turned
    with H/V and moved with the arrow keys, and black cells are added by hand.
    The sidebar lists the words of the current schema. The page keeps several
    named schemas. With store (the saved data, see read_store) they are saved
    back to the server, otherwise in the browser's localStorage.
    """
    sidebar = """<aside class="side" id="side"><div class="side-inner">
<h2>WORDS (<span id="word-count">0</span>)</h2>
<ul id="word-list"></ul>
<p class="hint" id="words-empty">Click an empty cell in the grid and type a word.</p>
</div></aside>"""
    edges = []
    for edge, line in [("top", "row"), ("left", "column"), ("right", "column"), ("bottom", "row")]:
        edges.append(f"""<div class="edge {edge}">
<button type="button" data-edge="{edge}" data-delta="1" title="Add a {line} ({edge})" aria-label="Add a {line} ({edge})">+</button>
<button type="button" data-edge="{edge}" data-delta="-1" title="Remove the {edge} {line}" aria-label="Remove the {edge} {line}">&minus;</button>
</div>""")
    edges = "\n".join(edges)
    body = f"""<div class="toolbar" role="toolbar" aria-label="Sandbox tools">
<div class="group" role="group" aria-label="Schema">
<span class="label">Schema</span>
<select id="schema" aria-label="Schema"></select>
<button type="button" id="schema-new" title="Start an empty schema (the current one is kept)">New</button>
<button type="button" id="schema-copy" title="Copy the current schema">Duplicate</button>
<button type="button" id="schema-rename">Rename</button>
<button type="button" id="schema-delete" class="danger">Delete</button>
<span class="saved" id="saved" aria-live="polite"></span>
</div>
<div class="group" role="group" aria-label="Selected word">
<span class="label">Word</span>
<button type="button" id="across" title="Across (H)">Across <kbd>H</kbd></button>
<button type="button" id="down" title="Down (V)">Down <kbd>V</kbd></button>
<button type="button" id="remove" title="Take out of the grid (Delete)">Take out <kbd>Del</kbd></button>
</div>
<div class="group" role="group" aria-label="Grid">
<span class="label">Grid</span>
<button type="button" id="paint" title="Add or remove black cells (B)" aria-pressed="false">Black cells <kbd>B</kbd></button>
<button type="button" id="all-black" aria-pressed="false" title="Count every empty cell as black, as in a full rectangular schema. Off: only the cells walled in by letters and the ones added by hand (A)">All black <kbd>A</kbd></button>
<button type="button" id="clear" class="danger" title="Remove every word and black cell">Clear</button>
</div>
<div class="group" role="group" aria-label="View">
<span class="label">View</span>
<button type="button" id="letters" aria-pressed="true" title="Show or hide letters (L)">Letters <kbd>L</kbd></button>
<button type="button" id="numbers" aria-pressed="false" title="Show or hide numbers (N)">Numbers <kbd>N</kbd></button>
<button type="button" id="words" aria-pressed="true" aria-controls="side" title="Show or hide the word list (W)">Words <kbd>W</kbd></button>
<button type="button" id="definitions" aria-pressed="false" aria-controls="clues" title="Show or hide the definitions (D)">Definitions <kbd>D</kbd></button>
</div>
<div class="group end">
<details class="help"><summary>Help</summary>
<p>Click an empty cell and type a word there (<kbd>Tab</kbd> turns it, <kbd>Enter</kbd> keeps it). Drag a word
to move it, or click it in the list to select it. <kbd>H</kbd> / <kbd>V</kbd>: across / down, arrows: move,
<kbd>Del</kbd> or &times; in the list: take it out, <kbd>Esc</kbd>: deselect. Click an empty cell, then a word in
the list, to move that word there.
<kbd>B</kbd>: add black cells. <kbd>A</kbd>: every empty cell
is black, for a full rectangular schema; off, only the cells walled in by letters or added by hand count. <kbd>L</kbd>: letters, <kbd>N</kbd>: numbers, <kbd>W</kbd>: word list,
<kbd>D</kbd>: definitions (click one to write it). The +/&minus; buttons around the grid add or remove
rows and columns. Every schema is saved by itself: New and Duplicate never touch the others.</p>
</details>
</div>
</div>
<p class="sandbox-status" id="status" aria-live="polite"></p>
<div class="board-row">
<div class="board-wrap"><div class="board-frame">
{edges}
<div class="board" id="board"></div>
</div></div>
{sidebar}
</div>
<div class="clues" id="clues" hidden></div>
{SANDBOX_STYLE}"""

    # Keep "</script>" inside the data from closing the script early
    def js(value):
        return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")

    script = SANDBOX_SCRIPT.replace("__STORE__", js(store))
    return page(body + script, title=f"{title} sandbox", wide=True)
