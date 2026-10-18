"""Build PREVIEW.html from ARTICLE.md so the preview always shows the exact article text.

Run with a Python that has the `markdown` package (no project dependency is added):
    python -m uv run --no-project --with markdown --with pillow python build_preview.py
"""
import html
import pathlib
import re

import markdown

ROOT = pathlib.Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "ARTICLE.md"
PREVIEW = ROOT / "PREVIEW.html"

FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
         "&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400"
         "&display=swap")

CSS = """
:root {
  --paper: #FBFAF7; --ink: #1B1F29; --ink-2: #3A4150; --muted: #6B7280; --line: #E4DFD5;
  --accent: #D2491A; --teal: #0E7C7B; --code-bg: #14171F; --code-ink: #E8E6E1;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--paper); color: var(--ink);
  font: 400 19px/1.68 'Source Serif 4', Georgia, 'Times New Roman', serif; }
main { max-width: 720px; margin: 0 auto; padding: 56px 20px 96px; }
.kicker { font: 600 13px/1 Inter, 'Segoe UI', sans-serif; letter-spacing: .14em; text-transform: uppercase;
  color: var(--teal); margin: 0 0 18px; }
h1 { font: 700 44px/1.12 Inter, 'Segoe UI', sans-serif; letter-spacing: -.02em; margin: 0 0 18px; }
.dek { font-size: 22px; line-height: 1.5; color: var(--ink-2); margin: 0 0 14px; }
.dek em { font-style: normal; }
.byline { font: 500 14px/1.4 Inter, 'Segoe UI', sans-serif; color: var(--muted); margin: 0 0 36px;
  padding-bottom: 28px; border-bottom: 1px solid var(--line); }
h2 { font: 700 28px/1.25 Inter, 'Segoe UI', sans-serif; letter-spacing: -.01em; margin: 64px 0 16px; }
h3 { font: 700 21px/1.3 Inter, 'Segoe UI', sans-serif; margin: 40px 0 12px; }
p { margin: 0 0 22px; }
a { color: var(--teal); text-decoration-thickness: 1px; text-underline-offset: 3px; }
strong { font-weight: 600; }
code { font: 500 .84em 'JetBrains Mono', Consolas, monospace; background: #EFEBE3; padding: .1em .35em;
  border-radius: 4px; }
pre { background: var(--code-bg); color: var(--code-ink); padding: 18px 20px; border-radius: 10px; overflow-x: auto;
  margin: 0 0 26px; font: 400 14.5px/1.6 'JetBrains Mono', Consolas, monospace; }
pre code { background: none; padding: 0; font: inherit; color: inherit; }
code, pre { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }
figure.shot-fig:not(.wide) { margin-left: auto; margin-right: auto; }
blockquote { margin: 0 0 26px; padding: 18px 22px; background: #EEF5F3; border-left: 4px solid var(--teal);
  border-radius: 0 10px 10px 0; font: 500 18px/1.6 Inter, 'Segoe UI', sans-serif; color: var(--ink-2); }
blockquote p { margin: 0; }
figure { margin: 34px 0 34px; }
figure img { display: block; width: 100%; height: auto; border-radius: 10px; border: 1px solid var(--line);
  background: #fff; }
figure.wide { margin-left: -60px; margin-right: -60px; }
figure.hero { margin: 8px -120px 40px; }
figure.hero img { border: 0; border-radius: 12px; }
figcaption { font: 400 14.5px/1.55 Inter, 'Segoe UI', sans-serif; color: var(--muted); margin-top: 10px; }
figcaption em { font-style: normal; }
.shot { font: 600 11px/1 Inter, 'Segoe UI', sans-serif; letter-spacing: .1em; text-transform: uppercase;
  color: var(--accent); margin-right: 6px; }
hr { border: 0; border-top: 1px solid var(--line); margin: 56px 0 28px; }
.footnote { font: 400 15px/1.6 Inter, 'Segoe UI', sans-serif; color: var(--muted); }
.footnote em { font-style: normal; }
@media (max-width: 1000px) { figure.wide, figure.hero { margin-left: 0; margin-right: 0; } }
@media (max-width: 600px) {
  body { font-size: 17.5px; }
  main { padding: 32px 16px 64px; }
  h1 { font-size: 32px; }
  .dek { font-size: 19px; }
  h2 { font-size: 24px; margin-top: 48px; }
  pre { font-size: 13px; padding: 14px; }
}
"""


def build() -> None:
    text = ARTICLE.read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", text, flags=re.M).group(1)
    body = markdown.markdown(text, extensions=["fenced_code", "sane_lists"], output_format="html5")

    # The H1 and the italic standfirst become the article header.
    body = re.sub(r"<h1>.*?</h1>\s*", "", body, count=1, flags=re.S)
    body = re.sub(r"<p><em>(.*?)</em></p>",
                  lambda m: f'<p class="dek"><em>{m.group(1)}</em></p>\n'
                            '<p class="byline">By Manjunatha S K · October 2026 · Built for WeMakeDevs × FalkorDB Graph Hacks</p>',
                  body, count=1, flags=re.S)

    # An image followed by an italic line becomes a figure with a caption.
    def figure(m: re.Match) -> str:
        attrs, caption = m.group(1), m.group(2)
        src = re.search(r'src="([^"]+)"', attrs).group(1)
        style = ""
        if "/screenshots/" in src:
            # Screenshots are captured at 2x: never show them larger than their natural CSS size.
            from PIL import Image
            natural = Image.open(ROOT / src).width // 2
            cls = "shot-fig wide" if natural > 760 else "shot-fig"
            style = f' style="max-width:{natural}px"' if natural <= 760 else ""
            label = '<span class="shot">Screenshot</span>'
        else:
            cls = "hero" if "01-hero" in src else "wide"
            label = ""
        return (f'<figure class="{cls}"{style}><img {attrs.strip().rstrip("/").strip()} loading="lazy">'
                f'<figcaption>{label}{caption}</figcaption></figure>')

    body = re.sub(r"<p><img (.*?)\s*/?>\s*<em>(.*?)</em></p>", figure, body, flags=re.S)
    body = re.sub(r"(<hr\s*/?>\s*)<p><em>(.*?)</em></p>", r'\1<p class="footnote"><em>\2</em></p>', body, flags=re.S)

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="What a FalkorDB graph of Delta Lake's public history reveals about knowledge risk when a maintainer leaves, the measurement mistake behind the first headline, and how handover suggestions are built from evidence.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{FONTS}">
<style>{CSS}</style>
</head>
<body>
<main>
<p class="kicker">Graph Hacks · Company Brain</p>
<h1>{html.escape(title)}</h1>
{body}
</main>
</body>
</html>
"""
    PREVIEW.write_text(page, encoding="utf-8")
    print(f"wrote {PREVIEW} ({len(page) // 1024} KB), figures: {page.count('<figure')}")


if __name__ == "__main__":
    build()
