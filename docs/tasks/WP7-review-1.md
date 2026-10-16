<review>
Reviewer (Claude Code) feedback on WP7 before the first live run. The adapter call shape and memory look right.
</review>

<fixes>
1. Token waste (high). loop.py sends `{"rows": rows, "graph": result["graph"]}` as every tool_result. The evidence
   graph is for the UI only (departure_impact + departure_files alone are ~113 nodes / 286 edges) and is re-sent on
   every later turn. Send the model only what it reasons over: {"tool", "row_count", "rows": first 40 rows,
   "truncated": n_more (only when > 0)}. Keep the full rows and graph in AgentAnswer for the UI. Make 40 a named
   constant. Add a test that a tool_result never contains the graph and is capped.
2. Also cap long string fields in rows (e.g. lists of example paths) so one row cannot blow up the context: lists
   longer than 10 -> first 10 + count. Keep it in one small helper with a docstring.
3. The first user message is json.dumps of a dict. Make it readable text instead: "Today is <date>.", then a
   "What you remember about this user:" section (only when recall has content), then "Question: <text>". Keep the
   static system prompt unchanged so it stays cacheable.
</fixes>

<verification_loop>
pytest must pass. Re-run the scripted CLI and show the size in characters of each tool_result sent to the LLM.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; the tool_result sizes.
</compact_output_contract>
