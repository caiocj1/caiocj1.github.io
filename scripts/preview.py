#!/usr/bin/env python3
"""Preview Markdown notes with rebuilding, automatic reload, and no browser caching."""
import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

from build_notes import ROOT, build

RELOAD_SCRIPT = '''<script data-local-preview>
(() => {
  const revision = __REVISION__;
  async function checkForChanges() {
    try {
      const response = await fetch('/__preview__/revision', {cache: 'no-store'});
      if (response.ok) {
        const next = await response.json();
        if (next.revision !== revision) {
          location.reload();
          return;
        }
      }
    } catch (_) {
      // Keep the current page usable while the preview server is restarting.
    }
    setTimeout(checkForChanges, 1000);
  }
  setTimeout(checkForChanges, 1000);
})();
</script>'''


class PreviewState:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.Lock()
        self.revision = None

    def fingerprint(self):
        paths = [self.root / 'styles.css']
        paths.extend(p for p in self.root.glob('*.html') if p.name != 'notes.html')
        for folder in ('notes', 'templates', 'assets'):
            for path in (self.root / folder).rglob('*'):
                relative = path.relative_to(self.root / folder)
                if any(part.startswith('.') for part in relative.parts):
                    continue
                if folder == 'notes' and path.suffix == '.html':
                    continue  # Generated article pages must not trigger a reload loop.
                if path.is_file():
                    paths.append(path)
        digest = hashlib.sha256()
        for path in sorted(paths):
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue  # An editor may replace a file atomically while scanning.
            digest.update(f'{path.relative_to(self.root)}:{stat.st_mtime_ns}:{stat.st_size}\n'.encode())
        return digest.hexdigest()

    def refresh(self):
        with self.lock:
            current = self.fingerprint()
            if current != self.revision:
                build(self.root, include_drafts=True)
                self.revision = current
            return self.revision


class PreviewServer(ThreadingHTTPServer):
    def service_actions(self):
        # Rebuild even when no browser is open or an old note URL was renamed.
        try:
            self.preview_state.refresh()
            self.last_build_error = None
        except Exception as error:
            message = str(error)
            if message != getattr(self, 'last_build_error', None):
                print(f'Could not build notes: {message}', flush=True)
            self.last_build_error = message


class PreviewHandler(SimpleHTTPRequestHandler):
    def log_request(self, code='-', size='-'):
        if urlsplit(self.path).path != '/__preview__/revision':
            super().log_request(code, size)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def response_file(self, body, content_type):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        return BytesIO(body)

    def send_head(self):
        request_path = urlsplit(self.path).path
        try:
            if request_path == '/__preview__/revision':
                revision = self.server.preview_state.refresh()
                return self.response_file(json.dumps({'revision': revision}).encode(), 'application/json')
            if request_path.endswith(('/', '.html')):
                revision = self.server.preview_state.refresh()
                path = Path(self.translate_path(self.path))
                if path.is_dir():
                    path = path / 'index.html'
                if path.is_file() and path.suffix == '.html':
                    script = RELOAD_SCRIPT.replace('__REVISION__', json.dumps(revision))
                    html = path.read_text().replace('</body>', script + '\n</body>')
                    return self.response_file(html.encode(), 'text/html; charset=utf-8')
                if request_path.startswith('/notes/') and path.suffix == '.html' and not path.exists():
                    self.send_response(302)
                    self.send_header('Location', '/notes.html')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return BytesIO(b'')
        except Exception as error:
            self.send_error(500, f'Could not build notes: {error}')
            return None
        if 'If-Modified-Since' in self.headers:
            del self.headers['If-Modified-Since']
        return super().send_head()


def create_server(root=ROOT, port=8000):
    state = PreviewState(root)
    state.refresh()
    handler = partial(PreviewHandler, directory=str(root))
    server = PreviewServer(('127.0.0.1', port), handler)
    server.preview_state = state
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    with create_server(port=args.port) as server:
        print(f'Preview: http://localhost:{args.port}/notes.html (includes drafts)', flush=True)
        print('Save in Obsidian; open pages reload automatically. Ctrl+C stops the server.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
