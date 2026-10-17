1. **Verdict**

Approve the direction, but reduce the scope substantially for Saturday. The strongest demo is a newcomer choosing a maintainer, understanding the departure impact, inspecting its evidence, and asking a relevant follow-up; a new overview dashboard, streaming transport, identity lifecycle, and ten-module rewrite together put that demo at risk.

2. **What I would change, cut or reorder**

- **Make departure the primary landing action.** Use a short introduction, the populated people search, and three starter questions. Defer the four-card Overview dashboard: it adds queries, loading states, and explanations before improving the headline demo.
- **Use accurate, modest labels.** “One person accounts for at least half the qualifying commit count” is different from “only one expert.” Bus factor 1 can coexist with several contributors ([05b_bus_factor_component.cypher:15](../../queries/05b_bus_factor_component.cypher:15)). Likewise, decision share measures implementing PR authorship, not exclusive knowledge ([07b_decision_share.cypher:1](../../queries/07b_decision_share.cypher:1)).
- **Keep suggestions and follow-ups; cut ghost text, rotating placeholders, and `@` completion.** Visible, complete questions deliver the requested newcomer value with much less keyboard and layout complexity. The existing “this maintainer” suggestion lacks a named subject ([index.html:30](../../web/index.html:30)).
- **Use truthful loading feedback before SSE.** Show the submitted question immediately, a busy state, and retryable errors. Currently the question only appears after success ([app.js:111](../../web/app.js:111)).
- **Prioritize evidence selection over fancy layouts.** Keep complete paths, identify the departing person, shorten labels, and explain omitted evidence. “Decisions as a side cluster” and fixed semantic rings require more than simply selecting `concentric`.
- **Make successor selection on demand.** Choosing an exposed area can invoke the existing successor tool; avoid querying every area automatically. The current endpoint deliberately chooses one area ([app.py:232](../../src/busfactor/api/app.py:232)).
- **Remove optional GitHub personalisation for now.** It reintroduces ambiguity about identity and authentication without helping the demo.
- **Do not hard-code “most active” to Murali.** Either resolve the graph-ranked leader or label the action “Explore Murali’s departure.” Test prefix ranking against actual counts rather than requiring a predetermined winner.

3. **Anything missing for a newcomer or judge**

- A visible explanation: **“This estimates knowledge concentration from public repository activity; it does not measure everything a person knows.”**
- Distinguish **two years of ingested data** from the tools’ default **365-day activity window**, minimum two commits, and confidence settings ([tools.py:12](../../src/busfactor/tools.py:12)). Describe exclusions per metric rather than implying those records are absent from the entire graph.
- Explain “cut off” as a change in the modeled collaboration network, not people losing actual contact.
- Show snapshot freshness and link to source PRs/RFCs. A Cypher link explains computation; a source link lets judges inspect evidence.
- Provide no-results, unknown-person, graph-unavailable, failed-answer, and empty-evidence states. On mobile, put the explanation and next action before the graph.
- Keep a clear **“Try without AI”** route. The tools already work independently of chat ([app.py:210](../../src/busfactor/api/app.py:210)); key setup instructions belong to the operator, not a visiting judge.
- Define whether “same chat” means visual continuity or actual conversational context. Each `ask()` currently constructs fresh messages; `sessionId` records episodes but does not restore a conversation transcript ([loop.py:158](../../src/busfactor/agent/loop.py:158), [loop.py:248](../../src/busfactor/agent/loop.py:248)). Fully specified follow-up questions are therefore essential.

4. **Technical risks grounded in the code**

| Area | Finding and recommendation |
|---|---|
| **SSE** | The provider blocks with `stream=False`, and tool calls run concurrently through `ThreadPoolExecutor`; `list(pool.map(...))` waits for the batch ([llm.py:36](../../src/busfactor/agent/llm.py:36), [loop.py:182](../../src/busfactor/agent/loop.py:182)). A callback needs a thread-safe event queue, call IDs, error events, disconnect handling, and guaranteed completion signaling. Tests must allow interleaved tool events. A POST stream also needs a fetch-stream client rather than simply replacing fetch with `EventSource`. Defer unless core UX is verified early. |
| **Anonymous memory** | Memory names are derived directly from caller-supplied identifiers, and the read endpoint has no ownership check ([memory.py:12](../../src/busfactor/agent/memory.py:12), [app.py:249](../../src/busfactor/api/app.py:249)). Regex validation prevents malformed names; it does not establish ownership. Use a full-entropy opaque browser credential, restrict deletion to its memory graph, handle unavailable localStorage, and bound retention. Strip UUID hyphens if retaining the proposed regex. |
| **“Forget me”** | Corrections are also copied into shared team memory ([memory.py:121](../../src/busfactor/agent/memory.py:121)). Deleting `mem_<id>` alone does not erase everything attributed to that visitor. Define deletion semantics and prevent an in-flight answer from recreating deleted history. |
| **History drawer** | `snapshot()` currently returns entity-grouped recall under the name `episodes`, not a chronological question/answer history ([memory.py:133](../../src/busfactor/agent/memory.py:133), [14c_mem_recall.cypher:15](../../queries/14c_mem_recall.cypher:15)). The drawer needs a real history query or reduced scope. |
| **Deterministic follow-ups** | Returned tool traces contain parameters and row counts, **not result rows**; rows are available inside the loop before the final return ([loop.py:207](../../src/busfactor/agent/loop.py:207), [loop.py:249](../../src/busfactor/agent/loop.py:249)). Generate follow-ups there from successful structured results. Do not extract entities from answer prose or offer “What replaced this?” without replacement evidence. Prefer fewer valid chips over invented premises. |
| **ES-module split** | The script is only 225 lines but attaches listeners immediately and shares graph state across views ([app.js:3](../../web/app.js:3), [app.js:81](../../web/app.js:81)). Extract graph and people-picker code first; defer the full split. Guard against older requests overwriting a newly selected person, and associate evidence with individual answers. |
| **CDN/markdown** | Cytoscape already depends on a CDN; its fallback cannot draw evidence ([index.html:9](../../web/index.html:9), [app.js:45](../../web/app.js:45)). Test unavailable dependencies and preserve readable text evidence. Current answers use `textContent`; markdown introduces an HTML boundary, so sanitise rendered output and keep a plain-text fallback. |
| **Combobox/accessibility** | The current picker is a submit-and-click search, with no keyboard suggestion behavior ([app.js:190](../../web/app.js:190)). Budget for focus management, active option announcement, loading/empty results, stale-response suppression, Escape, and touch. Keep Tab as normal navigation if autocomplete is cut. Also provide a readable evidence list: a canvas marked `role="img"` does not expose individual graph paths ([index.html:41](../../web/index.html:41)). |

5. **Likely root causes of the two reported bugs**

**“60 nodes · 0 edges”: likely stale or different served JavaScript—not the current departure cap.** This is a code-based hypothesis, not a browser-confirmed diagnosis.

The current departure renderer passes `data.focus_graph` directly into `showEvidence`, without `capGraph` ([app.js:188](../../web/app.js:188)). `showEvidence` draws that graph, and the count label reads its arrays before Cytoscape processing ([app.js:73](../../web/app.js:73), [app.js:42](../../web/app.js:42)). Given the stated 49-node/84-edge payload, this path should display **49/84**, even if layout subsequently fails. Edge mapping uses the expected `source`/`target` fields ([app.js:65](../../web/app.js:65)).

The exact **60** is consistent with a different path using the existing tail-slice cap, which can discard connecting nodes and remove all remaining edges ([app.js:30](../../web/app.js:30)). Inspect the browser’s actual `/app.js` response and departure request on the same origin; compare them with this checkout before changing graph algorithms. No-cache middleware already exists ([app.py:32](../../src/busfactor/api/app.py:32)).

**Missing cut-off names: likely an undiscoverable collapsed disclosure.** The renderer correctly reads `simulation.rows[0].cutOff` and appends its names inside a `<details>` element that is closed by default ([app.js:149](../../web/app.js:149)). CSS removes both the list marker and WebKit disclosure marker ([style.css:1](../../web/style.css:1)). Show the three names directly, or add an explicit chevron and count. If names remain absent after expansion, investigate served-code mismatch next.

6. **Priority order for one day**

- **Must — morning:** reproduce the served-asset discrepancy; verify graph edges and visible cut-off names; remove the login barrier; implement populated people search; add named starter questions, structured follow-ups, truthful metric explanations, and loading/error states.
- **Must — afternoon:** verify keyboard and 390 px flows, evidence tied to the selected answer/person, safe answer rendering, no-key operation, existing tests, and the fresh-volume Docker judge path. Freeze features with time left for fixes.
- **Should:** lightweight landing view, hash links, graph fit/reset and readable details, successor-by-area selection, a correctly scoped browser-history/reset feature.
- **Could:** four insight cards, SSE, ghost completion, `@` mentions, automatic prose entity chips, elaborate graph rings, and the full module split.

Review only; no files changed.