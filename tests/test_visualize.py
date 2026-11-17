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
        # and black, with the ones added by hand: black cells reachable from the
        # edge are grey. Cells added by hand also wall off what is behind them
        self.assertIn('function outsideSet(map, walls)', html)
        self.assertIn('map.has(k) || walls.has(k)) return;', html)
        self.assertIn('here.length ? "filled" : outside.has(k) ? "" : "block"', html)
        self.assertIn('.board.painting div.painted', html)
        # They are numbered so they can be counted
        self.assertIn('count.textContent = ++black;', html)

    def test_black_share_is_coloured(self):
        html = render_sandbox_page()
        self.assertIn('share <= 15 ? "good" : share <= 22 ? "fair" : "poor"', html)
        for name in ['good', 'fair', 'poor']:
            self.assertIn(f'.sandbox-status .ratio.{name}', html)

    def test_all_black_counts_every_empty_cell(self):
        # A full rectangular schema has no outside, so every empty cell is black
        html = render_sandbox_page()
        self.assertIn('id="all-black"', html)
        self.assertIn('const outside = allBlack ? new Set() : outsideSet(map, hand);', html)
        # It belongs to the schema, so it is saved and copied with it
        self.assertIn('blocks: [...manual], allBlack}', html)
        self.assertIn('allBlack = Boolean(schema.allBlack);', html)

    def test_only_letters_keep_an_edge_line(self):
        # An all-grey edge row or column can go, even with black cells on it
        html = render_sandbox_page()
        self.assertIn('return order.flatMap(cellsOf).every(', html)
        self.assertIn('[...order.flatMap(blocksOf), ...manualCells()].filter(inGrid)', html)

    def test_typing_mode_is_wired_up(self):
        html = render_sandbox_page()
        self.assertIn('function startTyping(r, c)', html)
        self.assertIn('if (typing) { typeKey(e); return; }', html)
        # The letter test must reach the browser as a real regex, not a Python escape
        self.assertIn('/^\\p{L}$/u.test(e.key)', html)

    def test_words_keep_room_for_black_cells(self):
        html = render_sandbox_page()
        self.assertIn('function makeRoom(w)', html)
        self.assertIn('order.forEach(makeRoom);', html)

    def test_picked_word_goes_to_picked_cell(self):
        html = render_sandbox_page()
        self.assertIn('if (typing && !typing.text) {', html)

    def test_store_is_embedded_or_null(self):
        self.assertIn('let store = null;', render_sandbox_page())
        store = {'current': 'a', 'schemas': [{'id': 'a', 'name': '</script> mine'}]}
        html = render_sandbox_page(store=store)
        self.assertIn('"name": "<\\/script> mine"', html)
        self.assertEqual(html.count('</script>'), 1)

    def test_schema_controls_word_list_and_black_cells(self):
        html = render_sandbox_page()
        for id_ in ['schema', 'schema-new', 'schema-copy', 'schema-rename', 'schema-delete', 'paint', 'word-list']:
            self.assertIn(f'id="{id_}"', html)
        self.assertLess(html.index('class="side"'), html.index('id="word-list"'))

    def test_one_toolbar_holds_every_control(self):
        html = render_sandbox_page()
        start, end = html.index('class="toolbar"'), html.index('id="status"')
        for id_ in ['schema', 'schema-new', 'across', 'remove', 'paint', 'clear',
                    'letters', 'numbers', 'words', 'definitions']:
            self.assertTrue(start < html.index(f'id="{id_}"') < end, id_)
        self.assertIn('<details class="help">', html)

    def test_view_toggles_sit_together(self):
        html = render_sandbox_page()
        # Letters, numbers, words and definitions, side by side, each with its key
        ids = [html.index(f'id="{id_}"') for id_ in ['letters', 'numbers', 'words', 'definitions']]
        self.assertEqual(ids, sorted(ids))
        for key in 'LNWD':
            self.assertIn(f'<kbd>{key}</kbd></button>', html)
        self.assertIn('const VIEWS = ["letters", "numbers", "words", "definitions"];', html)
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
