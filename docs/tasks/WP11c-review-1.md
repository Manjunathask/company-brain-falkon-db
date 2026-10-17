<review>
Reviewer (Claude Code) re-checked WP11c in the browser. Accepted: two columns at 1280 px with a sticky evidence panel
(the canvas stays visible while scrolling to the summary), mobile first screen (picker at 509-562 px, first starter at
665 px on a 375 x 812 screen), readable source (max line 122), follow-ups, copy, refresh line, timings. One small
layout fix remains. Only web/style.css and, if needed, web/index.html.
</review>

<fixes>
1. The evidence column is too narrow at 1280 px: it is about 398 px wide, the canvas is 345 x 278, and the header text
   "47 nodes · 84 links · showing 47 of 49 nodes" wraps into four lines beside "Departure evidence" and the Fit/Reset/+/−
   buttons. Give the evidence column about 44% of the shell at >= 1024 px (content column min 520 px), make the canvas
   height `clamp(320px, calc(100vh - 240px), 640px)`, put the count on its own line under the title in a smaller muted
   font, and keep the four buttons on one row (compact icon-style buttons with aria-labels and titles).
2. Keep everything else unchanged.
</fixes>

<verification_loop>
pytest and node checks must pass.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary.
</compact_output_contract>
