"""A standalone, offline score viewer. It opens no network connections."""

import html
import json
from pathlib import Path


def write_report(path, sessions, title='CSI motion report', note=''):
    payload = json.dumps(sessions, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>__TITLE__</title>
<style>
body{font:16px system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;color:#dce5ed;background:#111923}
h1{font-size:30px}p{line-height:1.6;color:#b8c8d5}.cards{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}
.card{background:#1c2a38;padding:18px 24px;border-radius:8px;min-width:170px}.card strong{display:block;font-size:25px;color:#fff}
select{font:inherit;padding:10px;background:#243647;color:#fff;border:1px solid #536777;border-radius:6px}
svg{width:100%;background:#182431;border-radius:8px;touch-action:none}text{fill:#aabccc;font-size:12px}
code{color:#85d3cf}#cursor{min-height:28px;color:#b8e0de}table{border-collapse:collapse;width:100%;margin-top:20px}td,th{text-align:left;border-bottom:1px solid #344554;padding:10px}
</style>
<h1>__TITLE__</h1><p>__NOTE__</p>
<label for="session">Recording </label><select id="session"></select>
<div class="cards"><div class="card">Motion windows<strong id="motion"></strong></div><div class="card">Still windows<strong id="still"></strong></div><div class="card">Unknown windows<strong id="unknown"></strong></div></div>
<svg id="plot" viewBox="0 0 1000 350" role="img" aria-label="Motion score over elapsed time"></svg>
<p id="cursor">Move over the plot for window details.</p>
<p>Cyan: motion score. Orange: calibrated threshold. Red shading: motion decision. Gray shading: unusable data. A still decision does not establish an empty room.</p>
<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody id="metrics"></tbody></table>
<p>All processing and rendering are local. This page contains scores and quality states, with no packet payloads.</p>
<script>
const sessions=__DATA__;
const select=document.getElementById('session'), svg=document.getElementById('plot');
const ns='http://www.w3.org/2000/svg';
function el(name,attrs,text){const e=document.createElementNS(ns,name);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;svg.appendChild(e);return e;}
sessions.forEach((s,i)=>{const o=document.createElement('option');o.value=i;o.textContent=s.name;select.appendChild(o);});
function draw(){
 const s=sessions[+select.value],r=s.windows;svg.replaceChildren();
 for(const state of ['motion','still','unknown'])document.getElementById(state).textContent=r.filter(w=>w.state===state).length;
 const origin=r[0].start,end=r[r.length-1].end,span=end-origin||1;
 const ymax=Math.max(...r.map(w=>w.score||0),...r.map(w=>w.threshold||0),.001)*1.12;
 const x=t=>60+900*(t-origin)/span,y=v=>300-260*v/ymax;
 r.forEach(w=>{if(w.state==='motion'||w.state==='unknown')el('rect',{x:x(w.start),y:40,width:Math.max(1,x(w.end)-x(w.start)),height:260,fill:w.state==='motion'?'#c05f61':'#8b97a1',opacity:.055});});
 for(let i=0;i<=4;i++){const v=ymax*i/4;el('line',{x1:60,y1:y(v),x2:960,y2:y(v),stroke:'#354554'});el('text',{x:5,y:y(v)+4},v.toFixed(4));const t=origin+span*i/4;el('text',{x:x(t)-12,y:325},(t-origin).toFixed(1)+'s');}
 let d='',newSegment=true;r.forEach(w=>{if(w.score===null){newSegment=true;return;}d+=(newSegment?'M':'L')+x((w.start+w.end)/2)+','+y(w.score)+' ';newSegment=false;});
 el('path',{d,fill:'none',stroke:'#6bd6d0','stroke-width':2});
 if(r[0].threshold)el('line',{x1:60,x2:960,y1:y(r[0].threshold),y2:y(r[0].threshold),stroke:'#efa263','stroke-width':2,'stroke-dasharray':'7 5'});
 const body=document.getElementById('metrics');body.replaceChildren();
 for(const [k,v] of Object.entries(s.metrics||{})){const tr=document.createElement('tr');for(const text of [k.replaceAll('_',' '),typeof v==='number'?Number(v.toFixed(4)):String(v)]){const td=document.createElement('td');td.textContent=text;tr.appendChild(td);}body.appendChild(tr);}
 svg.onpointermove=e=>{const rel=(e.clientX-svg.getBoundingClientRect().left)/svg.getBoundingClientRect().width;const time=origin+(rel*1000-60)/900*span;const w=r.reduce((a,b)=>Math.abs((b.start+b.end)/2-time)<Math.abs((a.start+a.end)/2-time)?b:a);document.getElementById('cursor').textContent=`${(w.start-origin).toFixed(2)} to ${(w.end-origin).toFixed(2)} s | ${w.state} | score ${w.score===null?'unavailable':w.score.toFixed(6)} | quality: ${w.quality}`;};
}
select.onchange=draw;draw();
</script></html>'''
    output = template.replace('__TITLE__', html.escape(title)).replace('__NOTE__', html.escape(note)).replace('__DATA__', payload)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output)
