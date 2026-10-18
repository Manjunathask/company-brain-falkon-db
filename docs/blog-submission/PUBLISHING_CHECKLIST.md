# Publishing checklist

## Before you publish

- [ ] Read `ARTICLE.md` once, out loud if you can. It is written in your voice, and the "How it was built, and by
      whom" section describes your decisions; change anything that doesn't sound like you.
- [ ] Confirm the line about planning with Claude before the hackathon (see FACT_CHECK.md, item 1).
- [ ] Decide whether to keep the date note in the footer. Counts tied to the 12-month window move slightly each day.
- [ ] Open `PREVIEW.html` in a browser (double-click works; the images use relative paths) to see the intended layout.

## Moving the article to a blogging platform

1. **Title:** "If a maintainer left tomorrow, who would know their code? I asked a graph"
2. **Subtitle / standfirst:** the italic paragraph under the title.
3. **Cover image:** `assets/01-hero-knowledge-concentration.png` (3200 × 1680, 1.9:1). If the platform crops covers
   to 2:1 or 16:9, check that the "25 of 69" text and the ring both stay inside the frame.
4. **Body:** paste the Markdown from the first `##` heading onwards. Leave out the `# title` line and the hero image
   if the platform already shows a title and cover.
5. **Images:** upload each image in `assets/` and `assets/screenshots/` (PNG, not SVG; not the `originals/`
   folder). Then replace each relative path, for example `assets/03-architecture.png`, with the hosted URL the
   platform gives you. If the platform's editor accepts Markdown, a find-and-replace on `assets/` works once you know
   its URL pattern. Keep the alt text inside `![...]`; VISUAL_ASSETS.md has shorter versions if there is a length limit.
6. **Captions:** each image is followed by an italic line; that line is the caption. Platforms with a caption field
   (for example, under an uploaded image) can take it there instead.
7. **Code blocks:** the three Cypher blocks are tagged `cypher`. If the platform has no Cypher highlighting, plain
   text is fine. Check that `->` and `>=` show as typed, not as arrows (some code fonts merge them).
8. **Links:** all 12 external links returned HTTP 200 on 18 Oct 2026. Check them again after pasting, especially the
   GitHub links to `queries/` files.

## After pasting

- [ ] Preview on a phone. The diagrams are designed for a 700–800 px column; on a phone readers need to tap images to
      zoom. Make sure tapping opens the full image.
- [ ] Check that no caption has ended up separated from its image.
- [ ] Check that the quoted departure sentence still shows as a block quote.
- [ ] Check heading levels: one title, `##` sections, and one `###` ("How it was built, and by whom").

## Submitting it for the hackathon

- [ ] Publish publicly, then add the article URL wherever the hackathon submission asks for the blog post. Check the
      [hackathon page](https://www.wemakedevs.org/hackathons/falkordb) for the blog-prize instructions; this checklist
      doesn't assume any.
- [ ] Link the article from the repository README (and the README from the article; the footer already does).
- [ ] Submissions close on **18 Oct 2026, 11:59 PM IST**.

## Suggested metadata

**SEO description (153 characters):**
What does a project lose when a maintainer leaves? A FalkorDB graph of Delta Lake's public history, a measurement
mistake, and evidence-backed handovers.

**Tags:** FalkorDB, graph database, knowledge graph, Cypher, open source, bus factor, Delta Lake, AI agents,
developer tools, hackathon
