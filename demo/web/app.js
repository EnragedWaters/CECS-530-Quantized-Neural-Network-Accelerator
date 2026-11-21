/* Browser code presents real backend calculations; it does not recreate the numerical model. */
'use strict';
const $=id=>document.getElementById(id);
const fmt=(n,d=0)=>Number(n).toLocaleString(undefined,{maximumFractionDigits:d});
const phases=['load_inputs','load_weights','compute','store_outputs'];
const phaseNames={load_inputs:'Load inputs',load_weights:'Load weights',compute:'Compute',store_outputs:'Store answers'};
const state={view:'accelerator',precision:'int8',run:null,position:0,timer:null,request:0,meta:null};
async function api(path,body){const r=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(data.error||'The calculation could not finish.');return data;}
function pause(){if(state.timer)clearInterval(state.timer);state.timer=null;$('play').textContent='▶ Play';}
function selectView(name){pause();state.view=name;document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==name+'-view');document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('selected',b.dataset.view===name);if(b.dataset.view===name)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});}
async function loadToy(){pause();state.run=null;state.position=0;const request=++state.request;$('toy-error').hidden=true;$('toy-stage').hidden=true;
 try{const run=await api('/api/simulate',{preset:$('toy-preset').value,precision:state.precision,config:{lanes:+$('toy-lanes').value,local_read_bytes_per_cycle:+$('toy-local').value,external_bytes_per_cycle:+$('toy-external').value}});if(request!==state.request)return;state.run=run;$('toy-stage').hidden=false;renderToy();}
 catch(e){if(request!==state.request)return;$('toy-error').textContent=e.message;$('toy-error').hidden=false;$('toy-total').textContent='—';$('toy-answer').textContent='—';}}
function renderToy(){const r=state.run;if(!r)return;const n=state.position;const event=n?r.trace[n-1]:null;const active=event?.phase;
 $('trace-position').max=r.trace.length;$('trace-position').value=n;$('cycle-label').textContent=`Cycle ${n} of ${fmt(r.metrics.total_cycles)}`;$('phase-pill').textContent=n===r.trace.length?'Complete':(phaseNames[active]||'Ready to start');
 $('external-path').classList.toggle('flowing',active==='load_inputs'||active==='load_weights'||active==='store_outputs');$('local-path').classList.toggle('flowing',active==='compute');
 $('machine-lane-caption').textContent=`${r.config.lanes} ${r.config.lanes===1?'lane':'lanes'} · ${r.precision==='int8'?'2':'8'} bytes per multiply-add`;
 $('phase-timeline').replaceChildren(...phases.map(phase=>{const b=document.createElement('button');b.textContent=`${phaseNames[phase]} · ${r.metrics[phase+'_cycles']}`;b.style.flex=r.metrics[phase+'_cycles'];b.className=phase===active?'active':(active&&phases.indexOf(phase)<phases.indexOf(active)?'past':'');b.onclick=()=>{pause();state.position=r.trace.findIndex(e=>e.phase===phase)+1;renderToy();};return b;}));
 const currentValues={};let group=-1;
 for(const e of r.trace.slice(0,n)){if(e.phase!=='compute')continue;if(e.group_start!==group){group=e.group_start;Object.keys(currentValues).forEach(k=>delete currentValues[k]);}for(const op of e.macs)currentValues[op.lane]=op;}
 const grid=$('lane-grid');grid.style.setProperty('--lanes',Math.min(r.config.lanes,8));grid.replaceChildren(...Array.from({length:r.config.lanes},(_,i)=>{const op=currentValues[i];const activeOp=event?.macs?.find(o=>o.lane===i);const status=activeOp?'working':event?.waiting_lanes?.includes(i)?'waiting':event?.unused_lanes?.includes(i)?'unused':op?.finished?'done':'';
 const div=document.createElement('div');div.className='lane '+status;const title=document.createElement('strong');title.textContent='Lane '+(i+1);const value=document.createElement('div');value.className='sum';value.textContent=op?fmt(op.accumulator,4):'—';const detail=document.createElement('small');detail.textContent=activeOp?`${fmt(activeOp.left,3)} × ${fmt(activeOp.right,3)}`:status==='waiting'?'Waiting for data':status==='unused'?'No output assigned':op?.finished?'Output complete':'Ready';div.append(title,value,detail);return div;}));
 let explanation='Press Step to load the input values.';
 if(event?.bytes)explanation=`${phaseNames[active]}: move ${event.bytes} bytes this cycle (${fmt(event.phase_moved_bytes)} of ${fmt(event.phase_total_bytes)} bytes).`;
 if(active==='compute'){const op=event.macs[0];explanation=`Lane ${op.lane+1}: ${fmt(op.accumulator_before,4)} + (${fmt(op.left,4)} × ${fmt(op.right,4)}) = ${fmt(op.accumulator,4)}. ${event.macs.length} ${event.macs.length===1?'lane works':'lanes work'} this cycle.`;if(event.waiting_lanes.length)explanation+=` ${event.waiting_lanes.length} wait for the local read connection.`;}
 if(n===r.trace.length)explanation=`Finished. ${r.output[0].length} ${r.output[0].length===1?'answer':'answers'} stored: ${r.output[0].map(v=>fmt(v,4)).join(', ')}.`;
 $('event-explanation').textContent=explanation;$('toy-total').textContent=fmt(r.metrics.total_cycles);$('toy-answer').textContent=fmt(r.output[0][0],4);$('step').disabled=n>=r.trace.length;
 $('toy-lesson-title').textContent=r.preset==='single'?'Where does 29 come from?':r.preset==='parallel'?'Independent outputs can run together.':'A last group can leave lanes unused.';
 $('toy-lesson').textContent=r.preset==='tail'?'There are ten outputs, each with 64 terms. With eight lanes, the second group has only two outputs. Empty lanes are different from lanes waiting for data.':'Load the values, calculate each output’s dot product, then store the answers. More lanes help only when they have independent outputs and enough data.';
}
function step(){if(state.run&&state.position<state.run.trace.length){state.position++;renderToy();}else pause();}
function play(){if(!state.run)return;if(state.timer){pause();return;}if(state.position>=state.run.trace.length)state.position=0;state.timer=setInterval(()=>{step();if(state.position>=state.run.trace.length)pause();},+$('playback-speed').value);$('play').textContent='Ⅱ Pause';}
$('play').onclick=play;$('step').onclick=()=>{pause();step();};$('reset').onclick=()=>{pause();state.position=0;renderToy();};$('trace-position').oninput=e=>{pause();state.position=+e.target.value;renderToy();};$('playback-speed').onchange=()=>{if(state.timer){pause();play();}};
['toy-lanes','toy-local','toy-external'].forEach(id=>$(id).onchange=loadToy);
$('toy-preset').onchange=()=>{$('toy-lanes').value=$('toy-preset').value==='single'?'1':'8';loadToy();};
document.querySelectorAll('[data-precision]').forEach(b=>b.onclick=()=>{state.precision=b.dataset.precision;document.querySelectorAll('[data-precision]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});loadToy();});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>selectView(b.dataset.view));
document.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(document.activeElement.tagName)||state.view!=='accelerator')return;if(e.code==='Space'){e.preventDefault();play();}if(e.code==='ArrowRight'){e.preventDefault();pause();step();}if(e.code==='ArrowLeft'){e.preventDefault();pause();state.position=Math.max(0,state.position-1);renderToy();}});
loadToy();
