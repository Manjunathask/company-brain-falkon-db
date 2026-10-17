<review>
The developer tested the revamp in Chrome (screenshots) and the reviewer (Claude Code) reproduced the problems. Root
cause of the two layout problems: each view (#leave-view, #ask-view) is a two-column CSS grid whose left-column items sit
in separate grid rows, and the evidence panel (about 733 px tall) sits in row 1, so row 1 is stretched (measured grid
rows on #ask-view: "797px 291px 144px").
- Ask: the intro and the composer form are in row 1, while #chat-list and #ask-empty (starter chips) are pushed to
  row 2 at about 976 px on a 765 px-high window. The developer had to scroll to reach the starter questions, and after
  clicking one the question and answer were appended to #chat-list below the fold and below the composer, so it looked
  like no answer came back.
- Leave: the same stretched row 1 leaves a large empty gap between "What is a bus factor?" and "Choose a maintainer".
Other findings: with no API key, a starter chip shows the tool's raw JSON rows (unreadable for a newcomer and the
default for judges); the "Welcome back — since you last asked about bart-samwel, 0 new commits landed." banner is
uninformative; the developer did not understand how the site knows who they are; the departure focus graph is a ring of
tiny commit-SHA labels.
Touch web/** and, only for item 6, src/busfactor/api/app.py; plus tests. Not README.md or docs/PROGRESS.md.
</review>

<fixes>
1. One wrapper per column. In both views put all left-column content in a single container (one grid cell) and the
   evidence panel in the second cell (`align-self: start`, sticky as now), so no left-side gaps can come from the
   panel's height. Remove the per-item grid-row placement.
2. Ask as a proper chat column. Order: intro + starter chips (empty state) -> chat list -> composer. On desktop
   (>= 1024 px) the left column is a card of height `calc(100vh - <header+tabs>)` where the message list scrolls and the
   composer is pinned at the bottom, so the starter chips and the composer are visible without scrolling on a 765 px
   window. On send: hide the intro/empty state, append the question, scroll the newest message into view; when the
   answer lands, scroll it into view (start of the answer). Follow-up chips stay under the answer. On mobile keep one
   column with the composer after the messages and scroll the new message into view.
3. Evidence placeholder. Before an answer (Ask) or before a person is chosen (Leave), show a compact placeholder card
   (about 140 px): "The graph behind each answer appears here." with the legend hidden. Expand to the full canvas when
   evidence arrives. On #leave without a login never show a previous person's graph.
4. No-key starter chips must be readable. A chip with tool "departure" opens #leave/<login>. Other tools render a small
   table with plain column headers (e.g. successor: Successor, Shared files, Commits here; why_not: Rejected decision,
   Chosen instead, Evidence, Discussion, Who to ask; declared_vs_actual: Module, Declared owners, Most active, Owners not
   in top 3) plus the evidence graph — never raw JSON. Keep one small mapping table in app.js.
5. Memory transparency. Replace the banner text: "Welcome back. Last time you asked: “<last question>”." and add
   ", <n> new commits since then in <entity>" only when n > 0. Under the composer, next to Start over, add one muted line:
   "This browser keeps an anonymous id so the app can remember your questions on this server. Start over clears it."
6. Readable departure graph. In the focus graph (api/app.py `_focused_departure_graph` or the client cap) drop Commit and
   File nodes; keep the person, ORPHANED/AT RISK components, the remaining experts, cut-off people, decisions and the
   successor. Concentric layout by role (person centre; ring 1 components and decisions; ring 2 people). Labels at a
   readable size (>= 11 px at 1x zoom), truncated, with full text on click. Commits and files stay in "Show full
   evidence".
</fixes>

<verification_loop>
pytest and node checks must pass. Add a CSS/structure test that each view's left content is a single wrapper element
and the evidence panel is its sibling. If you can, describe the measured top of the first starter chip and of the
composer at 1280 x 765.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; anything you could not verify.
</compact_output_contract>
