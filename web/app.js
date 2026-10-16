const $ = (selector) => document.querySelector(selector);
const byId = (id) => document.getElementById(id);
const state = {cy:null, sessionId:crypto.randomUUID(), evidence:null};

// The departure renderer reads only these fields. The API contract test mirrors this list.
const DEPARTURE_FIELDS = Object.freeze({
  simulation: ["rows", "login", "mainGroupBefore", "mainGroupAfter", "cutOff", "betweennessRank"],
  impact: ["rows", "component", "risk", "expertsLeft", "theirCommits", "remaining"],
  files: ["rows", "component", "orphanedFiles", "theirFiles", "examplePaths"],
  decision_share: ["rows", "decision", "theirPRs", "totalPRs", "share", "otherOpeners", "login", "prs"],
  successor: ["rows", "successor", "sharedFiles", "outOf", "theirCommits"],
  graph: ["nodes", "edges"],
  focus_graph: ["nodes", "edges"],
  successor_component: []
});

async function api(path, options={}) {
  const response = await fetch(path, {headers:{"Content-Type":"application/json", ...(options.headers||{})}, ...options});
  const data = await response.json().catch(()=>({detail:response.statusText}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}
function el(tag, cls, text) {
  const node=document.createElement(tag);
  if(cls) node.className=cls;
  if(text!==undefined) node.textContent=text;
  return node;
}
function safe(value) { return value == null ? "" : String(value); }
function capGraph(graph, limit=60) {
  const nodes=graph?.nodes||[];
  if(nodes.length<=limit) return {nodes,edges:graph?.edges||[]};
  // The merged evidence is appended in tool-call order, so the tail favors the latest paths.
  const kept=new Set(nodes.slice(-limit).map(node=>String(node.id)));
  return {nodes:nodes.slice(-limit),edges:(graph.edges||[]).filter(edge=>kept.has(String(edge.source))&&kept.has(String(edge.target)))};
}
function graphLabel(node) {
  const props=node.props||{};
  const value=props.login||props.name||props.path||props.title||props.sha||props.number||node.key||"";
  return `${node.label||"Node"}\n${value}`;
}
function drawGraph(graph, rooted=false) {
  graph ||= {nodes:[],edges:[]};
  byId("graph-count").textContent=`${graph.nodes?.length||0} nodes · ${graph.edges?.length||0} edges`;
  if(!window.cytoscape){byId("node-properties").textContent="Cytoscape could not load. Graph evidence remains available in the answer details.";return;}
  if(!state.cy){
    state.cy=cytoscape({container:byId("cy"),elements:[],style:[
      {selector:"node",style:{"label":"data(labelText)","font-size":9,"color":"#26344b","text-wrap":"wrap","text-max-width":105,"text-valign":"bottom","text-margin-y":6,"width":25,"height":25,"background-color":"#8997aa","border-width":1,"border-color":"#fff"}},
      {selector:"edge",style:{"curve-style":"bezier","width":1.5,"line-color":"#b8c3d3","target-arrow-color":"#b8c3d3","target-arrow-shape":"triangle","arrow-scale":.7,"label":"data(type)","font-size":7,"color":"#66758b","text-background-color":"#fafbfd","text-background-opacity":1,"text-background-padding":2}},
      {selector:'node[label = "Person"]',style:{"background-color":"#456ee3"}},
      {selector:'node[label = "Component"]',style:{"background-color":"#e49a31"}},
      {selector:'node[label = "Module"]',style:{"background-color":"#9067d8"}},
      {selector:'node[label = "File"]',style:{"background-color":"#20a58d"}},
      {selector:'node[label = "Decision"]',style:{"background-color":"#d35b88"}},
      {selector:'node[risk = "ORPHANED"]',style:{"background-color":"#d65050","border-width":3,"border-color":"#ffc4c0"}},
      {selector:'node[risk = "AT RISK"]',style:{"background-color":"#d78b18","border-width":3,"border-color":"#ffe1a8"}},
      {selector:"node:selected",style:{"border-color":"#142d68","border-width":3}}
    ],layout:{name:"cose",animate:false,fit:true,padding:28}});
    state.cy.on("tap","node",evt=>{
      const data=evt.target.data();
      byId("node-properties").textContent=JSON.stringify({label:data.label,key:data.key,properties:data.props},null,2);
    });
  }
  state.cy.elements().remove();
  const nodes=(graph.nodes||[]).map(node=>({data:{id:String(node.id),label:node.label,labelText:graphLabel(node),key:node.key,
    props:node.props||{},risk:node.risk||"",root:node.focusRole==="departing"}}));
  const edges=(graph.edges||[]).map((edge,index)=>({data:{id:`e${index}`,source:String(edge.source),target:String(edge.target),type:edge.type}}));
  state.cy.add([...nodes,...edges]);
  const layout=rooted?{name:"breadthfirst",directed:false,roots:state.cy.nodes().filter(node=>node.data("root")===true),circle:false,spacingFactor:1.15,animate:false,fit:true,padding:34}:
    {name:"cose",animate:false,fit:true,padding:28};
  state.cy.layout(layout).run();
}
function showEvidence(focused, full, rooted=false) {
  state.evidence={focused,full,rooted,showFull:false};
  const toggle=byId("evidence-toggle");
  const different=(focused?.nodes?.length||0)!==(full?.nodes?.length||0)||(focused?.edges?.length||0)!==(full?.edges?.length||0);
  toggle.classList.toggle("hidden",!different);
  toggle.textContent="Show full evidence";
  drawGraph(focused,rooted);
}
byId("evidence-toggle").addEventListener("click",()=>{
  if(!state.evidence)return;
  state.evidence.showFull=!state.evidence.showFull;
  byId("evidence-toggle").textContent=state.evidence.showFull?"Show focused graph":"Show full evidence";
  drawGraph(state.evidence.showFull?state.evidence.full:state.evidence.focused,state.evidence.rooted&&!state.evidence.showFull);
});
function renderToolCalls(container, calls=[]) {
  if(!calls.length){container.append(el("p","muted","No graph tool was used."));return;}
  calls.forEach(call=>{
    const card=el("div","call-card"),title=el("div","call-title"),name=el("span","",`${call.tool} · ${call.row_count} rows`),ms=el("small","",`${call.ms} ms`);
    title.append(name,ms);card.append(title);const pre=el("pre");pre.textContent=Array.isArray(call.cypher)?call.cypher.join("\n\n"):call.cypher||"No Cypher was returned for this call.";card.append(pre);container.append(card);
  });
}
function showMemoryRecall(item){
  const changes=item.changedSinceLastAsked||[];
  const changed=changes.reduce((sum,row)=>sum+(Number(row.commitCount)||0),0);
  const entity=item.entity||"your graph topics",question=item.earlierQuestions?.[0];
  byId("memory-banner").textContent=`Last time you asked${question?` “${question}”`:""} about ${entity}; since then ${changed} new commits are connected to it.`;
  byId("memory-banner").classList.remove("hidden");
}
async function loadTeamMemory(){
  const list=byId("team-memory-list");
  try{const team=await api("/api/team");list.replaceChildren();
    const items=(team.observations||[]).slice(0,8);
    if(!items.length){list.append(el("li","muted","No shared observations yet."));return;}
    items.forEach(item=>{const claim=item.kind==="user_claim"?" · user-provided claim":"";
      const when=item.ts?new Date(Number(item.ts)).toLocaleString():"time unknown";
      list.append(el("li","",`${item.agent} · ${when}${claim}: ${item.text}`));});
  }catch(error){list.replaceChildren(el("li","muted",`Team memory unavailable: ${error.message}`));}
}
function renderAnswer(result, question) {
  const user=el("article","chat-message user-message"),userLabel=el("div","message-label","You"),userText=el("div","answer-text",question);user.append(userLabel,userText);
  const answer=el("article","chat-message"),label=el("div","message-label","Bus Factor · graph answer"),text=el("div","answer-text",result.answer||"No answer returned."),details=document.createElement("details"),summary=el("summary","",`How I know · ${result.tool_calls?.length||0} graph tool calls`),calls=el("div","tool-calls");
  details.append(summary,calls);renderToolCalls(calls,result.tool_calls||[]);answer.append(label,text,details);byId("chat-list").append(user,answer);byId("chat-list").scrollTop=byId("chat-list").scrollHeight;
  showEvidence(capGraph(result.graph,60),result.graph,false);
  if(result.memory_recall?.length)showMemoryRecall(result.memory_recall[0]);
  loadTeamMemory();
}
byId("ask-form").addEventListener("submit",async event=>{
  event.preventDefault();const question=byId("question-input").value.trim(),user=byId("user-input").value.trim();if(!question||!user)return;
  const button=event.submitter;button.disabled=true;button.textContent="Thinking…";
  try{const result=await api("/api/ask",{method:"POST",body:JSON.stringify({question,user,sessionId:state.sessionId})});renderAnswer(result,question);byId("question-input").value="";}
  catch(error){byId("chat-list").append(el("div","chat-message",`Request failed: ${error.message}`));}
  finally{button.disabled=false;button.innerHTML='Ask <span aria-hidden="true">↗</span>';}
});
document.querySelectorAll(".tab").forEach(button=>button.addEventListener("click",()=>{
  document.querySelectorAll(".tab").forEach(item=>item.classList.toggle("active",item===button));
  document.querySelectorAll(".panel").forEach(panel=>panel.classList.toggle("active-panel",panel.id===button.dataset.panel));
}));
document.querySelectorAll(".suggestions button").forEach(button=>button.addEventListener("click",()=>{byId("question-input").value=button.textContent;byId("question-input").focus();}));
function makeList(items){const list=el("ul");(items||[]).forEach(item=>list.append(el("li","",typeof item==="string"?item:JSON.stringify(item))));return list;}
function addRiskRow(container,row){
  const details=document.createElement("details");details.className="risk-card";
  const summary=document.createElement("summary"),left=el("span","",`${row.component} · ${row.expertsLeft} ${row.expertsLeft===1?"expert":"experts"} left`),tag=el("span",`risk-tag ${row.risk==="ORPHANED"?"orphan":""}`,row.risk);
  summary.append(left,tag);const content=el("div","risk-content");
  const remaining=(row.remaining||[]).join(", ")||"none";
  content.append(el("div","",`Their commits: ${row.theirCommits}; remaining expert${row.expertsLeft===1?"":"s"}: ${remaining}`));
  details.append(summary,content);container.append(details);
}
function renderDeparture(data){
  const root=byId("departure-results");root.replaceChildren();
  const sim=data.simulation?.rows?.[0]||{};
  const metrics=el("div","headline-grid");
  [["Main group before",sim.mainGroupBefore],["Main group after",sim.mainGroupAfter],["Cut off",sim.cutOff?.length||0],["Bridge rank",sim.betweennessRank||"—"]].forEach(([label,value])=>{
    const metric=el("div","metric");metric.append(el("strong","",safe(value)),el("span","",label));metrics.append(metric);
  });
  root.append(metrics);

  const cutoff=document.createElement("details");cutoff.className="risk-card";cutoff.append(el("summary","","People cut off from the main group"));
  const cutoffContent=el("div","risk-content");
  cutoffContent.append(sim.cutOff?.length?makeList(sim.cutOff):el("div","","No people were cut off from the largest surviving group."));
  cutoff.append(cutoffContent);root.append(cutoff);

  const impact=data.impact?.rows||[],exposed=impact.filter(row=>row.risk==="ORPHANED"||row.risk==="AT RISK");
  exposed.sort((a,b)=>(b.theirCommits||0)-(a.theirCommits||0));
  const riskTitle=el("h3","","Component exposure");root.append(riskTitle);
  if(!exposed.length)root.append(el("p","empty-state","No recent component expertise is exposed for this person."));
  exposed.forEach(row=>addRiskRow(root,row));
  const covered=impact.filter(row=>row.risk==="COVERED").sort((a,b)=>(b.theirCommits||0)-(a.theirCommits||0));
  if(covered.length){
    const group=document.createElement("details");group.className="risk-card covered-group";
    group.append(el("summary","",`+ ${covered.length} covered components`));
    const content=el("div","risk-content");covered.forEach(row=>addRiskRow(content,row));group.append(content);root.append(group);
  }

  const files=data.files?.rows||[],fileCard=document.createElement("details");fileCard.className="risk-card";
  fileCard.append(el("summary","",`Orphaned files by component · ${files.reduce((sum,row)=>sum+(row.orphanedFiles||0),0)} files`));
  const fileContent=el("div","risk-content");
  files.forEach(row=>{fileContent.append(el("strong","",`${row.component} · ${row.orphanedFiles} of ${row.theirFiles} files`));fileContent.append(makeList(row.examplePaths||[]));});
  if(!files.length)fileContent.append(el("div","","No orphaned current files found."));
  fileCard.append(fileContent);root.append(fileCard);

  const decisions=data.decision_share?.rows||[],decisionCard=document.createElement("details");decisionCard.className="risk-card";
  decisionCard.append(el("summary","","Decisions they carry · who to ask"));
  const decisionContent=el("div","risk-content");
  if(!decisions.length)decisionContent.append(el("div","","No decision share above the current threshold."));
  decisions.forEach(row=>{
    decisionContent.append(el("strong","",`${row.decision} · ${row.theirPRs}/${row.totalPRs} implementing PRs (${Math.round((row.share||0)*100)}%)`));
    decisionContent.append(makeList((row.otherOpeners||[]).map(person=>`${person.login} (${person.prs} PRs)`)));
  });
  decisionCard.append(decisionContent);root.append(decisionCard);

  const successors=data.successor?.rows||[],successorCard=el("div","risk-card");
  successorCard.append(el("div","call-title",`Best successor for ${data.successor_component||"the exposed component"}`));
  const successorContent=el("div","risk-content");
  successorContent.append(data.successor_component?makeList(successors.map(row=>`${row.successor} · ${row.sharedFiles}/${row.outOf} shared files · ${row.theirCommits} component commits`)):el("div","","No ORPHANED or AT RISK component was found."));
  successorCard.append(successorContent);root.append(successorCard);
  showEvidence(data.focus_graph||{nodes:[],edges:[]},data.graph||{nodes:[],edges:[]},true);
}
byId("person-form").addEventListener("submit",async event=>{
  event.preventDefault();const text=byId("person-search").value.trim();if(!text)return;
  const out=byId("person-results");out.replaceChildren(el("span","muted","Searching the graph…"));
  try{
    const result=await api("/api/tools/find_entity",{method:"POST",body:JSON.stringify({params:{text,limit:15}})});out.replaceChildren();
    const people=(result.rows||[]).filter(row=>row.kind==="person");
    if(!people.length)out.append(el("span","muted","No people matched that search."));
    people.forEach(person=>{const login=person.key,button=el("button","person-result",`${person.label||login} · @${login}`);button.type="button";button.addEventListener("click",()=>runDeparture(login));out.append(button);});
  }catch(error){out.replaceChildren(el("span","muted",error.message));}
});
async function runDeparture(login){
  byId("person-search").value=login;byId("departure-results").replaceChildren(el("div","empty-state","Running graph departure queries…"));
  try{renderDeparture(await api(`/api/departure/${encodeURIComponent(login)}`));}
  catch(error){byId("departure-results").replaceChildren(el("div","empty-state",`Simulator failed: ${error.message}`));}
}
const toolParam=byId("tool-param");
byId("tool-select").addEventListener("change",()=>{
  const value=byId("tool-select").value;toolParam.placeholder=value==="find_entity"?"Search text":value==="decision_trace"?"Exact file path":value==="drift"?"Confidence (high or low)":"Optional filter";
  toolParam.classList.toggle("hidden",["groups","bridges","bus_factor"].includes(value));
});
byId("run-tool").addEventListener("click",async()=>{
  const name=byId("tool-select").value,value=toolParam.value.trim();let params={};
  if(name==="find_entity")params={text:value};if(name==="decision_trace")params={path:value};if(name==="drift"&&value)params={minConfidence:value};
  if(name==="bus_factor")params={minCommits:2,minTotal:5};if(name==="bridges")params={limit:10};
  byId("tool-result").classList.remove("hidden");byId("tool-result").textContent="Running…";
  try{const result=await api(`/api/tools/${name}`,{method:"POST",body:JSON.stringify({params})});byId("tool-result").textContent=JSON.stringify(result.rows,null,2);showEvidence(capGraph(result.graph,60),result.graph,false);}
  catch(error){byId("tool-result").textContent=error.message;}
});
async function init(){
  try{const health=await api("/api/health");byId("health-dot").className="good";byId("health-text").textContent=`${health.nodes.toLocaleString()} nodes · ${health.edges.toLocaleString()} edges`;}
  catch(_){byId("health-dot").className="bad";byId("health-text").textContent="Graph unavailable";}
  try{const memory=await api(`/api/memory/${encodeURIComponent(byId("user-input").value)}`);if(memory.recall?.length)showMemoryRecall(memory.recall[0]);else if(memory.episodes?.[0]){byId("memory-banner").textContent=`Last session: ${memory.episodes[0].text||"a graph question"}.`;byId("memory-banner").classList.remove("hidden");}}
  catch(_){}
}
init();
loadTeamMemory();
