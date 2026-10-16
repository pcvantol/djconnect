// Independent WHATWG-URL consumer check. No network or live authority.
import fs from 'node:fs';
const file = new URL('../../examples/client_contracts/vibecast_display_admission_v1/route-cases.json', import.meta.url);
const corpus = JSON.parse(fs.readFileSync(file, 'utf8'));
const reserved = new Set(['local','localhost','internal','invalid','test','example','lan','home','onion','arpa']);
function canonicalOrigin(value) {
  if (typeof value !== 'string' || !value.length || value.length > 2048 || /[^\x21-\x7e]|[%\\?#@]/.test(value)) return null;
  try {
    const url = new URL(value);
    const host = url.hostname;
    const labels = host.split('.');
    if (url.protocol !== 'https:' || url.username || url.password || url.port || host.length > 253 || labels.length < 2 || reserved.has(labels.at(-1))) return null;
    if (!labels.every(label => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label))) return null;
    if (!/^(?:[a-z]{2,63}|xn--[a-z0-9-]+)$/.test(labels.at(-1))) return null;
    const origin = 'https://' + host;
    const authority = value.slice('https://'.length).split('/')[0];
    return authority === host && url.origin === origin ? origin : null;
  } catch { return null; }
}
function allowed(value, selected) {
  const origin = canonicalOrigin(selected);
  return origin !== null && selected === origin && canonicalOrigin(value) === origin && value === origin + '/djconnect/vibecast/display';
}
if (corpus.status !== 'REVIEW_CANDIDATE_NOT_FROZEN') throw new Error('unexpected review status');
for (const c of corpus.cases) if (allowed(c.entry_url,c.selected_origin) !== c.allowed) throw new Error(c.id);
process.stdout.write(JSON.stringify({result:'PASS_WHATWG_LEXICAL_CORPUS_ONLY',cases:corpus.cases.length,network_fetches:false})+'\n');
