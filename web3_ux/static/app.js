async function loadDiscovery(){
  const comp = document.getElementById('compartment').value || undefined;
  const res = await fetch(`/api/discovery${comp?`?compartment_id=${encodeURIComponent(comp)}`:''}`);
  const data = await res.json();
  const root = document.getElementById('discoveryTables');
  root.innerHTML = '';
  const sections = ['vcns','subnets','security_lists','instances','load_balancers','functions_apps','streams'];
  sections.forEach(k=>{
    if(data[k]){
      root.appendChild(renderTable(k, data[k].items || []));
    }
  });
}

function renderTable(title, items){
  const section = document.createElement('section');
  const h = document.createElement('h3');
  h.textContent = `${title} (${items.length})`;
  section.appendChild(h);
  if(!items.length){
    const p=document.createElement('p');p.textContent='No data';section.appendChild(p);return section;
  }
  const cols = Object.keys(items[0]).slice(0,8);
  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const thr = document.createElement('tr');
  cols.forEach(c=>{const th=document.createElement('th');th.textContent=c;thr.appendChild(th);});
  thead.appendChild(thr); table.appendChild(thead);
  const tbody = document.createElement('tbody');
  items.forEach(it=>{ const tr=document.createElement('tr'); cols.forEach(c=>{ const td=document.createElement('td'); td.textContent=formatVal(it[c]); tr.appendChild(td); }); tbody.appendChild(tr); });
  table.appendChild(tbody);
  section.appendChild(table);
  return section;
}

function formatVal(v){
  if(v==null) return '';
  if(typeof v==='object') return JSON.stringify(v);
  return String(v);
}

async function loadCapacity(){
  const comp = document.getElementById('capCompartment').value || '';
  const res = await fetch(`/api/capacity${comp?`?compartment_id=${encodeURIComponent(comp)}`:''}`);
  const data = await res.json();
  document.getElementById('capacityOut').textContent = JSON.stringify(data,null,2);
}

async function loadCosts(){
  const tw = document.getElementById('timeWindow').value;
  const res = await fetch(`/api/costs?time_window=${tw}`);
  const data = await res.json();
  document.getElementById('costsOut').textContent = JSON.stringify(data,null,2);
}

async function loadShowOCI(){
  const res = await fetch('/api/showoci');
  const data = await res.json();
  document.getElementById('showOCIOut').textContent = (data.output || data.diff || JSON.stringify(data,null,2));
}

async function loadShowUsage(){
  const res = await fetch('/api/showusage');
  const data = await res.json();
  document.getElementById('showUsageOut').textContent = (data.output || JSON.stringify(data,null,2));
}

async function sendChat(){
  const input = document.getElementById('chatInput');
  const msg = input.value.trim(); if(!msg) return;
  const log = document.getElementById('chatLog');
  appendChat(log, 'user', msg);
  input.value='';
  try{
    const res = await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    const data = await res.json();
    appendChat(log, 'agent', data.reply || JSON.stringify(data));
  }catch(e){
    appendChat(log, 'agent', 'Error: '+e);
  }
}

function appendChat(root, who, text){
  const div = document.createElement('div');
  div.className = 'msg '+who;
  div.textContent = (who==='user'? 'You: ': 'Agent: ')+text;
  root.appendChild(div);
  root.scrollTop = root.scrollHeight;
}

async function loadRelations(){
  const res = await fetch('/api/relations');
  const data = await res.json();
  const mer = data.mermaid || 'graph TD; A-->B;';
  const el = document.getElementById('relationsGraph');
  el.textContent = mer;
  try{ mermaid.init(undefined, el); }catch(e){ console.error(e); }
}

async function loadDbSummary(){
  const res = await fetch('/api/db/summary');
  const data = await res.json();
  document.getElementById('dbSummary').textContent = JSON.stringify(data,null,2);
}

async function loadDbTable(){
  const table = document.getElementById('dbTable').value;
  const res = await fetch(`/api/db/table?table=${encodeURIComponent(table)}&limit=100`);
  const data = await res.json();
  const root = document.getElementById('dbTableView');
  root.innerHTML = '';
  const section = document.createElement('section');
  section.appendChild(renderTable(table, (data.rows||[]).slice(0,100)));
  root.appendChild(section);
}

async function syncDb(){
  const out = document.getElementById('dbSyncOut');
  out.textContent = 'Sync in progress...';
  try{
    const res = await fetch('/api/db/sync',{method:'POST'});
    const data = await res.json();
    out.textContent = JSON.stringify(data,null,2);
    await loadDbSummary();
  }catch(e){ out.textContent = 'Error: '+e; }
}

async function loadCostTrend(){
  const res = await fetch('/api/db/chart/costs');
  const data = await res.json();
  document.getElementById('dbChartsOut').textContent = JSON.stringify(data,null,2);
}

async function loadCapacityTrend(){
  const res = await fetch('/api/db/chart/capacity');
  const data = await res.json();
  document.getElementById('dbChartsOut').textContent = JSON.stringify(data,null,2);
}

async function analyzeFinops(){
  const tw = document.getElementById('finopsWindow').value;
  const th = parseFloat(document.getElementById('finopsThreshold').value||'3.0');
  const comp = document.getElementById('finopsCompartment').value||'';
  let url = `/api/finops/analyze?time_window=${encodeURIComponent(tw)}&threshold=${encodeURIComponent(th)}`;
  if(comp) url += `&compartment_id=${encodeURIComponent(comp)}`;
  const res = await fetch(url);
  const data = await res.json();
  document.getElementById('finopsOut').textContent = JSON.stringify(data,null,2);
}

// Preflight: check server config and enforce COMPARTMENT_OCID presence for Discovery/Capacity
async function checkPreflight(){
  try{
    const res = await fetch('/api/config');
    const data = await res.json();
    const cid = data.default_compartment_id || '';
    const hasComp = !!data.has_default_compartment;
    const banner = document.getElementById('preflight');
    const dBtn = document.getElementById('discoveryBtn');
    const cBtn = document.getElementById('capacityBtn');
    // Autofill inputs if empty and CID available
    const compIn = document.getElementById('compartment');
    const capIn = document.getElementById('capCompartment');
    const finIn = document.getElementById('finopsCompartment');
    const obsIn = document.getElementById('obsCompartment');
    if(cid){
      if(compIn && !compIn.value) compIn.value = cid;
      if(capIn && !capIn.value) capIn.value = cid;
      if(finIn && !finIn.value) finIn.value = cid;
      if(obsIn && !obsIn.value) obsIn.value = cid;
    }
    // Enable buttons if we have a CID either from env or user input
    const effectiveComp = (compIn && compIn.value) || cid;
    const ready = !!effectiveComp;
    banner.style.display = ready ? 'none' : 'block';
    if(dBtn) dBtn.disabled = !ready;
    if(cBtn) cBtn.disabled = !ready;
    // Hints when using env var
    const discHint = document.getElementById('discHint');
    const capHint = document.getElementById('capHint');
    const obsHint = document.getElementById('obsHint');
    const hintText = cid ? 'Using COMPARTMENT_OCID from .env' : '';
    if(discHint) discHint.textContent = hintText;
    if(capHint) capHint.textContent = hintText;
    if(obsHint) obsHint.textContent = hintText;
  }catch(e){
    // Non-fatal
    console.warn('Preflight failed', e);
  }
}

window.addEventListener('load', checkPreflight);
// Re-evaluate readiness when user types a compartment OCID
['compartment','capCompartment','finopsCompartment','obsCompartment'].forEach(id=>{
  const el = document.getElementById(id);
  if(el){ el.addEventListener('input', ()=>{ try{ checkPreflight(); }catch(_){} }); }
});

async function runQuickChecks(){
  const cid = document.getElementById('obsCompartment').value || '';
  const tr = document.getElementById('obsTimeRange').value || '24h';
  const ss = parseInt(document.getElementById('obsSample').value||'5', 10) || 5;
  const out = document.getElementById('obsQuickOut');
  const cards = document.getElementById('obsQuickCards');
  out.textContent = 'Running quick checks...';
  cards.innerHTML = '';
  let url = `/api/observability/quick_checks?time_range=${encodeURIComponent(tr)}&sample_size=${encodeURIComponent(ss)}`;
  if(cid) url += `&compartment_id=${encodeURIComponent(cid)}`;
  try{
    const res = await fetch(url);
    const data = await res.json();
    // Render friendly summary/cards
    const summary = data.summary || {}; const checks = data.checks || [];
    const region = data.region || '';
    const namespace = data.namespace || '';
    const wrap = document.createElement('div'); wrap.className='checks';
    const header = document.createElement('div'); header.className='check-item';
    const hname = document.createElement('div'); hname.className='check-name'; hname.textContent = 'Summary';
    const hbadge = document.createElement('span'); hbadge.className = 'badge '+(summary.ok?'badge-ok':'badge-fail'); hbadge.textContent = summary.ok?`OK (${summary.passed}/${summary.total})`:`FAIL (${summary.passed||0}/${summary.total||checks.length})`;
    header.appendChild(hname); header.appendChild(hbadge); wrap.appendChild(header);
    checks.forEach(c=>{
      const row = document.createElement('div'); row.className='check-item';
      const name = document.createElement('div'); name.className='check-name'; name.textContent = c.name || 'check';
      const badge = document.createElement('span'); badge.className='badge '+(c.success?'badge-ok':'badge-fail'); badge.textContent = c.success?'PASS':'FAIL';
      const info = document.createElement('div'); info.textContent = `count=${c.count ?? 0}`;
      // Actions: Copy query, Open Console
      const actions = document.createElement('div');
      actions.style.marginLeft = 'auto';
      const copyBtn = document.createElement('button'); copyBtn.textContent = 'Copy Query'; copyBtn.onclick = ()=>{ try{ navigator.clipboard.writeText(c.query||''); }catch(e){} };
      const link = document.createElement('a'); link.href = buildLaConsoleUrl(region, namespace); link.target = '_blank'; link.rel='noopener'; link.style.marginLeft='8px'; link.textContent = 'Open LA Console';
      actions.appendChild(copyBtn); actions.appendChild(link);
      row.appendChild(name); row.appendChild(badge); row.appendChild(info);
      row.appendChild(actions);
      wrap.appendChild(row);
    });
    cards.appendChild(wrap);
    // Keep raw JSON as well
    out.textContent = JSON.stringify(data,null,2);
  }catch(e){ out.textContent = 'Error: '+e; }
}

function buildLaConsoleUrl(region, namespace){
  // Use a safe generic LA console deep link with region context.
  // Prefilling queries via URL is not guaranteed/stable across versions; users can paste copied query.
  const base = 'https://cloud.oracle.com/loganalytics/log-groups';
  const params = new URLSearchParams();
  if(region) params.set('region', region);
  // Namespace can be displayed in future if stable linking requires it.
  return `${base}?${params.toString()}`;
}

// ===== Agents Admin (via MCP server) =====
async function loadAgents(){
  const list = document.getElementById('agentsList');
  const out = document.getElementById('agentsOut');
  list.innerHTML = 'Loading agents...'; out.textContent = '';
  try{
    const res = await fetch('/api/agents');
    const data = await res.json();
    renderAgents(list, data.items || data.agents || []);
    out.textContent = JSON.stringify(data,null,2);
  }catch(e){ list.innerHTML='Error loading agents'; out.textContent=String(e); }
}

function renderAgents(root, items){
  root.innerHTML = '';
  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const thr = document.createElement('tr');
  ['id','name','type','model','actions'].forEach(h=>{ const th=document.createElement('th'); th.textContent=h; thr.appendChild(th); });
  thead.appendChild(thr); table.appendChild(thead);
  const tbody = document.createElement('tbody');
  (items||[]).forEach(a=>{
    const tr = document.createElement('tr');
    const id=a.id||a.agentId||a.uuid||'';
    addCell(tr, id); addCell(tr, a.name||''); addCell(tr, a.type||''); addCell(tr, a.model||'');
    const td = document.createElement('td');
    const test = document.createElement('button'); test.textContent='Test'; test.onclick=()=>testAgent(id);
    const upd = document.createElement('button'); upd.textContent='Update'; upd.style.marginLeft='6px'; upd.onclick=()=>updateAgent(id);
    const del = document.createElement('button'); del.textContent='Delete'; del.style.marginLeft='6px'; del.onclick=()=>deleteAgent(id);
    td.appendChild(test); td.appendChild(upd); td.appendChild(del); tr.appendChild(td);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  root.appendChild(table);
}

function addCell(tr, txt){ const td=document.createElement('td'); td.textContent=txt; tr.appendChild(td); }

async function createAgent(){
  const name = document.getElementById('agentName').value.trim();
  const type = document.getElementById('agentType').value.trim();
  const model = document.getElementById('agentModel').value.trim();
  const out = document.getElementById('agentsOut');
  out.textContent='Creating agent...';
  try{
    const res = await fetch('/api/agents/create', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, type, model})});
    const data = await res.json(); out.textContent = JSON.stringify(data,null,2);
    await loadAgents();
  }catch(e){ out.textContent = 'Error: '+e; }
}

async function deleteAgent(id){
  const out = document.getElementById('agentsOut');
  try{
    const res = await fetch(`/api/agents/${encodeURIComponent(id)}`, {method:'DELETE'});
    const data = await res.json(); out.textContent = JSON.stringify(data,null,2);
    await loadAgents();
  }catch(e){ out.textContent = 'Error: '+e; }
}

// ===== KBs and Data Sources =====
async function loadKBs(){
  const root = document.getElementById('kbList'); const out = document.getElementById('kbOut');
  root.innerHTML = 'Loading KBs...'; out.textContent='';
  try{ const res=await fetch('/api/kbs'); const data=await res.json(); renderKBs(root, data.items||[]); out.textContent=JSON.stringify(data,null,2); }catch(e){ root.innerHTML='Error'; out.textContent=String(e); }
}

function renderKBs(root, items){
  root.innerHTML = '';
  const table=document.createElement('table'); const thead=document.createElement('thead'); const thr=document.createElement('tr');
  ['id','display_name','description','actions'].forEach(h=>{ const th=document.createElement('th'); th.textContent=h; thr.appendChild(th); }); thead.appendChild(thr); table.appendChild(thead);
  const tbody=document.createElement('tbody');
  (items||[]).forEach(k=>{
    const tr=document.createElement('tr'); const id=k.id||k.ocid||''; addCell(tr,id); addCell(tr,k.display_name||''); addCell(tr,k.description||'');
    const td=document.createElement('td');
    const upd=document.createElement('button'); upd.textContent='Update'; upd.onclick=()=>updateKB(id);
    const del=document.createElement('button'); del.textContent='Delete'; del.style.marginLeft='6px'; del.onclick=()=>deleteKB(id);
    td.appendChild(upd); td.appendChild(del); tr.appendChild(td); tbody.appendChild(tr);
  });
  table.appendChild(tbody); root.appendChild(table);
}

async function createKB(){
  const name=document.getElementById('kbName').value.trim(); const desc=document.getElementById('kbDesc').value.trim();
  const out=document.getElementById('kbOut'); out.textContent='Creating KB...';
  try{ const res=await fetch('/api/kbs/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name:name,description:desc})}); const data=await res.json(); out.textContent=JSON.stringify(data,null,2); await loadKBs(); }catch(e){ out.textContent='Error: '+e; }
}

async function updateKB(id){
  const out=document.getElementById('kbOut'); const tpl='{"display_name":"","description":""}'; const txt=prompt('Fields to update as JSON:',tpl); if(txt===null) return;
  let payload={}; try{ payload=JSON.parse(txt);}catch(e){ out.textContent='Invalid JSON'; return; }
  try{ const res=await fetch(`/api/kbs/${encodeURIComponent(id)}/update`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); const data=await res.json(); out.textContent=JSON.stringify(data,null,2); await loadKBs(); }catch(e){ out.textContent='Error: '+e; }
}

async function deleteKB(id){ const out=document.getElementById('kbOut'); try{ const res=await fetch(`/api/kbs/${encodeURIComponent(id)}`,{method:'DELETE'}); const data=await res.json(); out.textContent=JSON.stringify(data,null,2); await loadKBs(); }catch(e){ out.textContent='Error: '+e; } }

async function createDataSource(){
  const kb=document.getElementById('dsKbId').value.trim(); const name=document.getElementById('dsName').value.trim();
  const ns=document.getElementById('dsBucketNs').value.trim(); const bucket=document.getElementById('dsBucket').value.trim(); const prefix=document.getElementById('dsPrefix').value.trim();
  const out=document.getElementById('kbOut'); out.textContent='Creating Data Source...';
  const prefixes=[]; if(ns&&bucket&&(prefix||true)){ prefixes.push({namespace:ns,bucket:bucket,prefix:prefix}); }
  try{ const res=await fetch(`/api/kbs/${encodeURIComponent(kb)}/datasources/create`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name:name,object_storage_prefixes:prefixes})}); const data=await res.json(); out.textContent=JSON.stringify(data,null,2); await loadDataSources(); }catch(e){ out.textContent='Error: '+e; }
}

async function loadDataSources(){
  const kb=document.getElementById('dsKbId').value.trim(); const root=document.getElementById('dsList'); const out=document.getElementById('kbOut');
  root.innerHTML='Loading data sources...';
  try{ const res=await fetch(`/api/kbs/${encodeURIComponent(kb)}/datasources`); const data=await res.json(); renderDS(root, data.items||[]); out.textContent=JSON.stringify(data,null,2); }catch(e){ root.innerHTML='Error'; out.textContent=String(e); }
}

function renderDS(root, items){
  root.innerHTML=''; const table=document.createElement('table'); const thead=document.createElement('thead'); const thr=document.createElement('tr');
  ['id','display_name','knowledge_base_id','actions'].forEach(h=>{ const th=document.createElement('th'); th.textContent=h; thr.appendChild(th); }); thead.appendChild(thr); table.appendChild(thead);
  const tbody=document.createElement('tbody');
  (items||[]).forEach(d=>{ const tr=document.createElement('tr'); const id=d.id||''; addCell(tr,id); addCell(tr,d.display_name||''); addCell(tr,d.knowledge_base_id||''); const td=document.createElement('td'); const del=document.createElement('button'); del.textContent='Delete'; del.onclick=()=>deleteDS(id); td.appendChild(del); tr.appendChild(td); tbody.appendChild(tr); });
  table.appendChild(tbody); root.appendChild(table);
}

async function deleteDS(id){ const out=document.getElementById('kbOut'); try{ const res=await fetch(`/api/datasources/${encodeURIComponent(id)}`,{method:'DELETE'}); const data=await res.json(); out.textContent=JSON.stringify(data,null,2); await loadDataSources(); }catch(e){ out.textContent='Error: '+e; } }

// ===== Endpoints =====
async function loadEndpoints(){ const root=document.getElementById('epList'); const out=document.getElementById('epOut'); root.innerHTML='Loading endpoints...'; try{ const res=await fetch('/api/endpoints'); const data=await res.json(); renderEP(root, data.items||[]); out.textContent=JSON.stringify(data,null,2);}catch(e){ root.innerHTML='Error'; out.textContent=String(e);} }

function renderEP(root, items){ root.innerHTML=''; const table=document.createElement('table'); const thead=document.createElement('thead'); const thr=document.createElement('tr'); ['id','display_name','agent_id','lifecycle_state','actions'].forEach(h=>{ const th=document.createElement('th'); th.textContent=h; thr.appendChild(th); }); thead.appendChild(thr); table.appendChild(thead); const tbody=document.createElement('tbody'); (items||[]).forEach(ep=>{ const tr=document.createElement('tr'); const id=ep.id||''; addCell(tr,id); addCell(tr,ep.display_name||''); addCell(tr,ep.agent_id||''); addCell(tr,ep.lifecycle_state||''); const td=document.createElement('td'); const upd=document.createElement('button'); upd.textContent='Update'; upd.onclick=()=>updateEndpoint(id); const del=document.createElement('button'); del.textContent='Delete'; del.style.marginLeft='6px'; del.onclick=()=>deleteEndpoint(id); td.appendChild(upd); td.appendChild(del); tr.appendChild(td); tbody.appendChild(tr); }); table.appendChild(tbody); root.appendChild(table); }

async function createEndpoint(){ const name=document.getElementById('epName').value.trim(); const agent=document.getElementById('epAgentId').value.trim(); const desc=document.getElementById('epDesc').value.trim(); const trace=document.getElementById('epTrace').checked; const cit=document.getElementById('epCitation').checked; const out=document.getElementById('epOut'); out.textContent='Creating endpoint...'; try{ const res=await fetch('/api/endpoints/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name:name,agent_id:agent,description:desc,should_enable_trace:trace,should_enable_citation:cit})}); const data=await res.json(); out.textContent=JSON.stringify(data,null,2); await loadEndpoints(); }catch(e){ out.textContent='Error: '+e; } }

async function updateEndpoint(id){ const out=document.getElementById('epOut'); const tpl='{"display_name":"","description":"","should_enable_trace":false,"should_enable_citation":false}'; const txt=prompt('Fields to update as JSON:',tpl); if(txt===null) return; let payload={}; try{ payload=JSON.parse(txt);}catch(e){ out.textContent='Invalid JSON'; return; } try{ const res=await fetch(`/api/endpoints/${encodeURIComponent(id)}/update`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); const data=await res.json(); out.textContent=JSON.stringify(data,null,2); await loadEndpoints(); }catch(e){ out.textContent='Error: '+e; } }

async function deleteEndpoint(id){ const out=document.getElementById('epOut'); try{ const res=await fetch(`/api/endpoints/${encodeURIComponent(id)}`,{method:'DELETE'}); const data=await res.json(); out.textContent=JSON.stringify(data,null,2); await loadEndpoints(); }catch(e){ out.textContent='Error: '+e; } }
async function testAgent(id){
  const out = document.getElementById('agentsOut');
  const msg = prompt('Message to send to agent:', 'Hello');
  if(msg===null) return;
  out.textContent = 'Sending message...';
  try{
    const res = await fetch(`/api/agents/${encodeURIComponent(id)}/test`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message: msg})});
    const data = await res.json(); out.textContent = JSON.stringify(data,null,2);
  }catch(e){ out.textContent = 'Error: '+e; }
}

async function updateAgent(id){
  const out = document.getElementById('agentsOut');
  const tpl = '{\n  "name": "",\n  "type": "",\n  "model": "",\n  "description": "",\n  "config": {}\n}';
  const txt = prompt('Provide fields to update as JSON (leave empty to cancel):', tpl);
  if(txt===null) return;
  let payload={};
  try{ payload = JSON.parse(txt); }catch(e){ out.textContent='Invalid JSON'; return; }
  out.textContent = 'Updating agent...';
  try{
    const res = await fetch(`/api/agents/${encodeURIComponent(id)}/update`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    const data = await res.json(); out.textContent = JSON.stringify(data,null,2);
    await loadAgents();
  }catch(e){ out.textContent = 'Error: '+e; }
}
