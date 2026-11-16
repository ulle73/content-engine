import { workflow, node, trigger, expr } from '@n8n/workflow-sdk';

// Bevakar Drive-mappen VIDEOS (och dess undermappar GOLFKUPONGER/VIDEOS, /BILDER, FAIV …) var 5:e minut.
// Varje ny fil som Jonas lägger dit ger en notis i Discord #google-drive: "Ny video i drive: {url}".
// Sedda filer sparas i flödets statiska data; första körningen sparar bara det som redan finns (inga notiser).

const tick = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.2,
  config: { name: 'Var 5:e minut', parameters: { rule: { interval: [{ field: 'minutes', minutesInterval: 5 }] } } }
});

const folders = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.2,
  config: {
    name: 'Undermappar',
    parameters: {
      method: 'GET',
      url: 'https://www.googleapis.com/drive/v3/files',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'googleOAuth2Api',
      sendQuery: true,
      specifyQuery: 'keypair',
      queryParameters: { parameters: [
        { name: 'q', value: "('1wz8nL1n4fmnr3FHE6FHSXOdPJD8Y-86n' in parents or '1ameN95XSS1ZWJl3LXsX-9Nt8vaQAwU6y' in parents or '1MOqdtAekZRQ0W_-H3EdSlz7xtpPYnhSh' in parents or '15W0ueU_plehKIe4mrpsz6EHFiGi5u-Gs' in parents or '17eeBoQ3MIHKO2jS_y5gaZJrFvz8nQLFA' in parents) and mimeType = 'application/vnd.google-apps.folder' and trashed = false" },
        { name: 'fields', value: 'files(id,name)' },
        { name: 'pageSize', value: '1000' },
        { name: 'supportsAllDrives', value: 'true' },
        { name: 'includeItemsFromAllDrives', value: 'true' }
      ] },
      options: { timeout: 30000 }
    },
    credentials: { googleOAuth2Api: { id: 'g8EblI0kkFxkuMNA', name: 'Google account' } }
  },
  output: [{ files: [{ id: '1MOqdtAekZRQ0W_-H3EdSlz7xtpPYnhSh', name: 'VIDEOS' }] }]
});

const query = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Alla mappar',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `const fasta = ['1wz8nL1n4fmnr3FHE6FHSXOdPJD8Y-86n', '1ameN95XSS1ZWJl3LXsX-9Nt8vaQAwU6y', '1MOqdtAekZRQ0W_-H3EdSlz7xtpPYnhSh', '15W0ueU_plehKIe4mrpsz6EHFiGi5u-Gs', '17eeBoQ3MIHKO2jS_y5gaZJrFvz8nQLFA'];
// Råmaterial (t.ex. material-for-videos) är inte färdiga filer: ingen notis därifrån.
const under = ($input.first().json.files || []).filter((f) => !/material/i.test(f.name)).map((f) => f.id);
const ids = [...new Set([...fasta, ...under])];
return [{ json: { q: '(' + ids.map((id) => "'" + id + "' in parents").join(' or ') + ") and mimeType != 'application/vnd.google-apps.folder' and trashed = false", mappar: ids.length } }];`
    }
  },
  output: [{ q: "('1MOqdtAekZRQ0W_-H3EdSlz7xtpPYnhSh' in parents) and mimeType != 'application/vnd.google-apps.folder' and trashed = false", mappar: 5 }]
});

const list = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.2,
  config: {
    name: 'Filer i mapparna',
    parameters: {
      method: 'GET',
      url: 'https://www.googleapis.com/drive/v3/files',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'googleOAuth2Api',
      sendQuery: true,
      specifyQuery: 'keypair',
      queryParameters: { parameters: [
        { name: 'q', value: expr('{{ $json.q }}') },
        { name: 'fields', value: 'nextPageToken,files(id,name,mimeType,webViewLink,parents)' },
        { name: 'pageSize', value: '1000' },
        { name: 'supportsAllDrives', value: 'true' },
        { name: 'includeItemsFromAllDrives', value: 'true' }
      ] },
      options: {
        timeout: 30000,
        // Över 1000 filer: läs alla sidor (en utdatapost per sida).
        pagination: { pagination: {
          paginationMode: 'updateAParameterInEachRequest',
          parameters: { parameters: [{ type: 'qs', name: 'pageToken', value: '={{ $response.body.nextPageToken }}' }] },
          paginationCompleteWhen: 'other',
          completeExpression: '={{ !$response.body.nextPageToken }}',
          limitPagesFetched: true,
          maxRequests: 20
        } }
      }
    },
    credentials: { googleOAuth2Api: { id: 'g8EblI0kkFxkuMNA', name: 'Google account' } }
  },
  output: [{ files: [{ id: '1abc', name: 'T01_format_B1-slam_sthlm.mp4', mimeType: 'video/mp4', webViewLink: 'https://drive.google.com/file/d/1abc/view', parents: ['1MOqdtAekZRQ0W_-H3EdSlz7xtpPYnhSh'] }] }]
});

const fresh = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Nya filer',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `// Sedda fil-id sparas mellan körningar (bara i aktiva körningar, inte provkörningar i editorn).
// OBS: statisk data sparas bara om HELA körningen lyckas. Därför får notisdelen aldrig bli lång
// (förr: 150 filer x 1,5 s > 120 s-gränsen -> avbrott -> samma notiser igen var 5:e minut).
const s = $getWorkflowStaticData('global');
const files = $input.all().flatMap((i) => i.json.files || []);
// Tom lista = mappen syns inte (ej delad) eller tillfälligt fel: ändra inget.
if (!files.length) return [];
const seen = s.seen && Object.keys(s.seen).length ? s.seen : null;
const now = new Date().toISOString();
const nya = seen ? files.filter((f) => !seen[f.id]) : [];
// Behåll redan sedda id även om de saknas i just den här listningen, så att en ofullständig listning inte ger dubbletter senare.
const next = Object.assign({}, seen || {});
for (const f of files) if (!next[f.id]) next[f.id] = now;
s.seen = next;
if (!nya.length) return [];
const typ = (f) => { const m = String(f.mimeType || ''); return m.startsWith('video/') ? 'video' : m.startsWith('image/') ? 'bild' : 'fil'; };
const ikon = { video: '🎬', bild: '🖼️', fil: '📄' };
const lank = (f) => f.webViewLink || 'https://drive.google.com/file/d/' + f.id + '/view';
// Få filer: en notis per fil, som förut.
if (nya.length <= 3) return nya.map((f) => ({ json: { id: f.id, namn: f.name, content: ikon[typ(f)] + ' Ny ' + typ(f) + ' i drive: ' + lank(f) } }));
// Många filer på en gång: EN sammanfattning per mapp.
let mappnamn = {};
try { for (const m of $('Undermappar').first().json.files || []) mappnamn[m.id] = m.name; } catch (e) {}
const plural = { video: ['video', 'videor'], bild: ['bild', 'bilder'], fil: ['fil', 'filer'] };
const grupper = {};
for (const f of nya) { const p = (f.parents && f.parents[0]) || '?'; (grupper[p] = grupper[p] || { video: 0, bild: 0, fil: 0 })[typ(f)]++; }
const rader = Object.entries(grupper).map(([id, n]) => {
  const delar = ['bild', 'video', 'fil'].filter((t) => n[t]).map((t) => n[t] + ' ' + plural[t][n[t] === 1 ? 0 : 1]).join(', ');
  return '• ' + (mappnamn[id] || 'Huvudmappen') + ' – ' + delar + (id !== '?' ? ': <https://drive.google.com/drive/folders/' + id + '>' : '');
});
let content = '📦 ' + nya.length + ' nya filer i drive:\\n' + rader.join('\\n');
if (content.length > 1900) content = content.slice(0, 1880) + '\\n…';
return [{ json: { antal: nya.length, content } }];`
    }
  },
  output: [{ id: '1abc', namn: 'T01_format_B1-slam_sthlm.mp4', content: 'Ny video i drive: https://drive.google.com/file/d/1abc/view' }]
});

const post = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.2,
  config: {
    name: 'Notis i #google-drive',
    parameters: {
      method: 'POST',
      url: 'https://discord.com/api/v10/channels/1563325547407347773/messages',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'discordBotApi',
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ content: $json.content, allowed_mentions: { parse: [] } }) }}'),
      options: { timeout: 30000, batching: { batch: { batchSize: 1, batchInterval: 1500 } } }
    },
    credentials: { discordBotApi: { id: 'dnjEdT1ZwTX4J7MJ', name: 'Content Engine Discord Bot' } },
    retryOnFail: true,
    maxTries: 3,
    waitBetweenTries: 3000
  },
  output: [{ id: '123', channel_id: '1563325547407347773' }]
});

export default workflow('ce-drive-notis', 'CE – Ny fil i Drive → Discord')
  .add(tick)
  .to(folders)
  .to(query)
  .to(list)
  .to(fresh)
  .to(post);
