"""Real shared renderer in a DOM model, no model/provider/device calls."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BulletinVibeCastRendererTests(unittest.TestCase):
    def test_closed_news_sources_original_deadline_and_readonly_projection(self):
        from tests.test_bulletin_intake import NOW, rss
        from custom_components.djconnect.bulletin_intake import SOURCES, parse_feed
        from custom_components.djconnect.bulletin_source_policy import admitted_text, source_notice
        pair = tuple(parse_feed(source, rss(source), now=NOW)[0] for source in SOURCES[:2])
        notice = source_notice(pair, 'nl')
        body = ' '.join(['synthetic'] * (60 - len(notice.split())))
        full = body + '\n\n' + notice
        full = '🎵' * (1200 - len(full)) + full
        self.assertTrue(admitted_text(full, pair, 'nl'))
        self.assertEqual(len(full), 1200)
        script = r'''
import assert from 'node:assert/strict'; import fs from 'node:fs'; import vm from 'node:vm';
const source=fs.readFileSync(SOURCE,'utf8');
let now=Date.now(); class ClockDate extends Date { static now(){return now;} }
const stamp=new Date(now).toISOString(), expiry=new Date(now+45000).toISOString();
const sources=[
 {provider:'CBS',title:'Synthetic statistics publication',url:'https://www.cbs.nl/synthetic',license:'CC-BY-4.0',published_at:new Date(now-1000).toISOString()},
 {provider:'KNMI',title:'Synthetic weather research',url:'https://www.knmi.nl/synthetic',license:'CC0-1.0',published_at:new Date(now-2000).toISOString()}];
const labels={en:'DJ Bulletin',nl:'DJ Bulletin',de:'DJ-Bulletin',fr:'Bulletin du DJ',es:'Boletín del DJ'};
const run=(citations=sources,{locale='nl',type='dj_bulletin',deadline=expiry,qualified=true,admitted=true,created=stamp,body='Synthetic supported bulletin. Source adaptation notice.'}={})=>{
 const make=()=>({textContent:'',hidden:false,children:[],setAttribute:()=>{},removeAttribute:()=>{},addEventListener:()=>{},
  get firstChild(){return this.children[0] || null},removeChild(c){this.children.splice(this.children.indexOf(c),1)},appendChild(c){this.children.push(c)}});
 const elements=new Map();
 for(const id of ['spotify-source','moment-source','moment-research-sources','moment-type','moment-detail','clock','end-session','up-next','next-art','next-label','next-title','next-artist','state','artwork-card','artwork','mood','title','artist','moment','progress','album','time'])elements.set(id,make());
 const listeners=new Map(),sockets=[];class WS{constructor(){sockets.push(this)}close(){}}
 const context={URL,URLSearchParams,JSON,Math,Number,Array,Object,String,Set,Date:ClockDate,encodeURIComponent,navigator:{language:locale},
  document:{createElement:make,body:{classList:{toggle:()=>{}}},documentElement:{style:{setProperty:()=>{}}},querySelector:()=>null,getElementById:id=>elements.get(id)},
  window:{location:{protocol:'https:',host:'receiver.test',search:'?session_id=s&broadcast_token=t'},setTimeout:()=>1,clearTimeout:()=>{},addEventListener:(n,f)=>listeners.set(n,f)},WebSocket:WS};
 vm.runInNewContext(source,context);
 sockets[0].onmessage({data:JSON.stringify({type:'snapshot',snapshot:{session:{session_id:'s',locale},playback:{item_id:'item'},
  native_delivery:{admissions:admitted ? [{moment_id:'news',qualification:qualified?'qualified':'expired',current_display_allowed:true,display_expires_at:deadline}] : []},
  dj_moments:[{moment_id:'news',type,created_at:created,content:body,playback_item_id:'item',sources:citations,
   presentation_intent:{maximum_duration_seconds:60}}]}})});
 elements.event=(sequence,native)=>sockets[0].onmessage({data:JSON.stringify({type:'event',data:{session_id:'s',
  event_type:'session_flow_updated',delivery_sequence:sequence,payload:{native_delivery:native}}})});
 return elements;
};
for(const [locale,label] of Object.entries(labels)){
 const e=run(sources,{locale});assert.match(e.get('moment-detail').textContent,/Source adaptation notice/);
 assert.equal(e.get('moment-type').textContent,label);const links=e.get('moment-research-sources').children;
 assert.equal(links.length,2);assert.deepEqual(links.map(x=>x.href),sources.map(x=>x.url));
 assert(links.every(x=>x.rel==='noopener noreferrer'));
}
for(const [provider,url,license] of [['NASA','https://science.nasa.gov/synthetic','NASA-media-guidelines'],
 ['European Environment Agency','https://www.eea.europa.eu/synthetic','CC-BY-4.0'],['Eurostat','https://ec.europa.eu/synthetic','CC-BY-4.0']]){
 assert.notEqual(run([sources[0],{...sources[1],provider,url,license}]).get('moment-detail').textContent,'');
}
const unicode=UNICODE_BODY;
assert.equal(run(sources,{body:unicode}).get('moment-detail').textContent,unicode,'full actual admitted notice and astral text must survive');
assert.equal(run(sources,{body:unicode+'x'}).get('moment-detail').textContent,'','over1200codepoints must fail closed');
const withdrawing=run();
withdrawing.event(3,{admissions:[]});assert.equal(withdrawing.get('moment-detail').textContent,'');
withdrawing.event(2,{admissions:[{moment_id:'news',qualification:'qualified',current_display_allowed:true,display_expires_at:expiry}]});
assert.equal(withdrawing.get('moment-detail').textContent,'','older delivery cannot revive withdrawn authority');
const rejected=[[],[sources[0]],[sources[0],sources[0]],sources.concat(sources[0]),
 [sources[0],{...sources[0],url:'https://www.cbs.nl/another'}],
 [sources[0],{...sources[1],provider:'Invented'}],[sources[0],{...sources[1],provider:'toString'}],
 [sources[0],{...sources[1],url:'https://www.knmi.nl.evil.test/synthetic'}],
 [sources[0],{...sources[1],url:'javascript:alert(1)'}],
 [sources[0],{...sources[1],url:'https://secret@www.knmi.nl/synthetic'}],
 [sources[0],{...sources[1],license:'invented'}],[sources[0],{...sources[1],published_at:'invalid'}],
 [sources[0],{...sources[1],published_at:new Date(now+1).toISOString()}],
 [sources[0],{...sources[1],published_at:new Date(now-1800000).toISOString()}],
 [sources[0],{...sources[1],revision_url:'https://www.knmi.nl/invented'}]];
for(const citations of rejected)assert.equal(run(citations).get('moment-detail').textContent,'');
for(const options of [{deadline:''},{deadline:stamp},{admitted:false},{qualified:false},{created:''},{type:'track'}])
 assert.equal(run(sources,options).get('moment-detail').textContent,'');
// A new receiver/reconnect uses the original absolute expiry; no renewed lease.
now+=45001;assert.equal(run().get('moment-detail').textContent,'');
console.log(JSON.stringify({languages:5,publisher_positives:5,negative_cases:rejected.length+6,reconnect_expiry:'PASS'}));
'''.replace('SOURCE', json.dumps(str(ROOT / 'custom_components/djconnect/vibecast_renderer/renderer.js')), 1)
        script = script.replace('UNICODE_BODY', json.dumps(full))
        result = subprocess.run([shutil.which('node'), '--input-type=module', '-e', script],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
