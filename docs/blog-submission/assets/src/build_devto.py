"""Build DEVTO.md from ARTICLE.md: dev.to front matter, the hero as the cover image, and absolute image URLs.

Images point at the public GitHub repository, so docs/blog-submission/assets must be pushed to main first.
Run with any Python 3: python build_devto.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = "https://raw.githubusercontent.com/Manjunathask/company-brain-falkon-db/main/docs/blog-submission/"
DESCRIPTION = ("What does a project lose when a maintainer leaves? A FalkorDB graph of Delta Lake's public history, "
               "a measurement mistake, and evidence-backed handovers.")
TAGS = "falkordb, graphdatabase, opensource, ai"  # dev.to allows at most four lowercase alphanumeric tags


def build() -> pathlib.Path:
    text = (ROOT / "ARTICLE.md").read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", text, flags=re.M).group(1)
    body = re.sub(r"^# .+\n+", "", text, count=1, flags=re.M)

    # The hero becomes the cover image; its caption moves under the standfirst so the explanation is kept.
    hero = re.search(r"!\[[^\]]*\]\((assets/01-hero[^)]+)\)\n\*(.+?)\*\n", body)
    body = body.replace(hero.group(0), "")
    body = re.sub(r"^(\*Bus Factor turns.+?\*)\n", lambda m: f"{m.group(1)}\n\n*About the cover: {hero.group(2)}*\n",
                  body, count=1, flags=re.M)

    body = body.replace("](assets/", f"]({RAW}assets/")
    front = (f'---\ntitle: "{title}"\npublished: false\ndescription: "{DESCRIPTION}"\n'
             f"tags: {TAGS}\ncover_image: {RAW}{hero.group(1)}\n---\n\n")
    out = ROOT / "DEVTO.md"
    out.write_text(front + body.lstrip(), encoding="utf-8")
    return out


if __name__ == "__main__":
    path = build()
    text = path.read_text(encoding="utf-8")
    print(f"wrote {path} ({len(text)} chars, {text.count('raw.githubusercontent.com')} absolute image URLs)")
