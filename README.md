# caiocj1.github.io

Personal academic website for Caio Azevedo, built as a dependency-free static site for GitHub Pages.

## Local preview

From the repository root, run:

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Then open <http://localhost:8000>.

## Structure

- `index.html` — home and profile
- `publications.html` — publication record
- `notes.html` — future writing and blog posts
- `styles.css` — shared visual system and responsive styles
- `assets/` — portrait, PDF CV, and favicon
- `sitemap.xml` and `robots.txt` — search-engine discovery

The site uses plain HTML and CSS, so GitHub Pages can publish it directly from the repository root.
