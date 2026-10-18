# Visual assets

Thirteen figures appear in `ARTICLE.md`, in this order. Six are original diagrams or illustrations; seven are
screenshots of the running app. All PNGs are exported at 2× for sharp display at blog-column width.

**Kinds.** *Data illustration*: drawn from live query output. *Diagram*: hand-written SVG, every entity and count
checked against the code or the live graph. *Screenshot*: an unedited crop of a real capture. Nothing was drawn onto a
screenshot.

## Diagrams and illustration

| # | File (PNG to upload · editable SVG) | Kind | Size (px) | Placement | Purpose |
|---|---|---|---|---|---|
| 1 | `assets/01-hero-knowledge-concentration.png` · `.svg` | Data illustration | 3200 × 1680 | Top, under the standfirst | Shows knowledge concentration: 69 code areas, each joined to its most active author in the last 12 months; the 25 areas with a bus factor of 1 are orange. Generated from `assets/src/hero-data.json` (rows of `05b_bus_factor_component`, 18 Oct 2026) by `assets/src/build_visuals.py`. |
| 2 | `assets/02-knowledge-graph-explained.png` · `.svg` | Diagram | 2400 × 1800 | "The answer is spread across four places" | Teaches nodes, relationships and following a path, using seven real nodes (commit fa642d6, PR #6188, scottsand-db's review, the title-match link). |
| 3 | `assets/03-architecture.png` · `.svg` | Diagram | 2400 × 2400 | "What I built" | Actual data flow: sources, parsers, snapshot, load/link/derive, FalkorDB's separate graphs (`delta`, `mem_team`, `mem_v_<visitor>`, `whatif_*`), Python tool layer (joins memory in Python), web app, and agent. |
| 4 | `assets/04-measurement-correction.png` · `.svg` | Diagram | 2400 × 2000 | "My first headline was wrong" | Explains the method change behind 42 of 87 vs 25 of 69: the window mix-up (illustrative dots), the leaving-person threshold and the label change. Two columns, not a timeline, so it can't be read as an improvement in risk. |
| 5 | `assets/05-handover-evidence-chain.png` · `.svg` | Diagram | 2400 × 1720 | "One maintainer, one area, one handover" | The evidence behind "suggests scottsand-db": Hao Jiang's 3 PRs in `flink/inttest`, who reviewed each, the title-match decision link and the plain-sort order. |
| 6 | `assets/06-memory-changes-recommendation.png` · `.svg` | Diagram | 2400 × 1800 | "When a note changes the answer" | Keeps repository facts, an unverified (made-up) note and the derived suggestion visually separate, and shows how the note reaches the query (`$exclude`, joined in Python). |

## Screenshots (real app, captured 18 Oct 2026)

Captured with headless Microsoft Edge (Playwright) at 2× from a separate local instance of the app at the current
`main` (`24409e1`). It ran on port 8077 against the live `delta` graph, with a throwaway team-memory graph
(`BUSFACTOR_TEAM_GRAPH=mem_team_blog`) so that existing notes could not affect the "before" state. The throwaway
graph and the four visitor ids used were deleted afterwards. The originals are kept unchanged in
`assets/screenshots/originals/`; `assets/src/crop_screenshots.py` records each crop box.

| # | File | Size (px) | From original | Placement | What the reader should notice |
|---|---|---|---|---|---|
| 7 | `assets/screenshots/s1-landing-headline.png` | 1180 × 1530 | `01_landing_viewport.png` | "What I built" | The corrected headline (25 of 69), the ranked maintainer search, the starter questions. |
| 8 | `assets/screenshots/s2-departure-no-other-author.png` | 2200 × 1540 | `03b_evidence_expanded_viewport.png` | Handover section, after the quoted sentence | Three Flink areas with NO OTHER AUTHOR, each listing 5–6 active reviewers; the evidence graph with dotted review edges. |
| 9 | `assets/screenshots/s3-handover-successor.png` | 1740 × 1720 | `04_handover_before_full.png` (top) | Handover section | Suggested successor scottsand-db, the evidence table, files not yet touched, PRs to read first. Captured at 960 px wide (the app's one-column layout) so the table is readable. |
| 10 | `assets/screenshots/s4-handover-decisions-questions.png` | 1740 × 1480 | `04_handover_before_full.png` (lower part) | Handover section | "0 explicitly linked PRs · 1 title matches (keyword guesses)", the reason quoted from issue #4381, questions for Hao Jiang. |
| 11 | `assets/screenshots/s5-handover-after-note.png` | 1740 × 1490 | `05_handover_after_full.png` (top) | Memory section | The "What changed" line, the new suggestion (kaiqijinwow) and "Skipped scottsand-db … Unverified availability note". |
| 12 | `assets/screenshots/s6-agent-reads-team-note.png` | 1120 × 1724 | `08_ask_answer_top.png` (answer column) | Memory section | The chat agent reads the same shared note, calls it unverified, and says the evidence for the new suggestion is thin. |
| 13 | `assets/screenshots/s7-how-i-know-trace.png` | 1140 × 350 | `09_ask_how_i_know.png` | Memory section | The "How I know" trace: one tool call, name checks before it, timings, and the reply check flagging one name. |

The two Ask answers in screenshots 12 and 13 come from two separate runs of the same question.

## Alt text

The full alt text for every image is in `ARTICLE.md` (inside each `![...]`). Short versions for platforms that
limit alt-text length:

| # | Short alt text |
|---|---|
| 1 | Radial map: 25 of 69 Delta Lake code areas have one person behind at least half of their recent commits. |
| 2 | Seven connected nodes: a commit by harperjiang, its file and code area, PR #6188, its reviewer scottsand-db, and a title-match link to a design decision. |
| 3 | Architecture: public sources, snapshot, FalkorDB graphs, Python tool layer, web app and agent. |
| 4 | Old and corrected bus-factor calculations: 42 of 87 vs 25 of 69 on the same graph. |
| 5 | Evidence chain from Hao Jiang's three PRs to their reviewers, ending in the suggestion scottsand-db. |
| 6 | Repository facts, an unverified team note and the derived suggestion kept separate; the suggestion changes after the note. |
| 7 | Bus Factor landing view with the headline 25 of 69 and a maintainer search box. |
| 8 | Departure view for Hao Jiang: three NO OTHER AUTHOR areas with reviewers, beside an evidence graph. |
| 9 | Handover packet for flink/inttest suggesting scottsand-db, with an evidence table and PRs to read. |
| 10 | Handover packet: decision to preserve with a quoted reason, and questions for Hao Jiang. |
| 11 | Handover packet after the note: What changed line and kaiqijinwow suggested. |
| 12 | Chat agent's handover answer mentioning the unverified note. |
| 13 | How I know trace with name checks and timings. |

## Design system

- Palette (semantic, used the same way in every figure): ink `#1B1F29`, paper `#FBFAF7`, line `#DAD5CB`;
  vermillion `#D2491A` = the person leaving / risk; teal `#0E7C7B` = reviews and "follow the path"; plum `#A23B72` =
  design decisions, dashed for title-match guesses; violet `#6B4FB0` = pull requests; ochre `#B8650F` = code areas;
  amber `#B7791F` = unverified notes (dashed border); green `#23794A` = derived suggestions.
- Type: Inter (labels), JetBrains Mono (identifiers), loaded from Google Fonts when rendering.
- Layout: diagrams are 1200 px wide in SVG units with text at 15–31 px, so labels stay about 9–18 px at an 720–800 px
  column. On phones, readers need to tap to zoom.

## Rebuilding

```
python -m uv run --no-project --with playwright --with pillow python assets/src/build_visuals.py   # all SVG -> PNG (+ hero data)
python -m uv run --no-project --with pillow python assets/src/crop_screenshots.py <raw capture folder>
python -m uv run --no-project --with markdown --with pillow python assets/src/build_preview.py
```

Rendering uses the locally installed Microsoft Edge through Playwright (`channel="msedge"`). No project dependency
was added.
