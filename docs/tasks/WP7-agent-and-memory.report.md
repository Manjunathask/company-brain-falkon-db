Implemented WP7. No live LLM call was made, and I did not create a commit.

**Files changed**

- Added the agent interface, Anthropic and scripted adapters, prompt, loop, memory layer, and CLI under [src/busfactor/agent](../../src/busfactor/agent).
- Added memory queries [14_mem_record_episode.cypher](../../queries/14_mem_record_episode.cypher), [14b_mem_store_correction.cypher](../../queries/14b_mem_store_correction.cypher), [14c_mem_recall.cypher](../../queries/14c_mem_recall.cypher), and [14d_changed_since.cypher](../../queries/14d_changed_since.cypher).
- Added unit and FalkorDB integration coverage in [test_agent.py](../../tests/test_agent.py) and [test_memory_integration.py](../../tests/test_memory_integration.py).
- Updated [README.md](../../README.md), [docs/QUERIES.md](../../docs/QUERIES.md), and [docs/PROGRESS.md](../../docs/PROGRESS.md).

The memory queries record a session episode and its touched entity keys, store user corrections with provenance, and recall corrections and recent questions. The changed-since query traverses `delta` for commits and PRs after an entity’s last-asked timestamp; Python joins memory and Delta graphs by `Entity.key`.

**Verification**

`pytest`: **44 passed** in 19.57s, including the integration tests against the local FalkorDB instance. `git diff --check` reported no whitespace errors. The scripted CLI run returned:

```text
The graph tools returned the departure impact and file-risk evidence for huan233usc. Review the evidence graph and tool rows for details.
Tool trail:
- departure_impact params={"login": "huan233usc"} rows=48 ms=2127.55
- departure_files params={"login": "huan233usc"} rows=17 ms=2285.6
Evidence graph: 113 nodes, 286 edges
```

The CLI’s throwaway `mem_test_wp7` graph was removed after the run.

**Anthropic SDK call shape**

The adapter calls `client.beta.messages.create` with `model`, `max_tokens=16000`, cached-block `system`, `messages`, `tools`, `tool_choice={"type":"auto"}`, `output_config={"effort": ...}`, `stream=False`, `betas=["server-side-fallback-2026-07-01"]`, and `fallbacks="default"`. I confirmed these parameter names in the installed `.venv/Lib/site-packages/anthropic/resources/beta/messages/messages.py` at lines 122–147, and confirmed the client accepts `default_headers` at `_client.py:164–176`; `_CLIENT_LEVEL_HEADER_PARAMS` includes `anthropic-workspace-id` at `_client.py:133`.

**For the reviewer**

The SDK signatures and FalkorDB Cypher were verified locally. The Anthropic server’s acceptance of the requested model, effort, and fallback beta parameters remains unverified because live LLM calls were prohibited. `docs/tasks/WP7-agent-and-memory.md` was already modified when I started; I left it untouched.