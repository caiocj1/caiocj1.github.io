import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_notes import ROOT
from preview import PreviewState, create_server


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'notes').mkdir()
        (self.root / 'templates').mkdir()
        (self.root / 'templates/notes-page.html').write_text(
            (ROOT / 'templates/notes-page.html').read_text())
        self.note = self.root / 'notes/test.md'
        self.note.write_text('---\ntitle: Test\ndate: 2026-09-06\ndescription: Test.\ndraft: true\n---\nFirst version.')

    def test_revision_changes_on_source_edits_not_generated_pages(self):
        state = PreviewState(self.root)
        first = state.refresh()
        self.assertEqual(first, state.refresh())
        (self.root / 'notes/test.html').touch()
        self.assertEqual(first, state.refresh())
        self.note.write_text(self.note.read_text().replace('First version.', 'Updated version.'))
        second = state.refresh()
        self.assertNotEqual(first, second)
        self.assertEqual(second, state.refresh())
        self.assertIn('Updated version.', (self.root / 'notes/test.html').read_text())
        self.assertNotIn('math-preview.html', (self.root / 'notes.html').read_text())

    def test_bad_edits_can_recover(self):
        state = PreviewState(self.root)
        first = state.refresh()
        original = self.note.read_text()
        self.note.write_text('An unfinished edit')
        with self.assertRaises(ValueError):
            state.refresh()
        self.assertEqual(first, state.revision)
        self.note.write_text(original + '\nRecovered.')
        self.assertNotEqual(first, state.refresh())

    def test_http_reload_client_and_changed_revision(self):
        server = create_server(self.root, 0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def get(path):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
            connection.request('GET', path)
            response = connection.getresponse()
            result = response.status, dict(response.getheaders()), response.read().decode()
            connection.close()
            return result
        status, headers, html = get('/notes/test.html')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(int(headers['Content-Length']), len(html.encode()))
        self.assertIn('data-local-preview', html)
        self.assertNotIn('data-local-preview', (self.root / 'notes/test.html').read_text())
        revision = json.loads(get('/__preview__/revision')[2])['revision']
        self.note.write_text(self.note.read_text() + '\nSecond version.')
        changed = json.loads(get('/__preview__/revision')[2])['revision']
        self.assertNotEqual(revision, changed)
        self.assertIn('Second version.', get('/notes/test.html')[2])

    def test_metadata_updates_without_browser_requests_after_rename(self):
        server = create_server(self.root, 0)
        worker = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        renamed = self.note.with_name('renamed.md')
        self.note.rename(renamed)
        renamed.write_text(renamed.read_text().replace('title: Test', 'title: Updated title').replace('description: Test.', 'description: Updated description.'))
        output = renamed.with_suffix('.html')
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if output.exists() and 'Updated description.' in output.read_text():
                break
            time.sleep(0.02)
        # Wait for the whole build, including the index and stale-page cleanup.
        with server.preview_state.lock:
            html = output.read_text()
            index = (self.root / 'notes.html').read_text()
        self.assertIn('<title>Updated title — Caio Azevedo</title>', html)
        self.assertIn('<h1>Updated title</h1>', html)
        self.assertIn('name="description" content="Updated description."', html)
        self.assertIn('<p>Updated description.</p>', html)
        self.assertIn('Updated title', index)
        self.assertIn('Updated description.', index)
        self.assertFalse(self.note.with_suffix('.html').exists())
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
        connection.request('GET', '/notes/test.html')
        response = connection.getresponse()
        self.assertEqual(response.status, 302)
        self.assertEqual(response.getheader('Location'), '/notes.html')
        response.read()
        connection.close()


if __name__ == '__main__':
    unittest.main()
