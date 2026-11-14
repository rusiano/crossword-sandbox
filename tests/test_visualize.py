import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock
from src.crossword.visualize import add_words_to_file, main, page, parse_words, read_words, remove_word_from_file, serve
from src.crossword.sandbox import read_store, render_sandbox_page, store_path_for, write_store

class ParseWordsTests(unittest.TestCase):

    def test_plain_text_one_per_line(self):
        self.assertEqual(parse_words('cat\ndog\n\nbird\n'), ['cat', 'dog', 'bird'])

    def test_markdown_lists_headings_and_comments(self):
        text = '# My words\n<!-- ignore\nthis -->\n- cat\n* **dog**\n1. `bird`\n## More\n'
        self.assertEqual(parse_words(text), ['cat', 'dog', 'bird'])

    def test_separators_case_and_duplicates(self):
        self.assertEqual(parse_words('Cat, dog  CAT\ndog'), ['cat', 'dog'])

    def test_apostrophes_and_hyphens_are_joined(self):
        self.assertEqual(parse_words("don't\nx-ray"), ['dont', 'xray'])

    def test_unicode_letters_kept(self):
        self.assertEqual(parse_words('città\ncaffè'), ['città', 'caffè'])

class MainTests(unittest.TestCase):

    def test_serves_words_from_file_and_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            words_path = os.path.join(tmp, 'words.md')
            with open(words_path, 'w', encoding='utf-8') as f:
                f.write('# Words\n- cross\n- sword\n')
            with mock.patch('src.crossword.visualize.serve') as fake_serve:
                code = main(['Row', '-f', words_path, '--port', '9000'])
            self.assertEqual(code, 0)
            get_words = fake_serve.call_args.args[0]
            self.assertEqual(get_words(), ['row', 'cross', 'sword'])
            self.assertEqual(fake_serve.call_args.kwargs['words_file'], words_path)
            self.assertEqual(fake_serve.call_args.kwargs['port'], 9000)

class PageTests(unittest.TestCase):

    def test_sidebar_can_be_hidden(self):
        html = render_sandbox_page(['cross', 'sword'])
        self.assertIn('id="side-toggle"', html)
        self.assertIn('aria-controls="side"', html)
        self.assertIn('<aside class="side" id="side">', html)
        self.assertIn('main.side-hidden .side { display: none; }', html)
        # The toggle script finds the sidebar, so it must come after it
        self.assertLess(html.index('class="side"'), html.index('crossword-side-hidden'))

    def test_page_without_sidebar_has_no_toggle(self):
        self.assertNotIn('id="side-toggle"', page('<p>x</p>'))

    def test_title_is_escaped(self):
        html = page('<p>x</p>', title='<b>x</b>')
        self.assertNotIn('<b>x</b>', html)
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', html)

    def test_sidebar_is_alphabetical(self):
        import re
        words = ['sword', 'cross', 'row']
        listed = re.findall(r'<li data-word="([^"]+)">', render_sandbox_page(words))
        self.assertEqual(listed, sorted(words))


class SandboxPageTests(unittest.TestCase):

    words = ['sword', 'cross', 'row']

    def test_words_are_pickable_and_embedded(self):
        html = render_sandbox_page(self.words)
        self.assertIn('id="board"', html)
        self.assertIn('<li data-word="sword"><button type="button" class="pick">sword</button>', html)
        self.assertIn('const WORDS = ["cross", "row", "sword"];', html)
        self.assertNotIn('/generator', html)
        self.assertNotIn('action="/add"', html)

    def test_editable_forms_return_to_sandbox(self):
        html = render_sandbox_page(self.words, editable=True)
        self.assertIn('action="/add"', html)
        self.assertIn('action="/remove"', html)
        self.assertNotIn('name="next"', html)

    def test_script_waits_for_sidebar(self):
        # The script comes before the sidebar, so it must not run until the page is parsed
        html = render_sandbox_page(self.words)
        self.assertLess(html.index('<script>'), html.index('class="side"'))
        self.assertIn('document.addEventListener("DOMContentLoaded"', html)

    def test_grid_fits_longest_word(self):
        html = render_sandbox_page(['a' * 20, 'cat'])
        self.assertIn('const DEFAULT_SIZE = 20;', html)

    def test_words_get_black_end_cells(self):
        html = render_sandbox_page(self.words)
        self.assertIn('function blocksOf(w)', html)
        self.assertIn('.board div.block', html)

    def test_enclosed_empty_cells_are_black(self):
        # Empty cells cut off from the edge by words are inside the schema
        html = render_sandbox_page(self.words)
        # and only those are black: black cells reachable from the edge are grey
        self.assertIn('function outsideSet(map)', html)
        self.assertIn('here.length ? "filled" : outside.has(k) ? "" : "block"', html)
        self.assertIn('.board.painting div.painted', html)
        # They are numbered so they can be counted
        self.assertIn('count.textContent = ++black;', html)

    def test_only_letters_keep_an_edge_line(self):
        # An all-grey edge row or column can go, even with black cells on it
        html = render_sandbox_page(self.words)
        self.assertIn('return order.flatMap(cellsOf).every(', html)
        self.assertIn('[...order.flatMap(blocksOf), ...manualCells()].filter(inGrid)', html)

    def test_typing_mode_is_wired_up(self):
        html = render_sandbox_page(self.words)
        self.assertIn('function startTyping(r, c)', html)
        self.assertIn('if (typing) { typeKey(e); return; }', html)
        # The letter test must reach the browser as a real regex, not a Python escape
        self.assertIn('/^\\p{L}$/u.test(e.key)', html)

    def test_words_keep_room_for_black_cells(self):
        html = render_sandbox_page(self.words)
        self.assertIn('function makeRoom(w)', html)
        self.assertIn('order.forEach(makeRoom);', html)

    def test_picked_word_goes_to_picked_cell(self):
        html = render_sandbox_page(self.words)
        self.assertIn('if (typing && !typing.text) {', html)

    def test_store_is_embedded_or_null(self):
        self.assertIn('let store = null;', render_sandbox_page(self.words))
        store = {'current': 'a', 'schemas': [{'id': 'a', 'name': '</script> mine'}]}
        html = render_sandbox_page(self.words, store=store)
        self.assertIn('"name": "<\\/script> mine"', html)
        # The sandbox script and the sidebar toggle
        self.assertEqual(html.count('</script>'), 2)

    def test_schema_controls_typed_list_and_black_cells(self):
        html = render_sandbox_page(self.words)
        for id_ in ['schema', 'schema-new', 'schema-copy', 'schema-rename', 'schema-delete', 'paint', 'typed-list']:
            self.assertIn(f'id="{id_}"', html)
        # The typed list sits in the sidebar, under the words file list
        self.assertLess(html.index('class="side"'), html.index('id="typed-list"'))

    def test_one_toolbar_holds_every_control(self):
        html = render_sandbox_page(self.words)
        start, end = html.index('class="toolbar"'), html.index('id="status"')
        for id_ in ['schema', 'schema-new', 'across', 'remove', 'paint', 'clear', 'letters', 'numbers']:
            self.assertTrue(start < html.index(f'id="{id_}"') < end, id_)
        self.assertIn('<details class="help">', html)

    def test_letter_and_number_toggles(self):
        html = render_sandbox_page(self.words)
        self.assertIn('id="letters"', html)
        self.assertIn('id="numbers"', html)
        self.assertIn('class="clues" id="clues" hidden', html)
        self.assertIn('function numbering()', html)

    def test_clues_take_definitions(self):
        html = render_sandbox_page(self.words)
        self.assertIn('function setDefinition(w, text)', html)
        self.assertIn('#clues li.has-def .word { font-weight: 700; }', html)
        store = {'current': None, 'schemas': [], 'definitions': {'row': 'A line of seats'}}
        self.assertIn('"definitions": {"row": "A line of seats"}', render_sandbox_page(self.words, store=store))

    def test_edge_buttons_on_all_four_sides(self):
        html = render_sandbox_page(self.words)
        for edge in ['top', 'bottom', 'left', 'right']:
            self.assertIn(f'data-edge="{edge}" data-delta="1"', html)
            self.assertIn(f'data-edge="{edge}" data-delta="-1"', html)

    def test_script_tag_in_word_cannot_close_script(self):
        html = render_sandbox_page(['</script>'])
        # The sandbox script and the sidebar toggle
        self.assertEqual(html.count('</script>'), 2)

class SandboxStoreTests(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, 'words.sandbox.json')

    def tearDown(self):
        self.dir.cleanup()

    def test_path_follows_words_file(self):
        self.assertEqual(store_path_for(os.path.join('a', 'words.md')), os.path.join('a', 'words.sandbox.json'))

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


class WordsFileEditTests(unittest.TestCase):

    CONTENT = """# Words

<!--
- cat stays in this comment
-->

- cat
- dog
bird, cat, fish
"""

    def setUp(self):
        import tempfile
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, 'words.md')
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(self.CONTENT)

    def tearDown(self):
        self.dir.cleanup()

    def read(self):
        with open(self.path, encoding='utf-8') as f:
            return f.read()

    def test_add_appends_new_words_only(self):
        added = add_words_to_file(self.path, 'Owl, dog  newt')
        self.assertEqual(added, ['owl', 'newt'])
        self.assertTrue(self.read().endswith('bird, cat, fish\n- owl\n- newt\n'))

    def test_add_without_trailing_newline(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write('- cat')
        add_words_to_file(self.path, 'dog')
        self.assertEqual(self.read(), '- cat\n- dog\n')

    def test_remove_drops_line_and_cuts_from_shared_line(self):
        remove_word_from_file(self.path, 'cat')
        text = self.read()
        self.assertIn('- cat stays in this comment', text)
        self.assertNotIn('\n- cat\n', text)
        self.assertIn('\nbird, fish\n', text)
        self.assertEqual(parse_words(text), ['dog', 'bird', 'fish'])

    def test_remove_unknown_word_changes_nothing(self):
        remove_word_from_file(self.path, 'zebra')
        self.assertEqual(self.read(), self.CONTENT)


class ServerEditTests(unittest.TestCase):
    """Add and remove words through a running server."""

    def test_add_and_remove_over_http(self):
        import tempfile
        import threading
        import urllib.error
        import urllib.parse
        import urllib.request
        from unittest import mock
        from http.server import HTTPServer

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'words.md')
            with open(path, 'w', encoding='utf-8') as f:
                f.write('- cross\n- word\n- sword\n')

            servers = []
            real_init = HTTPServer.__init__

            def capture(server, address, handler):
                real_init(server, ('127.0.0.1', 0), handler)
                servers.append(server)

            with mock.patch.object(HTTPServer, '__init__', capture), redirect_stdout(StringIO()):
                thread = threading.Thread(
                    target=serve, args=(lambda: read_words(path),),
                    kwargs={'open_browser': False, 'words_file': path},
                    daemon=True)
                thread.start()
                while not servers:
                    thread.join(0.01)
                base = f'http://127.0.0.1:{servers[0].server_port}'
                try:
                    def post(action, word):
                        data = urllib.parse.urlencode({'word': word}).encode()
                        return urllib.request.urlopen(base + action, data=data).read().decode()

                    html = post('/add', 'rows')
                    self.assertEqual(read_words(path), ['cross', 'word', 'sword', 'rows'])
                    self.assertIn('WORDS (4)', html)
                    self.assertIn('id="board"', html)

                    html = post('/remove', 'word')
                    self.assertEqual(read_words(path), ['cross', 'sword', 'rows'])
                    self.assertIn('WORDS (3)', html)

                    html = urllib.request.urlopen(base + '/').read().decode()
                    self.assertIn('id="board"', html)
                    self.assertIn('WORDS (3)', html)
                    # The old sandbox URL redirects to /
                    self.assertTrue(urllib.request.urlopen(base + '/sandbox').geturl().endswith(':%d/' % servers[0].server_port))

                    # There is no generator page
                    with self.assertRaises(urllib.error.HTTPError) as err:
                        urllib.request.urlopen(base + '/generator')
                    self.assertEqual(err.exception.code, 404)
                    self.assertEqual(post('/add', 'cow').count('id="board"'), 1)
                    self.assertEqual(read_words(path), ['cross', 'sword', 'rows', 'cow'])

                    store = {'current': 'a', 'schemas': [{'id': 'a', 'name': 'One', 'order': ['cow']}]}
                    req = urllib.request.Request(base + '/store', data=json.dumps(store).encode(),
                                                 headers={'Content-Type': 'application/json'})
                    self.assertEqual(urllib.request.urlopen(req).status, 204)
                    self.assertEqual(read_store(store_path_for(path)), store)
                    html = urllib.request.urlopen(base + '/').read().decode()
                    self.assertIn('"name": "One"', html)

                    bad = urllib.request.Request(base + '/store', data=b'[]')
                    with self.assertRaises(urllib.error.HTTPError) as err:
                        urllib.request.urlopen(bad)
                    self.assertEqual(err.exception.code, 400)
                finally:
                    servers[0].shutdown()
                    thread.join(5)

