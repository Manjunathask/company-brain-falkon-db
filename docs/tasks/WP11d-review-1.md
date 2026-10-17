<review>
Reviewer (Claude Code) checked WP11d at 1280 x 765 (the developer's window). Accepted: Ask fits (first starter chip at
383 px, composer 615-764 px, evidence placeholder 140 px, anonymous-id note shown); a clicked question and its result
appear on screen right under it; the Leave gap is gone (57 px between "What is a bus factor?" and "Choose a
maintainer"); the departure graph is readable (person centre, components with risk borders, decision, remaining expert).
Five small fixes remain.
</review>

<fixes>
1. Chip routing. Starter chips now always run their tool directly (`if (item.tool) ... runToolSuggestion`). Only do that
   when chat is disabled. With chat enabled, a chip in the Ask view sends its question to the agent (written answer,
   evidence graph, follow-up chips). On the Leave landing, the departure chip opens the simulator as now; the other chips
   switch to Ask and send the question to the agent when chat is enabled (tool table when disabled).
2. Know chat availability before the first question: GET /api/health gains `chatEnabled` (true when the configured
   provider can run: anthropic with ANTHROPIC_API_KEY set, or scripted). The UI reads it at load and shows the
   chat-disabled notice up front when false. Test both values.
3. The readable tool table header shows the raw tool name ("WHY_NOT"). Use the plain-English label from TOOL_LABELS
   (exposed via /api/tools `label`), e.g. "Traced why a rejected decision was replaced".
4. Departure focus graph says "showing 13 of 19 nodes". When the focus graph has no more nodes than the cap, draw all of
   them; place nodes that are not connected to the person (e.g. cut-off people who were not direct collaborators) on the
   outer ring. Only show "showing N of M" when something was actually left out.
5. Leave hero: make the headline number the page heading. H1: "<busFactorOne> of <componentsReported> active code
   areas in Delta Lake have a bus factor of 1", then one muted line "One person wrote at least half of their commits in
   the last 12 months." with the "What is a bus factor?" link; drop the separate "See what depends on one person." heading
   and its paragraph (keep the eyebrow if you like). Goal: at 1280 x 765 the person search input is fully inside the first
   screen; keep the mobile first screen as it is.
</fixes>

<verification_loop>
pytest and node checks must pass.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary.
</compact_output_contract>
