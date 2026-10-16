- Claude schemas now expose question parameters only; full tool defaults remain available to the CLI and direct API.
- Added an opt-in `scripts/smoke_live.py`; it skips without `ANTHROPIC_API_KEY`. I did not run a live LLM call.
- Confirmed the departure focus graph uses a person-rooted breadth-first layout and full evidence uses cose; added regression coverage.
- Added no-cache headers for the page and static assets.

**Pytest:** 57 passed. No commit made.

**Optional parameters per Claude tool**

| Tool | Count | Tool | Count |
|---|---:|---|---:|
| bus_factor | 0 | bus_factor_component | 0 |
| departure_impact | 1 | departure_files | 1 |
| orphaned_decisions | 1 | decision_share | 1 |
| successor | 0 | simulate_departure | 0 |
| bridges | 0 | groups | 0 |
| decision_trace | 0 | why_not | 0 |
| drift | 1 | declared_vs_actual | 0 |
| find_entity | 1 | remember_correction | 0 |
| **Total** | **6** |  |  |