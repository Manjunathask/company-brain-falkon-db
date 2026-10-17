<review>
Reviewer (Claude Code): the wider evidence column works (panel 496 px, count on one line, buttons on one row), but the
graph disappeared: at 1280 x 800 the Cytoscape canvas has height 0. Computed chain: canvas 0 px <- div 0 px <-
div.graph-canvas 2 px (flex: 0 1 auto, min-height auto) <- section#leave-evidence.evidence (display flex, sticky,
768 px). The flex column shrinks .graph-canvas to 2 px because the long "Evidence as text" list takes the space.
</review>

<fixes>
1. In web/style.css: `.evidence .graph-canvas { flex: 0 0 auto; height: clamp(320px, calc(100vh - 240px), 640px);
   min-height: 320px; }` (or equivalent), and make the "Evidence as text" block the part that scrolls inside the sticky
   panel (`flex: 1 1 auto; min-height: 0; overflow: auto;`), with the selected-node details kept compact. Apply to both
   the Leave and Ask evidence panels. Below 1024 px keep the canvas at a fixed 340 px.
2. Add a regression test that reads style.css and asserts the graph canvas rule has a non-shrinking flex basis and a
   min-height (string check is fine), so this cannot silently return.
</fixes>

<verification_loop>
pytest and node checks must pass.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary.
</compact_output_contract>
