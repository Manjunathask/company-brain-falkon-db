import { renderEvidence } from "./graph.js?v=11b";
import { mountPeopleCombobox } from "./people-combobox.js?v=11b";

const $ = selector => document.querySelector(selector);
const state = {
  evidence: { leave: null, ask: null },
  suggestions: [],
  toolLabels: {},
  chatEnabled: false,
  departureToken: 0,
  askToken: 0,
  sessionId: crypto.randomUUID(),
  currentLogin: "",
};

// Keep an anonymous visitor key so their memory can be recalled and deleted.
function visitor() {
  try {
    let value = localStorage.getItem("busfactor-visitor");
    if (!/^v_[0-9a-f]{32}$/.test(value || "")) {
      value = `v_${crypto.randomUUID().replaceAll("-", "")}`;
      localStorage.setItem("busfactor-visitor", value);
    }
    return value;
  } catch (_) {
    return `v_${crypto.randomUUID().replaceAll("-", "")}`;
  }
}

const visitorId = visitor();

// Decode JSON errors into a message shared by all API requests.
async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  let data = {};
  try {
    data = await response.json();
  } catch (_) {}
  if (!response.ok) {
    const error = new Error(data.detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return data;
}

// Create UI nodes with textContent so repository data is never interpreted as HTML.
const el = (tag, className = "", value = "") => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value;
  return node;
};

function setTab() {
  const ask = location.hash === "#ask";
  $("#tab-leave").classList.toggle("active", !ask);
  $("#tab-ask").classList.toggle("active", ask);
  $("#tab-leave").setAttribute("aria-selected", String(!ask));
  $("#tab-ask").setAttribute("aria-selected", String(ask));
  $("#leave-view").hidden = ask;
  $("#ask-view").hidden = !ask;
  draw(ask ? "ask" : "leave");
  if (!ask && location.hash.startsWith("#leave/")) {
    const login = decodeURIComponent(location.hash.slice(7));
    if (login !== state.currentLogin) selectPerson(login, false);
  } else if (!ask && location.hash === "#leave") {
    state.currentLogin = "";
    state.departureToken++;
    $("#departure-results").replaceChildren();
    $("#team-line").classList.add("hidden");
    evidence("leave", { nodes: [], edges: [] }, [], "departure");
  }
}

window.addEventListener("hashchange", setTab);
$("#about-button").onclick = () => {
  const popover = $("#about-popover");
  const closed = popover.classList.toggle("hidden");
  $("#about-button").setAttribute("aria-expanded", String(!closed));
};

function draw(view) {
  const saved = state.evidence[view];
  const panel = $(`#${view}-evidence`);
  if (saved && panel) {
    renderEvidence(panel, saved.graph, { roots: saved.roots, layout: saved.layout });
  }
}

function evidence(view, graph, roots = [], layout = "chat") {
  state.evidence[view] = { graph: graph || { nodes: [], edges: [] }, roots, layout };
  if ((location.hash === "#ask") === (view === "ask")) draw(view);
}

function suggestionText(item) {
  return typeof item === "string" ? item : item.question || item.label || "Explore the graph";
}

function chip(item, destination) {
  const button = el("button", "chip", suggestionText(item));
  button.type = "button";
  button.onclick = () => {
    if (item.tool) {
      if (item.tool === "departure" && (destination === "leave" || !state.chatEnabled)) {
        return selectPerson(item.params?.login);
      }
      location.hash = "#ask";
      return state.chatEnabled ? send(suggestionText(item)) : runToolSuggestion(item);
    }
    location.hash = "#ask";
    $("#question-input").value = suggestionText(item);
    grow();
    $("#question-input").focus();
    if (destination === "ask" && $("#chat-disabled").classList.contains("hidden")) {
      send(suggestionText(item));
    }
  };
  return button;
}

async function runToolSuggestion(item) {
  const chat = $("#chat-list");
  const question = suggestionText(item);
  $("#ask-welcome").classList.add("hidden");
  $("#ask-empty").classList.add("hidden");
  chat.append(
    message("You", question, "user-message"),
    message("Graph tool", "Querying the graph…", "pending-message"),
  );
  try {
    const result = await api(`/api/tools/${encodeURIComponent(item.tool)}`, {
      method: "POST",
      body: JSON.stringify({ params: item.params || {} }),
    });
    chat.lastElementChild.remove();
    const article = readableToolResult(item.tool, result.rows || [],
      state.toolLabels[item.tool] || item.label || item.tool);
    chat.append(article);
    evidence("ask", result.graph, Object.values(item.params || {}));
    article.scrollIntoView({ block: "start" });
  } catch (error) {
    chat.lastElementChild.textContent = error.message;
  }
}

async function loadLanding() {
  try {
    const data = await api("/api/summary");
    $("#headline").textContent =
      `${data.busFactorOne} of ${data.componentsReported} active code areas in Delta Lake have a bus factor of 1`;
    $("#dataset-chip").textContent =
      `${data.snapshotDate || "Snapshot date unavailable"} · ` +
      `${data.dataWindow || "two-year repository window"}`;
    $("#dataset-counts").textContent =
      `Risk settings: ${data.windowDays || 365} days, at least ` +
      `${data.minCommits || 2} commits, and ${data.minTotal || 5} area commits.`;
  } catch (_) {
    $("#headline").textContent =
      "Repository summary is temporarily unavailable. You can still choose a contributor " +
      "or explore a question.";
    $("#dataset-chip").textContent = "Repository snapshot unavailable";
    $("#dataset-counts").textContent = "Risk settings are unavailable while the summary endpoint is offline.";
  }

  try {
    const health = await api("/api/health");
    state.chatEnabled = Boolean(health.chatEnabled);
    $("#chat-disabled").classList.toggle("hidden", state.chatEnabled);
    $("#dataset-counts").textContent +=
      ` Snapshot graph: ${Number(health.nodes).toLocaleString()} records and ` +
      `${Number(health.edges).toLocaleString()} relationships.`;
  } catch (_) {
    state.chatEnabled = false;
    $("#chat-disabled").classList.remove("hidden");
    $("#dataset-counts").textContent += " Snapshot graph counts unavailable.";
  }

  try {
    const data = await api("/api/tools");
    state.toolLabels = Object.fromEntries((data.tools || []).map(tool => [tool.name, tool.label]));
  } catch (_) {}

  try {
    const data = await api("/api/suggestions");
    state.suggestions = data.suggestions || [];
    const leave = $("#leave-suggestions");
    const ask = $("#ask-suggestions");
    leave.replaceChildren();
    ask.replaceChildren();
    state.suggestions.slice(0, 3).forEach(item => leave.append(chip(item, "leave")));
    state.suggestions.slice(0, 4).forEach(item => ask.append(chip(item, "ask")));
    if (!state.suggestions.length) {
      leave.textContent = ask.textContent = "Suggested questions are temporarily unavailable.";
    }
  } catch (_) {
    $("#leave-suggestions").textContent = $("#ask-suggestions").textContent =
      "Suggested questions are temporarily unavailable.";
  }

  try {
    const data = await api("/api/team");
    const run = (data.refreshRuns || []).find(item =>
      Number(item.newCommits || 0) + Number(item.newPRs || 0) > 0,
    );
    if (!run) {
      $("#team-line").classList.add("hidden");
      return;
    }
    const date = new Date(run.ts).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
    });
    const observations = (run.observations || []).slice(0, 2);
    const commits = Number(run.newCommits || 0);
    const prs = Number(run.newPRs || 0);
    const summary =
      `Last refresh (${date}): ${commits} new commit${commits === 1 ? "" : "s"}, ` +
      `${prs} PR${prs === 1 ? "" : "s"}`;
    $("#team-line").textContent = observations.length
      ? `${summary}; ${observations.join("; ")}`
      : `${summary}.`;
    $("#team-line").classList.remove("hidden");
  } catch (_) {
    $("#team-line").classList.add("hidden");
  }
}

function countRisk(data, risk) {
  return (data.impact?.rows || []).filter(row => row.risk === risk).length;
}

async function selectPerson(login, changeHash = true) {
  if (!login) return;
  state.currentLogin = login;
  if (changeHash) location.hash = `#leave/${encodeURIComponent(login)}`;
  const token = ++state.departureToken;
  evidence("leave", { nodes: [], edges: [] }, [], "departure");
  const output = $("#departure-results");
  output.replaceChildren(el("p", "loading-state", `Looking at recent work by @${login}…`));
  try {
    const data = await api(`/api/departure/${encodeURIComponent(login)}`);
    if (token === state.departureToken) renderDeparture(data, login);
  } catch (error) {
    if (token !== state.departureToken) return;
    const text = error.status === 404
      ? `We couldn’t find @${login} in the active contributor list. Choose a suggested contributor or try another name.`
      : `Departure estimate temporarily unavailable: ${error.message}`;
    output.replaceChildren(el("div", "empty-state", text));
    evidence("leave", { nodes: [], edges: [] }, [], "departure");
  }
}

mountPeopleCombobox($("#people-picker"), {
  onSelect: person => selectPerson(person.login),
});

function disclosure(parent, title, children, open = true) {
  const details = document.createElement("details");
  details.className = "disclosure";
  details.open = open;
  details.append(el("summary", "", title));
  const body = el("div", "disclosure-body");
  if (children.length) children.forEach(child => body.append(child));
  else body.append(el("p", "muted", "No matching items in the current estimate."));
  details.append(body);
  parent.append(details);
}

function list(values) {
  const items = el("ul", "plain-list");
  values.forEach(value => items.append(el("li", "", value)));
  if (!values.length) items.append(el("li", "muted", "No examples were returned."));
  return items;
}

function askAction(parent, question) {
  const button = el("button", "text-button", "Ask about this");
  button.type = "button";
  button.onclick = () => {
    location.hash = "#ask";
    $("#question-input").value = question;
    grow();
    $("#question-input").focus();
  };
  parent.append(button);
}

const GITHUB = "https://github.com/delta-io/delta";
const LINK_KIND = {
  "issue-ref": "explicit: issue reference",
  "rfc-doc": "explicit: RFC document",
  "title-keyword": "title match (keyword guess)",
};

function externalLink(href, text) {
  const link = el("a", "source-link", text);
  link.href = href;
  link.target = "_blank";
  link.rel = "noopener";
  return link;
}

// Where a decision card's claims come from: the RFC, its tracking issue, and the PRs with how each was linked.
function sourceLinks(row) {
  const box = el("div", "source-links");
  if (row.rfcPath) box.append(externalLink(`${GITHUB}/blob/master/${row.rfcPath}`, "RFC document"));
  if (row.issue) box.append(externalLink(`${GITHUB}/issues/${row.issue}`, `Tracking issue #${row.issue}`));
  (row.prs || []).forEach(pr => {
    const item = el("span", `source-pr ${pr.confidence === "high" ? "explicit" : "title-match"}`);
    item.append(externalLink(`${GITHUB}/pull/${pr.number}`, `PR #${pr.number}`),
      el("small", "", LINK_KIND[pr.via] || (pr.confidence === "high" ? "explicit" : "title match")));
    item.title = pr.title || "";
    box.append(item);
  });
  return box;
}

function areaCard(row, login, name) {
  const card = el("article", "detail-item");
  const heading = el("h4", "", row.component);
  const badgeClass = row.risk === "NO OTHER AUTHOR" ? "orphan" : "at-risk";
  heading.append(" ", el("span", `risk-badge ${badgeClass}`, row.risk));

  const display = `${name} (@${login})`;
  const commits = Number(row.theirCommits || 0);
  const others = Number(row.expertsLeft || 0);
  const contribution = `${display} wrote ${commits} recent commit${commits === 1 ? "" : "s"} here`;
  const detail = others
    ? `${others} other recent author${others === 1 ? "" : "s"} ` +
      `remain${others === 1 ? "s" : ""}: ${(row.remaining || []).join(", ")}.`
    : "No other recent author with at least 2 commits here.";
  card.append(heading, el("p", "", `${contribution}. ${detail}`));
  const reviewerCount = Number(row.reviewerCount || 0);
  const reviewerNames = (row.reviewerPRs || []).length
    ? row.reviewerPRs.map(item => `${item.login} (${item.prs} PR${Number(item.prs) === 1 ? "" : "s"})`)
    : (row.reviewers || []);
  const reviewText = reviewerCount
    ? `Reviewed by: ${reviewerNames.join(", ")}` +
      `${reviewerCount > reviewerNames.length ? ` and ${reviewerCount - reviewerNames.length} more` : ""}` +
      ` · ${reviewerCount} active reviewer${reviewerCount === 1 ? "" : "s"}`
    : (others === 0
      ? "Nobody else authored or reviewed this code in the last 12 months at the stated thresholds."
      : "No other active reviewers in the last 12 months.");
  card.append(el("p", "muted", reviewText));

  const actions = el("div", "detail-actions");
  const draft = el("button", "", "Draft handover");
  draft.type = "button";
  draft.onclick = () => openHandover(card, login, name, row.component);
  actions.append(draft);
  const successors = el("button", "secondary", "Show successors");
  successors.type = "button";
  successors.onclick = async () => {
    successors.disabled = true;
    successors.textContent = "Checking…";
    try {
      const data = await api("/api/tools/successor", {
        method: "POST",
        body: JSON.stringify({ params: { login, component: row.component } }),
      });
      const text = data.rows?.length
        ? `Suggested successor: ${data.rows.map(item =>
          `${item.successor} (${item.sharedFiles}/${item.outOf} shared files)`,
        ).join(", ")}`
        : "No successor found for this area.";
      successors.replaceWith(el("p", "successor-result", text));
    } catch (_) {
      successors.disabled = false;
      successors.textContent = "Retry successors";
    }
  };
  actions.append(successors);
  askAction(actions, `Who could take over ${row.component} if ${name} left?`);
  card.append(actions);
  return card;
}

// Handover packet for one area: a sourced successor, PRs to read, decisions to keep and questions to ask.
async function openHandover(card, login, name, component) {
  document.querySelectorAll(".handover-panel").forEach(panel => panel.remove());
  const panel = el("section", "handover-panel");
  panel.setAttribute("aria-live", "polite");
  panel.append(el("p", "muted", `Drafting the handover for ${component}…`));
  card.after(panel);
  panel.scrollIntoView({ block: "start" });
  try {
    const packet = await api(`/api/handover/${encodeURIComponent(login)}?component=${encodeURIComponent(component)}`);
    renderHandover(panel, packet, () => openHandover(card, login, name, component));
    evidence("leave", packet.graph, [login]);
  } catch (error) {
    panel.replaceChildren(el("p", "muted", `Handover unavailable: ${error.message}`));
  }
}

async function noteAvailability(login, status, reason) {
  return api("/api/availability", {
    method: "POST",
    body: JSON.stringify({ login, status, reason, visitor: visitorId }),
  });
}

function unavailableForm(login, redraw) {
  const box = el("span", "unavailable-box");
  const open = el("button", "secondary small", "Mark unavailable");
  open.type = "button";
  open.onclick = () => {
    const form = el("form", "unavailable-form");
    const input = el("input");
    input.placeholder = "Reason, e.g. on leave until January";
    input.setAttribute("aria-label", `Why ${login} is unavailable`);
    const save = el("button", "small", "Save note");
    form.append(input, save);
    form.onsubmit = async event => {
      event.preventDefault();
      save.disabled = true;
      await noteAvailability(login, "unavailable", input.value || "no reason given");
      redraw();
    };
    box.replaceChildren(form);
    input.focus();
  };
  box.append(open);
  return box;
}

function handoverSection(title) {
  const section = el("div", "handover-section");
  section.append(el("h4", "", title));
  return section;
}

function changedLine(changed) {
  const text = changed.same
    ? `Same suggestion as the packet saved on ${changed.previousDate}.`
    : `The packet saved on ${changed.previousDate} suggested ${changed.previousCandidate}; ` +
      `now ${changed.candidate || "nobody"}.`;
  return el("p", "handover-changed",
    `What changed: ${text}${changed.reasons.length ? ` Why: ${changed.reasons.join("; ")}.` : ""}`);
}

function successorSection(packet, redraw) {
  const section = handoverSection("Suggested successor");
  if (packet.successor) {
    const why = el("p", "");
    why.append(el("strong", "", packet.successor.login), `: ${packet.successor.why}`);
    section.append(why);
    const table = document.createElement("table");
    table.className = "tool-table";
    const head = document.createElement("tr");
    ["Candidate", `Reviewed ${packet.login}'s PRs here`, "Shared files", "Own commits here", "PRs reviewed here",
      "Shared decisions", ""].forEach(label => head.append(el("th", "", label)));
    table.append(head);
    packet.candidates.forEach(row => {
      const tr = document.createElement("tr");
      [row.login, `${row.reviewedTheirPRs} of ${row.theirPRCount}`, `${row.sharedFiles} of ${row.outOf}`,
        row.areaCommits, row.areaReviews, cellText(row.sharedDecisions)]
        .forEach(value => tr.append(el("td", "", String(value))));
      const action = el("td");
      action.append(unavailableForm(row.login, redraw));
      tr.append(action);
      table.append(tr);
    });
    section.append(table);
    if (packet.successor.toLearn?.length) {
      section.append(el("p", "muted",
        `Not touched by ${packet.successor.login} yet: ${packet.successor.toLearn.join(", ")}`));
    }
  } else {
    section.append(el("p", "muted", `No active author or reviewer of this area was found besides ${packet.name}.`));
  }
  packet.skipped.forEach(item => {
    const line = el("p", "handover-skipped",
      `Skipped ${item.login}: marked unavailable${item.reason ? ` (${item.reason})` : ""} · ${item.label}, ` +
      `${item.source || "unknown source"}. `);
    const undo = el("button", "secondary small", "Mark available");
    undo.type = "button";
    undo.onclick = async () => {
      undo.disabled = true;
      await noteAvailability(item.login, "available", "");
      redraw();
    };
    line.append(undo);
    section.append(line);
  });
  return section;
}

function readingSection(packet) {
  const section = handoverSection("Read these first");
  const list = el("ul", "handover-list");
  packet.read.forEach(pr => {
    const item = el("li");
    item.append(externalLink(`${GITHUB}/pull/${pr.number}`, `#${pr.number} ${pr.title}`),
      el("small", "", ` · ${pr.filesHere} file${pr.filesHere === 1 ? "" : "s"} here` +
        `${pr.reviewers?.length ? ` · reviewed by ${pr.reviewers.join(", ")}` : ""}`));
    (pr.decisions || []).forEach(decision => item.append(el("span",
      `decision-chip ${decision.confidence === "high" ? "explicit" : "title-match"}`,
      `${decision.title} · ${decision.confidence === "high" ? "explicit" : "title match"}`)));
    list.append(item);
  });
  section.append(packet.read.length ? list : el("p", "muted", `No recent PRs by ${packet.name} in this area.`));
  return section;
}

function decisionsSection(packet) {
  const section = handoverSection("Decisions to preserve");
  packet.preserve.forEach(decision => {
    const card = el("article", "detail-item");
    card.append(el("h4", "", `${decision.title} (${decision.status || "unknown"})`),
      el("p", "", `${decision.explicitPRs} explicitly linked PRs here · ${decision.titleMatchPRs} title matches ` +
        "(keyword guesses)" + (decision.supersession ? ` · ${decision.supersession}` : "")),
      sourceLinks(decision),
      el("p", "muted", decision.otherActiveCount
        ? `Other active participants: ${decision.otherActive.join(", ")}`
        : `No other active participant${decision.leavingParticipated ? ` besides ${packet.name}` : ""}.`));
    if (decision.rationale) {
      card.append(el("p", "muted", `Stated reason, quoted from ${decision.rationaleSource}:`),
        el("blockquote", "rationale", decision.rationale));
    }
    section.append(card);
  });
  if (!packet.preserve.length) section.append(el("p", "muted", "No RFC decision is linked to this area's PRs."));
  return section;
}

function questionsSection(packet) {
  const section = handoverSection(`Questions for ${packet.name}`);
  const list = el("ol", "handover-list");
  packet.ask.forEach(item => {
    const li = el("li", "", item.text);
    li.title = item.from;
    list.append(li);
  });
  section.append(packet.ask.length ? list : el("p", "muted", "No questions generated."));
  return section;
}

function handoverActions(packet) {
  const actions = el("div", "detail-actions");
  const status = el("span", "muted handover-status");
  const save = el("button", "", "Save to team memory");
  save.type = "button";
  save.onclick = async () => {
    save.disabled = true;
    try {
      await api(`/api/handover/${encodeURIComponent(packet.login)}/save`, {
        method: "POST",
        body: JSON.stringify({ component: packet.component, candidate: packet.successor?.login || null,
          visitor: visitorId }),
      });
      status.textContent = "Saved to team memory. Anyone drafting this handover will see what changed since.";
    } catch (error) {
      save.disabled = false;
      status.textContent = `Not saved: ${error.message}`;
    }
  };
  const copy = el("button", "secondary", "Copy as Markdown");
  copy.type = "button";
  copy.onclick = async () => {
    try {
      await navigator.clipboard.writeText(packet.markdown);
      status.textContent = "Copied. Paste it into a GitHub issue.";
    } catch (_) {
      status.textContent = "Copy unavailable here; open the Markdown below.";
    }
  };
  actions.append(save, copy, status);
  return actions;
}

function renderHandover(panel, packet, redraw) {
  panel.replaceChildren(el("h3", "", `Handover: ${packet.component}`),
    el("p", "muted", `If ${packet.name} (@${packet.login}) leaves · drafted ${packet.draftedOn}`));
  if (packet.changed) panel.append(changedLine(packet.changed));
  const markdown = document.createElement("details");
  markdown.append(el("summary", "", "Markdown"), el("pre", "handover-markdown", packet.markdown));
  panel.append(successorSection(packet, redraw), readingSection(packet), decisionsSection(packet),
    questionsSection(packet), el("p", "muted handover-caveat", packet.caveat), handoverActions(packet), markdown);
}

// Render the departure summary first, then put the highest-commit areas first in each section.
function renderDeparture(data, login) {
  const root = $("#departure-results");
  root.replaceChildren();
  const summary = data.summary || {};
  const simulation = data.simulation?.rows?.[0] || {};
  const person = data.graph?.nodes?.find(node =>
    node.focusRole === "departing" || node.props?.login === login,
  );
  const name = summary.name || person?.props?.name || login;
  const sentence = el(
    "p",
    "departure-sentence",
    `If ${name} left: ${summary.noOtherAuthor ?? countRisk(data, "NO OTHER AUTHOR")} code areas ` +
      "where they made 2+ commits in the last 12 months would have no other recent author " +
      `(${(summary.noOtherAuthor ?? countRisk(data, "NO OTHER AUTHOR")) -
        (summary.noOtherAuthorOrReviewer ?? 0)} of them were reviewed by other active people), ` +
      `${summary.oneOtherAuthor ?? countRisk(data, "ONE OTHER AUTHOR")} would have one other recent author, ` +
      `${summary.orphanedFiles ?? "—"} current files would have no other recent editor, ` +
      `and ${summary.cutOff ?? simulation.cutOff?.length ?? "—"} people would lose their ` +
      "link to the main collaboration network.",
  );
  const jump = el("a", "jump-evidence", "Jump to the evidence graph");
  jump.href = "#leave-evidence";
  root.append(sentence, jump);

  const decisions = data.decision_share?.rows || [];
  const mainDecision = decisions[0];
  const decisionMetric = !mainDecision
    ? "—"
    : Number(mainDecision.explicitPRs || 0) === 0
      ? "none"
      : `${mainDecision.theirExplicitPRs}/${mainDecision.explicitPRs}`;
  const metrics = [
    ["Bus factor 1", "≥50%",
      "One person wrote at least half of the area’s qualifying commits; other people may still have contributed."],
    ["NO OTHER AUTHOR", summary.noOtherAuthor ?? countRisk(data, "NO OTHER AUTHOR"),
      "No other active author has at least 2 commits here in the last 12 months; reviewers are shown separately."],
    ["ONE OTHER AUTHOR", summary.oneOtherAuthor ?? countRisk(data, "ONE OTHER AUTHOR"),
      "One other active author has at least 2 commits here in the last 12 months."],
    ["Bridge rank", simulation.betweennessRank ?? "—",
      "This person’s position by how often they connect collaboration groups in shortest paths."],
    ["Cut off", summary.cutOff ?? simulation.cutOff?.length ?? 0,
      "People losing their only modeled shared-file link to the largest group."],
    ["Main group", `${simulation.mainGroupBefore ?? "—"} → ${simulation.mainGroupAfter ?? "—"}`,
      "Largest collaboration group before and after the departure scenario."],
    ["Explicit decision PRs", decisionMetric,
      "Pull requests they opened out of explicitly linked pull requests for the leading decision; title guesses are separate below."],
  ];
  metrics[3][1] = summary.bridgeRank ?? simulation.betweennessRank ?? "—";
  const grid = el("div", "metric-grid");
  metrics.forEach(([label, value, tip]) => {
    const card = el("div", "metric-card");
    card.append(el("strong", "", value), el("span", "", label));
    const hint = el("span", "tip metric-tip", "What this means");
    hint.tabIndex = 0;
    hint.append(el("span", "tooltip", tip));
    card.append(hint);
    grid.append(card);
  });
  root.append(grid);

  const impact = data.impact?.rows || [];
  const exposed = impact
    .filter(row => ["NO OTHER AUTHOR", "ONE OTHER AUTHOR"].includes(row.risk))
    .sort((left, right) => Number(left.reviewerCount || 0) - Number(right.reviewerCount || 0) ||
      Number(right.theirCommits || 0) - Number(left.theirCommits || 0));
  const orphaned = exposed.filter(row => row.risk === "NO OTHER AUTHOR");
  const atRisk = exposed.filter(row => row.risk === "ONE OTHER AUTHOR");
  disclosure(root, `No other recent author · ${orphaned.length}`, orphaned.map(row => areaCard(row, login, name)));
  disclosure(root, `One other recent author · ${atRisk.length}`, atRisk.map(row => areaCard(row, login, name)));

  disclosure(root, `Decisions they worked on · ${decisions.length}`, decisions.map(row => {
    const card = el("article", "detail-item");
    const authors = (row.otherOpeners || []).map(item => `${item.login} (${item.prs} PRs)`).join(", ");
    const explicit = Number(row.explicitPRs || 0) === 0
      ? "No explicitly linked PRs"
      : `Explicitly linked PRs: they opened ${row.theirExplicitPRs} of ${row.explicitPRs}`;
    card.append(
      el("h4", "", row.decision),
      el("p", "", `${explicit} · Title match only: ${row.theirTitleMatchPRs} of ${row.titleMatchPRs}`),
      el("p", "muted", "Title matches are keyword guesses."),
      sourceLinks(row),
      el("p", "muted", `Other PR authors: ${authors || "none listed"}`),
    );
    askAction(card, `Who else worked on the ${row.decision} decision?`);
    return card;
  }));

  const cutOff = simulation.cutOff || [];
  disclosure(root, `People cut off from the main network · ${cutOff.length}`, [
    list(cutOff.length ? cutOff : ["No people lose a link to the main collaboration group in this model."]),
  ]);
  const files = data.files?.rows || [];
  const fileCount = summary.orphanedFiles ?? files.reduce(
    (total, row) => total + Number(row.orphanedFiles || 0),
    0,
  );
  const paths = files.flatMap(row =>
    (row.examplePaths || []).map(path => `${path} · ${row.component}`),
  );
  disclosure(root, `Files only they edited · ${fileCount}`, [list(paths)], false);

  if (data.successor_component) {
    const card = el("article", "detail-item");
    const candidates = (data.successor?.rows || []).map(row =>
      `${row.successor} · ${row.sharedFiles}/${row.outOf} shared files · ${row.theirCommits} commits`,
    );
    card.append(
      el("h4", "", `Suggested successor for ${data.successor_component}`),
      el("p", "", candidates.join("; ") || "No successor estimate returned."),
    );
    root.append(card);
  }
  // The focused graph summarises reviews as one edge per reviewer; the full graph draws the PRs behind them.
  let full = false;
  const toggle = el("button", "secondary", "Show full evidence");
  toggle.type = "button";
  toggle.onclick = () => {
    full = !full;
    toggle.textContent = full ? "Show focused evidence" : "Show full evidence";
    evidence("leave", full ? data.graph : (data.focus_graph || data.graph), [login], full ? "chat" : "departure");
  };
  const toggleRow = el("div", "detail-actions");
  toggleRow.append(toggle, el("span", "muted",
    "Full evidence adds the reviewed PRs, commits and files behind the summary edges."));
  root.append(toggleRow);
  evidence("leave", data.focus_graph || data.graph, [login], "departure");
}

function message(label, content, className = "") {
  const article = el("article", `chat-message ${className}`);
  article.append(el("div", "message-label", label), el("div", "answer-text", content));
  return article;
}

function markdown(node, source) {
  if (window.marked?.parse && window.DOMPurify?.sanitize) {
    node.innerHTML = window.DOMPurify.sanitize(window.marked.parse(source || ""));
    node.classList.add("markdown");
  } else {
    node.textContent = source || "No answer returned.";
  }
}

function toolCalls(parent, calls) {
  calls.forEach(call => {
    const item = el("section", "call-card");
    const heading = el("div", "call-title", call.label || call.tool);
    heading.append(el("small", "", `${call.row_count ?? 0} rows · ${call.ms ?? 0} ms`));
    const rows = call.rows || [];
    const shown = Math.min(rows.length, 12);
    item.append(heading, toolTable(call.tool, rows, shown));
    if ((call.row_count ?? 0) > shown) {
      item.append(el("p", "muted", `Showing ${shown} of ${call.row_count} rows.`));
    }
    item.append(el("div", "tool-params", `Parameters\n${JSON.stringify(call.params || {}, null, 2)}`));
    const details = document.createElement("details");
    details.append(el("summary", "", "Cypher query"));
    const copy = el("button", "secondary copy-button", "Copy query");
    copy.type = "button";
    copy.onclick = async () => {
      try {
        await navigator.clipboard.writeText(call.cypher || "");
        copy.textContent = "Copied";
      } catch (_) {
        copy.textContent = "Copy unavailable";
      }
    };
    details.append(copy, el("pre", "", call.cypher || "Query text unavailable"));
    item.append(details);
    parent.append(item);
  });
}

function answer(result) {
  const article = el("article", "chat-message answer-message");
  article.append(el("div", "message-label", "Bus Factor · graph answer"));
  const body = el("div", "answer-text");
  markdown(body, result.answer);
  const jump = el("a", "jump-evidence", "Jump to the evidence graph");
  jump.href = "#ask-evidence";
  article.append(body, jump);

  const details = document.createElement("details");
  details.className = "how-know";
  details.append(el("summary", "", `How I know · ${result.tool_calls?.length || 0} graph tool calls`));
  const calls = el("div", "tool-calls");
  toolCalls(calls, result.tool_calls || []);
  details.append(calls);
  article.append(details);

  const followups = (result.followups || []).slice(0, 4);
  if (followups.length) {
    const section = el("section", "followups");
    section.append(el("strong", "", "Keep exploring"));
    const chips = el("div", "chip-list");
    followups.forEach(question => {
      const button = el("button", "chip", question);
      button.type = "button";
      button.onclick = () => send(question);
      chips.append(button);
    });
    section.append(chips);
    article.append(section);
  }
  $("#chat-list").append(article);
  evidence("ask", result.graph, Object.values(result.tool_calls?.[0]?.params || {}));
  article.scrollIntoView({ block: "start" });
}

// Plain labels for the no-key starter tools; unknown fields get readable labels too.
const toolColumns = {
  successor: [["successor", "Successor"], ["sharedFiles", "Shared files"], ["theirCommits", "Recent commits here"]],
  why_not: [["rejected", "Rejected decision"], ["chosenInstead", "Chosen instead"],
    ["rationale", "Stated reason (quoted)"], ["rationaleSource", "Reason source"], ["evidence", "Evidence"],
    ["discussion", "Discussion"], ["whoToAsk", "Who to ask"]],
  handover_plan: [["component", "Area"], ["successor", "Suggested successor"], ["read", "Read these first"],
    ["preserve", "Decisions to preserve"], ["ask", "Questions"], ["skipped", "Skipped"]],
  declared_vs_actual: [["module", "Module"], ["declared", "Declared owners"], ["actualTop3", "Most active"], ["ownersNotInTop3", "Owners not in top 3"]],
};

// Plain text for one table cell: lists, capped lists ({items, truncated}) and small maps, never raw JSON.
function cellText(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.map(cellText).join(", ") : "—";
  if (typeof value === "object") {
    if (Array.isArray(value.items)) return `${cellText(value.items)} (+${value.truncated} more)`;
    if (value.login) return value.prs === undefined ? value.login : `${value.login} (${value.prs})`;
    return Object.entries(value).map(([key, item]) => `${key}: ${cellText(item)}`).join(" · ");
  }
  return typeof value === "number" && !Number.isInteger(value) ? value.toFixed(2) : String(value);
}

function toolTable(tool, rows, limit = 12) {
  const columns = toolColumns[tool] || Object.keys(rows[0] || {}).map(key => [key,
    key.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/^./, char => char.toUpperCase())]);
  if (!rows.length || !columns.length) return el("p", "muted", "No matching rows in the current graph.");
  const table = document.createElement("table");
  table.className = "tool-table";
  const head = document.createElement("thead");
  const header = document.createElement("tr");
  columns.forEach(([, label]) => header.append(el("th", "", label)));
  head.append(header);
  const body = document.createElement("tbody");
  rows.slice(0, limit).forEach(row => {
    const tr = document.createElement("tr");
    columns.forEach(([key]) => {
      const cell = el("td", "", cellText(row[key]));
      if (key === "discussion" && Number.isInteger(row[key])) {
        cell.replaceChildren(externalLink(`${GITHUB}/issues/${row[key]}`, `#${row[key]}`));
      }
      tr.append(cell);
    });
    body.append(tr);
  });
  table.append(head, body);
  return table;
}

function readableToolResult(tool, rows, title) {
  const article = el("article", "chat-message");
  article.append(el("div", "message-label", title), toolTable(tool, rows));
  return article;
}

async function send(question) {
  question = question.trim();
  if (!question) return;
  const token = ++state.askToken;
  const chat = $("#chat-list");
  const pending = message("Bus Factor", "Querying the graph…", "pending-message");
  pending.setAttribute("aria-live", "polite");
  const userMessage = message("You", question, "user-message");
  chat.append(userMessage, pending);
  userMessage.scrollIntoView({ block: "start" });
  $("#ask-welcome").classList.add("hidden");
  $("#ask-empty").classList.add("hidden");
  $("#question-input").value = "";
  grow();
  try {
    const data = await api("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question, user: visitorId, sessionId: state.sessionId }),
    });
    if (token !== state.askToken) return;
    pending.remove();
    answer(data);
  } catch (error) {
    if (token !== state.askToken) return;
    const text = error.status === 503
      ? "Chat needs an Anthropic API key on the server; you can still use the " +
        "departure simulator and the suggested questions."
      : `Could not answer this yet: ${error.message}`;
    pending.replaceChildren(el("p", "", text));
    const retry = el("button", "secondary", "Retry");
    retry.type = "button";
    retry.onclick = () => {
      pending.remove();
      send(question);
    };
    pending.append(retry);
    if (error.status === 503) $("#chat-disabled").classList.remove("hidden");
  }
}

$("#ask-form").onsubmit = event => {
  event.preventDefault();
  send($("#question-input").value);
};

function grow() {
  const input = $("#question-input");
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
}

$("#question-input").addEventListener("input", () => {
  grow();
  updateGhost();
});

$("#question-input").addEventListener("keydown", event => {
  const ghost = $("#ghost-text");
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("#ask-form").requestSubmit();
  } else if (event.key === "Escape") {
    ghost.textContent = "";
    ghost.dataset.completion = "";
  } else if (event.key === "Tab" && ghost.dataset.completion) {
    event.preventDefault();
    $("#question-input").value = ghost.dataset.completion;
    ghost.textContent = "";
    ghost.dataset.completion = "";
    grow();
  }
});

// Show the first matching named suggestion as a non-editing tab completion.
function updateGhost() {
  const value = $("#question-input").value;
  const ghost = $("#ghost-text");
  ghost.textContent = "";
  ghost.dataset.completion = "";
  if (!value.trim()) return;
  const match = state.suggestions.map(suggestionText).find(question =>
    question.toLowerCase().startsWith(value.toLowerCase()) && question.length > value.length,
  );
  if (match) {
    ghost.textContent = match;
    ghost.dataset.completion = match;
  }
}

$("#start-over").onclick = async () => {
  state.askToken++;
  try {
    await api(`/api/memory/${encodeURIComponent(visitorId)}`, { method: "DELETE" });
  } catch (_) {}
  try {
    localStorage.removeItem("busfactor-visitor");
  } catch (_) {}
  location.reload();
};

async function loadMemory() {
  try {
    const data = await api(`/api/memory/${encodeURIComponent(visitorId)}`);
    const item = data.recall?.find(entry => (entry.earlierQuestions || []).length) || data.recall?.[0];
    if (!item) return;
    const entity = String(item.entity || "a Delta topic").replace(/^[^:]+:/, "");
    const count = item.commitCount || item.newCommits || 0;
    const lastQuestion = item.earlierQuestions?.[0];
    $("#memory-banner").textContent = lastQuestion
      ? `Welcome back. Last time you asked: “${lastQuestion}.”` +
        (count > 0 ? `, ${count} new commits since then in ${entity}.` : "")
      : `Welcome back. Last time you asked about ${entity}.`;
    $("#memory-banner").classList.remove("hidden");
  } catch (_) {}
}

function mountEvidence(node) {
  const template = $("#evidence-template").content.firstElementChild.cloneNode(true);
  template.id = node.id;
  template.querySelector("h2").textContent = node.getAttribute("title");
  template.classList.add("is-placeholder");
  node.replaceWith(template);
}

document.querySelectorAll("evidencepanel").forEach(mountEvidence);
setTab();
loadLanding();
loadMemory();
