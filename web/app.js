import { renderEvidence } from "./graph.js?v=11b";
import { mountPeopleCombobox } from "./people-combobox.js?v=11b";

const $ = selector => document.querySelector(selector);
const state = {
  evidence: { leave: null, ask: null },
  suggestions: [],
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
    if (item.tool && !$("#chat-disabled").classList.contains("hidden")) {
      if (item.tool === "departure") return selectPerson(item.params?.login);
      location.hash = "#ask";
      return runToolSuggestion(item);
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
    const article = el("article", "chat-message");
    article.append(
      el("div", "message-label", item.label || item.tool),
      el("pre", "tool-result", JSON.stringify(result.rows || [], null, 2)),
    );
    chat.append(article);
    evidence("ask", result.graph, Object.values(item.params || {}));
  } catch (error) {
    chat.lastElementChild.textContent = error.message;
  }
}

async function loadLanding() {
  try {
    const data = await api("/api/summary");
    $("#headline").textContent =
      `${data.busFactorOne} of ${data.componentsReported} active code areas in Delta Lake ` +
      "have a bus factor of 1: one person wrote at least half of their commits in the last 12 months.";
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
    $("#dataset-counts").textContent +=
      ` Snapshot graph: ${Number(health.nodes).toLocaleString()} records and ` +
      `${Number(health.edges).toLocaleString()} relationships.`;
  } catch (_) {
    $("#dataset-counts").textContent += " Snapshot graph counts unavailable.";
  }

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

function areaCard(row, login, name) {
  const card = el("article", "detail-item");
  const heading = el("h4", "", row.component);
  const badgeClass = row.risk === "ORPHANED" ? "orphan" : "at-risk";
  heading.append(" ", el("span", `risk-badge ${badgeClass}`, row.risk));

  const display = `${name} (@${login})`;
  const commits = Number(row.theirCommits || 0);
  const others = Number(row.expertsLeft || 0);
  const contribution = `${display} wrote ${commits} recent commit${commits === 1 ? "" : "s"} here`;
  const detail = others
    ? `${others} other active contributor${others === 1 ? "" : "s"} ` +
      `remain${others === 1 ? "s" : ""}: ${(row.remaining || []).join(", ")}.`
    : "No other active contributor with at least 2 recent commits.";
  card.append(heading, el("p", "", `${contribution}. ${detail}`));

  const actions = el("div", "detail-actions");
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
    `If ${name} left: ${summary.orphaned ?? countRisk(data, "ORPHANED")} code areas ` +
      "would have no other active contributor with at least 2 recent commits, " +
      `${summary.atRisk ?? countRisk(data, "AT RISK")} would rely on one remaining person, ` +
      `${summary.orphanedFiles ?? "—"} current files would have no other recent editor, ` +
      `and ${summary.cutOff ?? simulation.cutOff?.length ?? "—"} people would lose their ` +
      "link to the main collaboration network.",
  );
  const jump = el("a", "jump-evidence", "Jump to the evidence graph");
  jump.href = "#leave-evidence";
  root.append(sentence, jump);

  const decisions = data.decision_share?.rows || [];
  const mainDecision = decisions[0];
  const decisionMetric = mainDecision
    ? `${mainDecision.theirPRs}/${mainDecision.totalPRs}`
    : "—";
  const metrics = [
    ["Bus factor 1", "≥50%",
      "One person wrote at least half of the area’s qualifying commits; other people may still have contributed."],
    ["ORPHANED", summary.orphaned ?? countRisk(data, "ORPHANED"),
      "No other active contributor has at least 2 recent commits in the area."],
    ["AT RISK", summary.atRisk ?? countRisk(data, "AT RISK"),
      "One active contributor remains under the current activity threshold."],
    ["Bridge rank", simulation.betweennessRank ?? "—",
      "This person’s position by how often they connect collaboration groups in shortest paths."],
    ["Cut off", summary.cutOff ?? simulation.cutOff?.length ?? 0,
      "People losing their only modeled shared-file link to the largest group."],
    ["Main group", `${simulation.mainGroupBefore ?? "—"} → ${simulation.mainGroupAfter ?? "—"}`,
      "Largest collaboration group before and after the departure scenario."],
    ["Decision share", decisionMetric,
      "Pull requests this person opened out of all pull requests linked to the leading decision."],
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
    .filter(row => ["ORPHANED", "AT RISK"].includes(row.risk))
    .sort((left, right) => Number(right.theirCommits || 0) - Number(left.theirCommits || 0));
  const orphaned = exposed.filter(row => row.risk === "ORPHANED");
  const atRisk = exposed.filter(row => row.risk === "AT RISK");
  disclosure(root, `Areas with no expert left · ${orphaned.length}`, orphaned.map(row => areaCard(row, login, name)));
  disclosure(root, `Areas relying on one person · ${atRisk.length}`, atRisk.map(row => areaCard(row, login, name)));

  disclosure(root, `Decisions they carry · ${decisions.length}`, decisions.map(row => {
    const card = el("article", "detail-item");
    const authors = (row.otherOpeners || []).map(item => `${item.login} (${item.prs} PRs)`).join(", ");
    card.append(
      el("h4", "", row.decision),
      el("p", "", `They opened ${row.theirPRs} of ${row.totalPRs} pull requests ` +
        `linked to this decision (${Math.round((row.share || 0) * 100)}%).`),
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
    item.append(
      heading,
      el("div", "tool-params", `Parameters\n${JSON.stringify(call.params || {}, null, 2)}`),
      el("pre", "tool-rows", call.rows
        ? JSON.stringify(call.rows, null, 2)
        : `${call.row_count ?? 0} result rows returned; row values are not included in this API trace.`),
    );
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
}

async function send(question) {
  question = question.trim();
  if (!question) return;
  const token = ++state.askToken;
  const chat = $("#chat-list");
  const pending = message("Bus Factor", "Querying the graph…", "pending-message");
  pending.setAttribute("aria-live", "polite");
  chat.append(message("You", question, "user-message"), pending);
  $("#ask-empty").classList.add("hidden");
  $("#question-input").value = "";
  grow();
  chat.scrollTop = chat.scrollHeight;
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
    const item = data.recall?.[0];
    if (!item) return;
    const entity = String(item.entity || "a Delta topic").replace(/^[^:]+:/, "");
    const count = item.commitCount || item.newCommits || 0;
    $("#memory-banner").textContent =
      `Welcome back — since you last asked about ${entity}, ` +
      `${count} new commits landed.`;
    $("#memory-banner").classList.remove("hidden");
  } catch (_) {}
}

function mountEvidence(node) {
  const template = $("#evidence-template").content.firstElementChild.cloneNode(true);
  template.id = node.id;
  template.querySelector("h2").textContent = node.getAttribute("title");
  node.replaceWith(template);
}

document.querySelectorAll("evidencepanel").forEach(mountEvidence);
setTab();
loadLanding();
loadMemory();
