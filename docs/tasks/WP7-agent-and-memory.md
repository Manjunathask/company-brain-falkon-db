<task>
You are implementing work package WP7 of "Bus Factor" (Graph Hacks, FalkorDB). Read AGENTS.md,
docs/PLAN.md (Memory section and query 13), docs/PROGRESS.md and docs/QUERIES.md. WP6 built
src/busfactor/tools.py: every tool returns {tool, params, cypher, rows, graph}. FalkorDB is reachable.

Scope: the agent loop behind a small swappable LLM interface, and the per-user memory graph (Track 02).
Hard rule 1: the agent may only state facts that came from tool results (Cypher or FalkorDB algorithms).
No vector store, no free-text answers without a tool call.

Build:
1. src/busfactor/agent/llm.py: a tiny interface the loop depends on:
   class LLM(Protocol): def step(self, system: str, messages: list, tools: list[dict]) -> Step
   Step = {stop: 'tool_use'|'end'|'refusal'|'max_tokens', text: str, tool_calls: [{id, name, input}],
   raw_assistant_content: <provider-native content to append back to history unchanged>}.
   The loop owns the history format through two helpers on the LLM: assistant_message(step) and
   tool_results_message(results). Two implementations:
   a) AnthropicLLM (official `anthropic` SDK, already installed: 1.15.0; read its source under
      .venv/Lib/site-packages/anthropic for exact names, do not guess):
      - model from env AGENT_MODEL, default "claude-opus-5-5"; effort from env AGENT_EFFORT, default
        "medium", sent as output_config={"effort": ...}; do not send `thinking` (adaptive is the default on
        this model; "disabled" and budget_tokens are rejected with 400); max_tokens 16000; non-streaming.
      - tools: name, description (from the tool docstring), input_schema with additionalProperties: false
        and required, and "strict": True. Keep the tool list in a fixed order.
      - tool_choice must stay auto (forcing "any"/"tool" returns 400 on this model).
      - prompt caching: system prompt as a list with one text block carrying
        cache_control {"type": "ephemeral"}; the system text must be static (no timestamps or user names in
        it; put per-request context such as "today" and memory recall in the first user message instead).
      - refusals: use client.beta.messages.create with betas=["server-side-fallback-2026-07-01"] and
        fallbacks="default"; still check stop_reason == "refusal" before reading content and return
        Step(stop='refusal'). If the SDK rejects these parameters, report it rather than working around it.
      - append the full response.content to history (never just the text); history is append-only.
      - parallel tool calls: return all tool_result blocks in ONE user message; a failed tool returns a
        tool_result with is_error True and the error text.
   b) ScriptedLLM for tests: replays a fixed list of Steps (tool calls then a final text) so the loop,
      memory and evidence collection are tested without network or keys.
   Provider chosen by env AGENT_PROVIDER (anthropic | scripted). Leave a clear seam for an OpenAI
   adapter but do not write one.
2. src/busfactor/agent/loop.py: ask(question, user, session_id, llm) -> AgentAnswer:
   - before the first LLM call: recall memory for the user (see 3) and include it, plus today's date, in the
     first user message;
   - loop: call llm.step; run each tool call through tools.py (validate inputs against the tool schema
     first; unknown tool or bad input -> is_error result); stop at 'end', 'refusal', 'max_tokens' or after
     8 tool rounds (then ask the model for a final answer once without tools);
   - AgentAnswer = {answer, tool_calls: [{tool, params, cypher, row_count, ms}], graph (merged evidence
     subgraph of all tool results, de-duplicated by node id / edge source+type+target), entities (graph keys
     touched), stop_reason, usage}.
   - system prompt (static, in src/busfactor/agent/prompt.py): who the agent is (company brain over the
     delta-io/delta graph), that every claim must come from a tool result and name its evidence (counts,
     people, files, PR numbers), how to read confidence on IMPLEMENTS/PARTICIPATED_IN, to use find_entity
     when a name is ambiguous, to prefer simulate_departure + departure_impact + departure_files +
     orphaned_decisions + successor for "what if X leaves", and to say plainly when the graph has no evidence.
     Keep it short and specific; no ALL-CAPS rules.
3. Memory graph per user, `mem_<login>` (PLAN.md query 13), in new query files numbered after WP6's last
   query (WP6 used 13 for find_entity, so use 14, 14b, 14c, 14d):
   14_mem_record_episode   MERGE Session; CREATE Question {text, ts, answer, tools}; ABOUT -> Entity {key}
   14b_mem_store_correction  Correction {text, ts, source} -CORRECTS-> Entity
   14c_mem_recall          for a list of entity keys (or the user's last 5 questions when no keys yet):
                           lastAsked, earlier questions, corrections
   14d_changed_since       runs on the `delta` graph: for an entity key (person:<login>,
                           component:<name>, module:<name>, decision:<slug>) count and list commits/PRs
                           since a timestamp
   Entity keys use the prefixes above; tools.py results already carry the raw keys - map them in one place.
   src/busfactor/agent/memory.py joins the two graphs in Python by Entity.key (Cypher cannot cross graphs).
   After each answer, record the episode. A user correction ("actually X still owns Y") is stored through
   a `remember_correction` tool the LLM can call, and recalled corrections must be shown in the first user
   message of later sessions. Corrections never change the `delta` graph.
4. CLI: `python -m busfactor.agent ask "<question>" --user <login> [--session <id>]` prints the answer, the
   tool trail (tool, params, rows, ms) and the evidence graph size; `python -m busfactor.agent memory
   --user <login>` prints what the memory graph holds.
5. Tests: loop with ScriptedLLM (tool call -> tool result -> answer; parallel calls -> one tool_result
   message; bad input -> is_error; round limit); memory record/recall/correction on a throwaway mem graph;
   14d on the fixture graph; the merged evidence graph de-duplicates. Integration tests only touch
   bf_test / mem_test_* graphs and clean up.
6. README: an "Agent" section (how to run, env vars AGENT_PROVIDER/AGENT_MODEL/AGENT_EFFORT,
   ANTHROPIC_API_KEY) and a "Memory (Track 02)" section in a few sentences. Append to docs/PROGRESS.md.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/, or data/delta. Do
not run git commit. Never print or log API keys. Do not make live LLM calls; the reviewer runs those.
</action_safety>

<verification_loop>
pytest must pass including integration tests. Run the CLI once with AGENT_PROVIDER=scripted and a scripted
"what if huan233usc leaves" run that calls departure_impact and departure_files, and include the output.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; scripted CLI output; the exact SDK call shape you used (parameter names) and
where in the installed SDK you confirmed them; decisions for the reviewer; anything uncertain.
</compact_output_contract>
