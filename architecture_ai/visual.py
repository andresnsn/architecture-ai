"""Offline overview from model claims, with explicit evidence warnings."""
import html
import json
from pathlib import Path
from architecture_ai.analyzer import _audit_citations


def build_visual(result, repositories, source_records, path):
    components = {item['name']: item for item in result.get('components', []) if isinstance(item, dict) and item.get('name')}
    names = [p.name for p in repositories]
    # A model-proposed component must not silently replace an input repository.
    nodes = []
    for name in names:
        entry = components.get(name, {})
        ev = entry.get('evidence', [])
        warnings = _audit_citations({'components': [entry], 'relationships': []}, source_records) if entry else []
        ok = bool(ev) and not warnings
        nodes.append({'name': name, 'responsibility': entry.get('responsibility', 'Responsabilidade não identificada') if ok else 'Responsabilidade não comprovada; consulte a análise.',
                      'certainty': entry.get('certainty', 'unknown') if ok else 'unknown',
                      'evidence': ev if ok else [], 'interfaces': [
                          {'protocol': interface.get('protocol', '?'), 'operation': interface.get('operation', '?'),
                           'certainty': interface.get('certainty', 'unknown'), 'evidence': interface.get('evidence', [])}
                          for interface in entry.get('interfaces', []) if isinstance(interface, dict) and interface.get('evidence')
                          and not _audit_citations({'components': [], 'relationships': [interface]}, source_records)
                      ]})
    relations = []
    for rel in result.get('relationships', []):
        if not isinstance(rel, dict) or rel.get('source') not in names:
            continue
        evidence = rel.get('evidence', [])
        warnings = _audit_citations({'components': [], 'relationships': [rel]}, source_records)
        if not evidence or warnings:
            continue
        relations.append({'source': rel.get('source'), 'target': rel.get('target') or 'Destino desconhecido',
                          'protocol': rel.get('protocol', '?'), 'operation': rel.get('operation', ''),
                          'certainty': rel.get('certainty', 'unknown'), 'evidence': evidence})
    for relation in relations:
        target = relation['target']
        if target not in {node['name'] for node in nodes}:
            nodes.append({'name': target, 'responsibility': 'Destino externo ou não identificado entre os repositórios analisados.',
                          'certainty': 'unknown', 'evidence': [], 'interfaces': []})
    data = json.dumps({'nodes': nodes, 'relations': relations, 'unknowns': result.get('unknowns', [])}, ensure_ascii=False).replace('<', '\\u003c')
    template = '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture AI</title><style>
:root{color-scheme:light;font:15px system-ui,sans-serif;color:#18304c;background:#f3f6fb}body{margin:0}header{background:#132c4b;color:white;padding:30px max(5vw,25px)}header p{color:#b7cee8}main{max-width:1200px;margin:auto;padding:28px}.notice{background:#fff7de;border-left:4px solid #d39423;padding:14px;border-radius:5px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}.card,.edge{background:white;border:1px solid #d7e1ed;border-radius:12px;padding:18px;box-shadow:0 4px 15px #17365b0d}.card h3{margin:0 0 10px}.badge{display:inline-block;background:#e9f2ff;color:#225386;border-radius:15px;padding:4px 9px;font-size:12px}.edge{margin:10px 0;display:flex;gap:12px;flex-wrap:wrap;align-items:center}.arrow{font-size:22px;color:#3e77b1}.uncertain{border-left:4px dashed #c18424}.sources{font-size:12px;color:#49647e;margin-top:10px;overflow-wrap:anywhere}code{white-space:pre-wrap}h2{margin-top:36px}footer{color:#647b91;margin-top:30px}svg{width:100%;min-height:160px;background:white;border:1px solid #d7e1ed;border-radius:12px}text{font-family:system-ui,sans-serif}</style></head><body><header><h1>Architecture AI</h1><p>Visão dos repositórios e evidências disponíveis</p></header><main><p class="notice">Relações são hipóteses baseadas no material analisado. Uma citação existente não garante que ela prove a conclusão; revise o código. Ausência de ligação não prova que ela não exista.</p><h2>Diagrama</h2><svg id="graph" role="img" aria-label="Diagrama de aplicações e relações"></svg><h2>Aplicações</h2><div id="nodes" class="grid"></div><h2>Comunicações encontradas</h2><div id="edges"></div><h2>Informações desconhecidas</h2><ul id="unknowns"></ul><footer>Gerado localmente a partir das evidências fornecidas ao modelo.</footer></main><script>
const data=__DATA__;const label=x=>({confirmed:'confirmado',inferred:'inferido',unknown:'desconhecido'}[x]||'desconhecido');const $=id=>document.getElementById(id);function el(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e}function sources(parent,items){if(!items.length)return;let d=el('div',null,'sources');d.append(el('strong','Evidências: '));items.forEach(x=>{let p=el('div',`${x.repository}/${x.file}:${x.line} — ${x.snippet}`);d.append(p)});parent.append(d)}
for(const n of data.nodes){const d=el('article',null,'card');d.append(el('h3',n.name),el('span',label(n.certainty),'badge'),el('p',n.responsibility));if(n.interfaces&&n.interfaces.length){const list=el('ul');for(const x of n.interfaces){const item=el('li',`${x.protocol} ${x.operation} (${label(x.certainty)})`);sources(item,x.evidence);list.append(item)}d.append(list)}sources(d,n.evidence);$('nodes').append(d)}
for(const x of data.relations){const d=el('article',null,'edge '+(x.certainty==='confirmed'?'':'uncertain'));d.append(el('strong',x.source),el('span','→','arrow'),el('strong',x.target),el('span',`${x.protocol} ${x.operation} • ${label(x.certainty)}`,'badge'));sources(d,x.evidence);$('edges').append(d)}if(!data.relations.length)$('edges').append(el('p','Nenhuma relação com citação verificável foi identificada.'));
for(const u of data.unknowns)$('unknowns').append(el('li',String(u)));
const svg=$('graph'),ns='http://www.w3.org/2000/svg';function shape(tag,attrs,text){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text)e.textContent=text;svg.append(e)}shape('defs',{},'');const defs=svg.querySelector('defs');defs.innerHTML='<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#4c7ba8"/></marker>';const W=1000,H=Math.max(180,data.nodes.length*125+40);svg.setAttribute('viewBox',`0 0 ${W} ${H}`);const positions={};data.nodes.forEach((n,i)=>{const y=30+i*125;positions[n.name]=y;shape('rect',{x:30,y,width:270,height:70,rx:10,fill:'#eef5fd',stroke:'#7e9fbe'});shape('text',{x:45,y:y+30,fill:'#163553','font-size':15,'font-weight':700},n.name);shape('text',{x:45,y:y+51,fill:'#536c84','font-size':12},label(n.certainty))});data.relations.forEach((r,i)=>{const y=positions[r.source];if(y===undefined)return;const target=positions[r.target];const y2=target===undefined?y+35:target+35;const xx=340+i*20;shape('path',{d:`M 300 ${y+35} H ${xx} V ${y2} H ${target===undefined?xx+30:300}`,fill:'none',stroke:'#4c7ba8','stroke-width':2,'marker-end':'url(#arrow)','stroke-dasharray':r.certainty==='confirmed'?'':'6 4'});shape('text',{x:Math.min(xx+40,510),y:y+22+i*15,fill:'#274b70','font-size':12},`→ ${r.target} · ${r.protocol} ${r.operation}`)});
</script></body></html>'''
    path.write_text(template.replace('__DATA__', data), encoding='utf-8')
    return path
