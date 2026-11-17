import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock
from src.crossword.visualize import main, page, serve
from src.crossword.sandbox import read_store, render_sandbox_page, write_store

class MainTests(unittest.TestCase):

    def test_serves_with_store_file(self):
        with mock.patch('src.crossword.visualize.serve') as fake_serve:
            code = main(['--store', 'mine.json', '--port', '9000'])
        self.assertEqual(code, 0)
        self.assertEqual(fake_serve.call_args.kwargs['store_path'], 'mine.json')
        self.assertEqual(fake_serve.call_args.kwargs['port'], 9000)

class PageTests(unittest.TestCase):

    def test_sidebar_can_be_hidden(self):
        html = render_sandbox_page()
        self.assertIn('<aside class="side" id="side">', html)
        self.assertIn('main.side-hidden .side { display: none; }', html)
        self.assertIn('classList.toggle("side-hidden", !view.words)', html)
        # It is on whenever the page opens
        self.assertIn('\nview.words = true;', html)

    def test_word_list_opens_a_definition_popup(self):
        html = render_sandbox_page()
        self.assertIn('<dialog class="def-dialog" id="def-dialog"', html)
        self.assertIn('select(w);\n  openDefinition(w);', html)
        # It can be closed without saving: ×, Cancel, Esc (native) or a click on the backdrop
        self.assertIn('for (const id of ["def-close", "def-cancel"]) document.getElementById(id).onclick = () => defDialog.close();', html)
        self.assertIn('if (e.target === defDialog && downOnBackdrop) defDialog.close();', html)
        # Only Save writes the definition
        self.assertIn('  if (to !== w) renameWord(w, to);\n  setDefinition(to, definition);', html)
        # Shortcuts are off while it is open
        self.assertIn('if (defDialog.open) return;', html)

    def test_word_popup_edits_the_letters(self):
        html = render_sandbox_page()
        start = html.index('<dialog class="def-dialog"')
        self.assertLess(start, html.index('id="word-input"'))
        self.assertLess(html.index('id="word-input"'), html.index('id="def-input"'))
        self.assertIn('function renameWord(w, to)', html)
        # Letters only, never the same word twice, and the grid grows to fit
        self.assertIn('/^\\p{L}+$/u.test(to)', html)
        self.assertIn('to !== w && to in placed', html)
        self.assertIn('  makeRoom(to);\n}', html)

    def test_word_list_marks_words_without_definition(self):
        html = render_sandbox_page()
        self.assertIn('li.classList.toggle("no-def", !store.definitions[w]);', html)
        self.assertIn('.side li.no-def button.pick { font-style: italic; font-weight: 400; color: #555; }', html)
        self.assertIn('.side li button.pick { color: var(--ink); font-weight: 700; }', html)
        # An (i) beside the heading explains the list
        side = html.index('<aside class="side" id="side">')
        self.assertLess(side, html.index('id="words-info"'))
        self.assertIn('id="words-help" role="tooltip"', html)
        # The Words button in the toolbar replaced the title row toggle
        self.assertNotIn('id="side-toggle"', html)

    def test_only_a_wide_page_spans_the_window(self):
        self.assertIn('<main class="wide">', page('<p>x</p>', wide=True))
        self.assertIn('<main>', page('<p>x</p>'))

    def test_title_is_escaped(self):
        html = page('<p>x</p>', title='<b>x</b>')
        self.assertNotIn('<b>x</b>', html)
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', html)

    def test_sidebar_lists_schema_words(self):
        # The list is filled in by the script from the current schema's grid
        html = render_sandbox_page()
        self.assertIn('<ul id="word-list"></ul>', html)
        self.assertIn('const words = [...order].sort();', html)
        self.assertNotIn('typed-list', html)

    def test_word_list_sits_beside_the_board(self):
        html = render_sandbox_page()
        row = html.index('class="board-row"')
        self.assertTrue(row < html.index('id="board"') < html.index('<aside class="side" id="side">'))
        # The list scrolls inside the sidebar instead of stretching it past the board
        self.assertIn('.side-inner { position: absolute; inset: 0 0 0 24px;', html)
        self.assertIn('overflow-y: auto;', html)


class SandboxPageTests(unittest.TestCase):

    def test_page_has_board_and_no_words_file_forms(self):
        html = render_sandbox_page()
        self.assertIn('id="board"', html)
        self.assertNotIn('/generator', html)
        self.assertNotIn('action="/add"', html)
        self.assertNotIn('action="/remove"', html)

    def test_taking_a_word_out_drops_it_from_the_list(self):
        html = render_sandbox_page()
        self.assertIn('if (e.target.closest("button.forget")) { removeFromBoard(w); return; }', html)
        # Old schemas lose their separate list of typed words
        self.assertIn('delete current.typed;', html)

    def test_script_waits_for_page(self):
        html = render_sandbox_page()
        self.assertIn('document.addEventListener("DOMContentLoaded"', html)

    def test_words_get_black_end_cells(self):
        html = render_sandbox_page()
        self.assertIn('function blocksOf(w)', html)
        self.assertIn('.board div.block', html)

    def test_enclosed_empty_cells_are_black(self):
        # Empty cells cut off from the edge by words are inside the schema
        html = render_sandbox_page()
        # and black: empty cells reachable from the edge are grey
        self.assertIn('function outsideSet(map)', html)
        # It comes in from every side of the grid
        self.assertIn('return spread(map, Object.values(edgeLines()).flat());', html)
        self.assertIn('seen.has(k) || map.has(k)) return;', html)
        self.assertIn('here.length ? "filled" : outside.has(k) ? "" : "block"', html)
        # They are counted, and numbered when the view asks for it
        # Only walled-in cells are counted: external ones only with External as black
        self.assertIn('if (!here.length && !outside.has(k) && ++black && view.blackNumbers) {', html)

    def test_external_cells_get_the_darker_grey(self):
        # The cells along a word's sides don't delimit it, only the ones at its ends
        html = render_sandbox_page()
        # External cells (dark grey) are the word ends and the cells within the
        # area the letters span, so a schema closed on all four sides has no light grey
        self.assertIn('const ends = new Set([...outside].filter(k => wordEnds.has(k) || hard.has(k)));', html)
        # Hard external cells spread from the empty cells of the closed sides
        self.assertIn('return spread(map, closed.flat(), open);', html)
        # A cell on an open side is never hard, not even in a corner shared with a closed side
        self.assertIn('if (barred && barred.has(k)) return;', html)
        self.assertIn('const bordering = new Set([...outside].filter(k => !wordEnds.has(k) && inArea(k)));', html)
        # Word ends (real black cells) and bordering cells get different greys
        self.assertIn('.board div.ext { background: #c6c6c6; }', html)
        self.assertIn('.board div.end { background: #7d7d7d; }', html)
        self.assertIn('External as black <kbd>A</kbd></button>', html)
        self.assertNotIn('Outside as black', html)
        self.assertNotIn('touchesLetter', html)

    def test_letters_that_cannot_be_crossed_are_blue(self):
        html = render_sandbox_page()
        self.assertIn('.board div.nocross { background: #e6f0ff; }', html)
        self.assertIn('here.length === 1 && !clash && uncrossable(k, here[0].word) ? "nocross" : ""', html)
        # Black on both sides across the word's direction; past the edge counts as black
        self.assertIn('? isBlack(r - 1, c) && isBlack(r + 1, c)', html)
        self.assertIn('if (!inGrid([r, c])) return true;', html)
        # Grey cells on a closed side of the grid (the schema's margin) block too
        self.assertIn('return wordEnds.has(k) || !walledIn.has(k) || hard.has(k);', html)

    def test_black_share_is_coloured(self):
        html = render_sandbox_page()
        self.assertIn('share <= 15 ? "good" : share <= 22 ? "fair" : "poor"', html)
        for name in ['good', 'fair', 'poor']:
            self.assertIn(f'.sandbox-status .ratio.{name}', html)
        # Hovering (or focusing) the (i) beside it shows the suggested shares
        self.assertIn('id="ratio-info"\naria-describedby="ratio-help"', html)
        self.assertIn('id="ratio-help" role="tooltip"', html)
        self.assertIn('.info:hover .popover, .info:focus-within .popover { display: block; }', html)

    def test_undefined_share_is_red_unless_zero(self):
        html = render_sandbox_page()
        start, end = html.index('id="status"'), html.index('class="board-row"')
        self.assertTrue(start < html.index('id="undefined"') < end)
        self.assertIn('const missing = order.filter(w => !store.definitions[w]).length;', html)
        self.assertIn('undef.className = "ratio " + (missing ? "poor" : "good");', html)
        self.assertIn('Math.ceil(missing / order.length * 100)', html)
        # The word count sits just before it
        self.assertIn('id="word-total"></span><span id="undefined-part">', html)

    def test_grid_size_is_editable(self):
        html = render_sandbox_page()
        start, end = html.index('id="status"'), html.index('class="board-row"')
        for id_ in ['rows', 'cols']:
            self.assertTrue(start < html.index(f'<input type="number" id="{id_}"') < end, id_)
        self.assertIn('function setSize(axis, value)', html)
        self.assertIn('while (size() > n && (shrink(far) || shrink(near)));', html)
        # The status line no longer names the selected word
        self.assertNotIn('selected: ', html)

    def test_save_note_sits_outside_the_toolbar(self):
        html = render_sandbox_page()
        self.assertLess(html.index('class="save-note" id="saved"'), html.index('class="toolbar"'))
        self.assertIn('setSaved("Not saved, retrying…", true)', html)
        self.assertIn('.save-note.error', html)

    def test_all_black_counts_every_empty_cell(self):
        # A full rectangular schema has no outside, so every empty cell is black
        html = render_sandbox_page()
        self.assertIn('id="all-black"', html)
        self.assertIn('const outside = allBlack ? new Set() : outsideSet(map);', html)
        # It belongs to the schema, so it is saved and copied with it
        self.assertIn('{rows, cols, placed, order, allBlack}', html)
        self.assertIn('allBlack = Boolean(schema.allBlack);', html)

    def test_only_letters_keep_an_edge_line(self):
        # An all-grey edge row or column can go, even with black cells on it
        html = render_sandbox_page()
        self.assertIn('return order.flatMap(cellsOf).every(', html)
        self.assertIn('const cells = order.flatMap(blocksOf).filter(inGrid);', html)

    def test_black_cells_are_no_longer_painted_by_hand(self):
        html = render_sandbox_page()
        for gone in ['id="paint"', 'Edit black cells', 'painting', 'manual']:
            self.assertNotIn(gone, html)
        # Black cells saved by hand in older schemas are dropped on the next save
        self.assertIn('delete current.blocks;', html)

    def test_trim_removes_empty_outer_lines(self):
        html = render_sandbox_page()
        grid = html.index('aria-label="Grid"')
        self.assertTrue(grid < html.index('id="trim"') < html.index('aria-label="View"'))
        self.assertIn('Trim <kbd>T</kbd></button>', html)
        self.assertIn('for (const edge of EDGES) while (shrink(edge));', html)
        self.assertIn('if (e.key.toLowerCase() === "t") { e.preventDefault(); trim(); return; }', html)
        self.assertIn('document.getElementById("trim").disabled = !EDGES.some(canShrink);', html)

    def test_typing_mode_is_wired_up(self):
        html = render_sandbox_page()
        self.assertIn('function startTyping(r, c)', html)
        self.assertIn('if (typing) { typeKey(e); return; }', html)
        # The letter test must reach the browser as a real regex, not a Python escape
        self.assertIn('/^\\p{L}$/u.test(e.key)', html)
        # A word typed past the grid makes it grow instead of being cut
        self.assertIn('while (short() && (across ? cols : rows) < MAX_LINES) grow(across ? "right" : "bottom");', html)

    def test_words_keep_room_for_black_cells(self):
        html = render_sandbox_page()
        self.assertIn('function makeRoom(w)', html)
        self.assertIn('order.forEach(makeRoom);', html)

    def test_clicking_a_listed_word_never_moves_it(self):
        # A cell picked on the board no longer pulls the clicked word there
        html = render_sandbox_page()
        self.assertNotIn('if (typing && !typing.text) {', html)
        self.assertNotIn('click one in the list to put it here', html)

    def test_store_is_embedded_or_null(self):
        self.assertIn('let store = null;', render_sandbox_page())
        store = {'current': 'a', 'schemas': [{'id': 'a', 'name': '</script> mine'}]}
        html = render_sandbox_page(store=store)
        self.assertIn('"name": "<\\/script> mine"', html)
        self.assertEqual(html.count('</script>'), 1)

    def test_schema_controls_word_list_and_black_cells(self):
        html = render_sandbox_page()
        for id_ in ['schema', 'schema-new', 'schema-copy', 'schema-rename', 'schema-delete', 'word-list']:
            self.assertIn(f'id="{id_}"', html)
        self.assertLess(html.index('class="side"'), html.index('id="word-list"'))

    def test_schema_bar_sits_apart_from_the_tools(self):
        html = render_sandbox_page()
        # Picking and managing schemas has its own bar
        bar, tools = html.index('class="toolbar schemas"'), html.index('class="toolbar" role="toolbar"')
        for id_ in ['schema', 'schema-new', 'schema-copy', 'schema-rename', 'clear', 'schema-delete']:
            self.assertTrue(bar < html.index(f'id="{id_}"') < tools, id_)
        # The sticky toolbar holds the tools for the current schema
        end = html.index('id="status"')
        for id_ in ['across', 'remove', 'trim', 'letters', 'numbers', 'words', 'definitions']:
            self.assertTrue(tools < html.index(f'id="{id_}"') < end, id_)
        self.assertIn('<details class="help">', html)
        self.assertIn('.toolbar.schemas { position: static;', html)

    def test_view_toggles_sit_together(self):
        html = render_sandbox_page()
        # Letters, numbers, black cell numbers, words and definitions, side by side, each with its key
        ids = [html.index(f'id="{id_}"') for id_ in
               ['letters', 'numbers', 'black-cells', 'words', 'definitions']]
        self.assertEqual(ids, sorted(ids))
        for key in 'LNBWD':
            self.assertIn(f'<kbd>{key}</kbd></button>', html)
        self.assertIn('{name: "blackNumbers", id: "black-cells", key: "b"},', html)
        self.assertIn('Black cells <kbd>B</kbd></button>', html)
        # The definitions have their own toggle, apart from the numbers
        self.assertIn('box.hidden = !view.definitions || !order.length;', html)
        self.assertIn('class="clues" id="clues" hidden', html)
        self.assertIn('function numbering()', html)

    def test_clues_take_definitions(self):
        html = render_sandbox_page()
        self.assertIn('function setDefinition(w, text)', html)
        self.assertIn('#clues li.has-def .word { font-weight: 700; }', html)
        store = {'current': None, 'schemas': [], 'definitions': {'row': 'A line of seats'}}
        self.assertIn('"definitions": {"row": "A line of seats"}', render_sandbox_page(store=store))

    def test_edge_buttons_on_all_four_sides(self):
        html = render_sandbox_page()
        for edge in ['top', 'bottom', 'left', 'right']:
            self.assertIn(f'data-edge="{edge}" data-delta="1"', html)
            self.assertIn(f'data-edge="{edge}" data-delta="-1"', html)

class SandboxStoreTests(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, 'schemas.json')

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_or_broken_file_gives_empty_store(self):
        self.assertEqual(read_store(self.path), {'current': None, 'schemas': []})
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write('not json')
        self.assertEqual(read_store(self.path), {'current': None, 'schemas': []})

    def test_write_then_read(self):
        store = {'current': 'a', 'schemas': [{'id': 'a', 'name': 'Città', 'blocks': ['1,2']}]}
        write_store(self.path, store)
        self.assertEqual(read_store(self.path), store)
        self.assertFalse(os.path.exists(self.path + '.tmp'))

    def test_write_rejects_bad_shape(self):
        with self.assertRaises(ValueError):
            write_store(self.path, {'schemas': 'nope'})
        self.assertFalse(os.path.exists(self.path))


class ServerTests(unittest.TestCase):
    """Load the page and save schemas through a running server."""

    def test_page_and_store_over_http(self):
        import threading
        import urllib.error
        import urllib.request
        from http.server import HTTPServer

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'schemas.json')
            servers = []
            real_init = HTTPServer.__init__

            def capture(server, address, handler):
                real_init(server, ('127.0.0.1', 0), handler)
                servers.append(server)

            with mock.patch.object(HTTPServer, '__init__', capture), redirect_stdout(StringIO()):
                thread = threading.Thread(
                    target=serve, kwargs={'open_browser': False, 'store_path': path}, daemon=True)
                thread.start()
                while not servers:
                    thread.join(0.01)
                base = f'http://127.0.0.1:{servers[0].server_port}'
                try:
                    html = urllib.request.urlopen(base + '/').read().decode()
                    self.assertEqual(html.count('id="board"'), 1)
                    # The page code is reloaded on every request; if that fails,
                    # the last version that loaded is served
                    with mock.patch('importlib.reload', side_effect=SyntaxError('half-saved')) as reload:
                        self.assertIn('id="board"', urllib.request.urlopen(base + '/').read().decode())
                    self.assertTrue(reload.called)
                    # The old sandbox URL redirects to /
                    self.assertTrue(urllib.request.urlopen(base + '/sandbox').geturl().endswith(':%d/' % servers[0].server_port))

                    # There is no generator page, and words can no longer be added or removed
                    for url, data in [('/generator', None), ('/add', b'word=cow'), ('/remove', b'word=cow')]:
                        with self.assertRaises(urllib.error.HTTPError) as err:
                            urllib.request.urlopen(base + url, data=data)
                        self.assertEqual(err.exception.code, 404)

                    store = {'current': 'a', 'schemas': [{'id': 'a', 'name': 'One', 'order': ['cow']}]}
                    req = urllib.request.Request(base + '/store', data=json.dumps(store).encode(),
                                                 headers={'Content-Type': 'application/json'})
                    self.assertEqual(urllib.request.urlopen(req).status, 204)
                    self.assertEqual(read_store(path), store)
                    html = urllib.request.urlopen(base + '/').read().decode()
                    self.assertIn('"name": "One"', html)

                    bad = urllib.request.Request(base + '/store', data=b'[]')
                    with self.assertRaises(urllib.error.HTTPError) as err:
                        urllib.request.urlopen(bad)
                    self.assertEqual(err.exception.code, 400)
                finally:
                    servers[0].shutdown()
                    thread.join(5)
