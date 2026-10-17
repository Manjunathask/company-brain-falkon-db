# Three-minute demo script

This walkthrough follows the current two-tab UI against the live `delta` graph. The result values below were read with `.venv/Scripts/python` from the local API on **2026-10-17**; they can change when the graph is refreshed.

## Before recording

- Start the local app with an Anthropic API key configured on the server. Confirm `/api/health` reports chat enabled by clicking a starter question during a rehearsal.
- Open `http://127.0.0.1:8000` in a fresh browser profile so earlier test questions do not appear in visitor memory.
- Use a window about **1280 × 765** or larger so the evidence graph stays beside the results.
- Have the local Delta clone and the local development environment ready only if showing refresh; that section is for local development, not the Docker image.

## Walkthrough (about 3 minutes)

**0:00–0:20 — Start with the scale.** The page opens on **What if someone leaves?** Point to the large page heading: its live value comes from `/api/summary` and says **42 of 87 active code areas in Delta Lake have a bus factor of 1**. Point to **What is a bus factor?** and explain that it means one person wrote at least half of an area's qualifying commits in the last 12 months; it does not mean nobody else contributed.

**0:20–0:55 — Pick a maintainer.** Under **Choose a maintainer**, click the search field. The picker lists the top 10 by recent commits. Type `m`; use **↓** to highlight **Murali Ramanujam (@murali-db)**, then press **Enter**. Read the one-sentence result: “If Murali Ramanujam left: 5 code areas would have no other active contributor with at least 2 recent commits, 11 would rely on one remaining person, 43 current files would have no other recent editor, and 3 people would lose their link to the main collaboration network.” Point out the counted sections: **Areas with no expert left · 5**, **Areas relying on one person · 11**, **Decisions they carry · 1**, **People cut off from the main network · 3**, and **Files only they edited · 43** (the last section starts collapsed). In an exposed area, click **Show successors** and show the suggestion that appears. The **Departure evidence** graph sits beside the results, with Murali in the centre and connected people, areas, and decision evidence around them. Click **Ask about this** on one area to show how a result can seed an Ask question.

**0:55–1:15 — Compare another person.** Click the maintainer search again, select its current text, type `scottsand-db`, then use **↓** and **Enter** to choose Scott Sandre. Point to the decision section: **Catalog-Managed Tables**, with **43 of 88 PRs** opened by Scott.

**1:15–2:00 — Ask and inspect the evidence.** Click **Ask**. Click a starter question chip; with a server key, it goes to the agent and the answer appears in the chat. Then click the composer, type `Why was`, press **Tab** to accept the visible completion **Why was Managed Commits rejected, and what replaced it?**, and press **Enter** to send. Read the answer in place. Expand **How I know** to show the plain-English graph tool labels, returned rows and parameters; expand **Cypher query** to show the query text (and **Copy query**). Point to the **Answer evidence** graph beside the chat. The answer's **Keep exploring** follow-up chips are built from successful graph-tool rows, so click one to ask about another returned entity.

**2:00–2:35 — Show visitor memory (Track 02).** Reload in the same browser profile, click **Ask**, and show **Welcome back. Last time you asked …**. Open an incognito window at the same app, click **Ask**, and point to the note that this browser keeps an anonymous id: incognito creates a new visitor with no prior history, so there is no welcome-back history to show yet. Point out **Start over** below the composer; it clears this browser's visitor history and starts a fresh anonymous identity. Each visitor's `mem_v_<id>` graph stores that visitor's episodes and corrections. The shared `mem_team` graph stores sourced observations written by repository refreshes, separate from any one visitor's history.

**2:35–3:00 — Refresh and team memory (local development only).** In a terminal at the repo root, with the Delta clone and `GITHUB_TOKEN` configured, run `.venv/Scripts/python -m busfactor.refresh`. Return to the landing page and point to the refresh line that reports recent repo changes: it displays **Last refresh (date): …** when a refresh recorded new commits or PRs. A refresh with no new commits or PRs does not produce that line. This local command pulls the Delta clone and refreshes GitHub PR activity; it is not part of the Docker-only recording path.

## No API key

The landing page and maintainer departure view still work. On **Ask**, the named starter chips call their corresponding graph tools directly and show the result in readable tables; they do not invoke the agent. A typed free-form question cannot get an agent answer, and the page explains that chat needs an Anthropic API key on the server.

## Expected values as of 2026-10-17

Live values from `/api/summary` and `/api/departure/{login}` using `.venv/Scripts/python`:

| Check | Expected value |
|---|---|
| Landing headline | **42 of 87** active code areas have bus factor 1 |
| `murali-db` | Sentence: **5** areas with no other active contributor, **11** relying on one, **43** current files, **3** people cut off. Decision share: **Enforce Vacuum Protocol Check, 1 of 3 PRs**. Top successor: **ni-mi** for `iceberg/serverSidePlanning` (**3/9** shared files). |
| `scottsand-db` | Sentence: **2** areas with no other active contributor, **6** relying on one, **26** current files, **0** people cut off. Decision share: **Catalog-Managed Tables, 43 of 88 PRs**. Top successor: **harperjiang** for `kernel/kernel-api/snapshot` (**2/2** shared files). |

Server timing from the 2026-10-17 log: graph tools took about **0.3 s**; most of a **10–20 s** answer is model time.
