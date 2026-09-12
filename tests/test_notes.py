import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_notes import ROOT, build, read_note, render_markdown


class NotesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'notes').mkdir()
        (self.root / 'templates').mkdir()
        (self.root / 'templates/notes-page.html').write_text(
            (ROOT / 'templates/notes-page.html').read_text())

    def note(self, name='test', draft='false', date='2026-09-06', body='Hello.'):
        path = self.root / 'notes' / f'{name}.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'---\ntitle: {name}\ndate: {date}\ndescription: A note.\ndraft: {draft}\n---\n{body}')
        return path

    def test_math_and_code_are_preserved(self):
        html = render_markdown(r'''# Introduction

Inline $x_1 = \frac{a}{b}$.

$$
\begin{bmatrix}1 & 2 \\ 3 & 4\end{bmatrix}
$$

`$literal$`

```python
value = "$not_math$"
```

Prices are $5 and $10.
''')
        self.assertIn('<h2 id="introduction">', html)
        self.assertIn(r'\(x_1 = \frac{a}{b}\)', html)
        self.assertIn(r'\begin{bmatrix}1 &amp; 2 \\ 3 &amp; 4\end{bmatrix}', html)
        self.assertIn('<code>$literal$</code>', html)
        self.assertIn('$not_math$', html)
        self.assertIn('Prices are $5 and $10.', html)
        self.assertEqual(html.count('class="math inline"'), 1)
        self.assertEqual(html.count('<div class="math block'), 1)

    def test_display_math_does_not_require_blank_lines(self):
        html = render_markdown(r'''Before the equation:
$$
J = \mathbb{E}\left[\sum_{i=1}^{T} r_i\right]
$$
After the equation.

```text
$$
not mathematics
$$
```
''')
        self.assertIn('<p>Before the equation:</p>', html)
        self.assertIn(r'\[J = \mathbb{E}\left[\sum_{i=1}^{T} r_i\right]\]', html)
        self.assertIn('<p>After the equation.</p>', html)
        self.assertEqual(html.count('<div class="math block'), 1)
        self.assertEqual(html.count('class="math block math-unframed"'), 1)
        self.assertIn('not mathematics', html)
        self.assertIn('<code class="language-text">', html)

        framed = render_markdown('Before.\n\n$$\nx+y\n$$\n')
        self.assertIn('class="math block"', framed)
        self.assertNotIn('math-unframed', framed)

        labelled = render_markdown(
            'Before.\n$$\nx+y\n$$ (policy-objective)\nAfter.\n\n$$\ny+z\n$$\n')
        self.assertIn(
            '<div id="policy-objective" class="math block math-unframed">', labelled)
        self.assertIn('<p>After.</p>', labelled)
        self.assertEqual(labelled.count('<div'), 2)

    def test_mermaid_fences_render_as_diagrams(self):
        html = render_markdown('''```mermaid
flowchart LR
    A[Observations] --> B[Policy]
```

```python
print("still code")
```
''')
        self.assertIn('<figure class="mermaid-figure">', html)
        self.assertIn('<pre class="mermaid" role="img" aria-label="Mermaid diagram">', html)
        self.assertIn('A[Observations] --&gt; B[Policy]', html)
        self.assertIn('<summary>Diagram source</summary>', html)
        self.assertIn('<code class="language-python">', html)

    def test_mermaid_scripts_load_only_on_diagram_pages(self):
        self.note('diagram', body='```mermaid\nflowchart LR\nA --> B\n```')
        self.note('plain', body='No diagram.')
        build(self.root)
        diagram = (self.root / 'notes/diagram.html').read_text()
        plain = (self.root / 'notes/plain.html').read_text()
        listing = (self.root / 'notes.html').read_text()
        self.assertIn('assets/vendor/mermaid/mermaid.min.js', diagram)
        self.assertIn('assets/mermaid.js', diagram)
        self.assertNotIn('assets/vendor/mermaid/mermaid.min.js', plain)
        self.assertNotIn('assets/vendor/mermaid/mermaid.min.js', listing)

    def test_drafts_and_stale_generated_files(self):
        source = self.note(draft='true')
        manual = self.root / 'notes/manual.html'
        manual.write_text('<p>Keep me.</p>')
        self.assertEqual(build(self.root, include_drafts=True), 1)
        self.assertIn('noindex', source.with_suffix('.html').read_text())
        self.assertIn('notes/test.html', (self.root / 'notes.html').read_text())
        self.assertEqual(build(self.root), 0)
        self.assertFalse(source.with_suffix('.html').exists())
        self.assertNotIn('notes/test.html', (self.root / 'notes.html').read_text())
        self.assertTrue(manual.exists())
        self.note(draft='false')
        build(self.root)
        source.rename(source.with_name('renamed.md'))
        build(self.root)
        self.assertFalse(source.with_suffix('.html').exists())
        self.assertTrue(source.with_name('renamed.html').exists())

    def test_relative_links_assets_and_sorting(self):
        self.note('older', date='2026-01-01')
        self.note('topic/newer', body='![Figure](attachments/figure.png)\n\n[Old note](../older.md#heading)')
        build(self.root)
        html = (self.root / 'notes/topic/newer.html').read_text()
        self.assertIn('src="attachments/figure.png"', html)
        self.assertIn('href="../older.html#heading"', html)
        self.assertIn('href="../../styles.css"', html)
        index = (self.root / 'notes.html').read_text()
        self.assertLess(index.index('notes/topic/newer.html'), index.index('notes/older.html'))
        self.assertNotIn('<footer', html)

    def test_invalid_properties_leave_previous_output_untouched(self):
        self.note()
        build(self.root)
        before = (self.root / 'notes.html').read_text()
        self.note(draft='"false"')
        with self.assertRaisesRegex(ValueError, 'draft must be true or false'):
            build(self.root)
        self.assertEqual((self.root / 'notes.html').read_text(), before)
        bad = self.note(date='not-a-date')
        with self.assertRaisesRegex(ValueError, 'YYYY-MM-DD'):
            read_note(bad)

    def test_manual_page_is_not_overwritten(self):
        self.note()
        page = self.root / 'notes/test.html'
        page.write_text('A hand-written page')
        with self.assertRaisesRegex(ValueError, 'refusing to overwrite'):
            build(self.root)
        self.assertEqual(page.read_text(), 'A hand-written page')


if __name__ == '__main__':
    unittest.main()
