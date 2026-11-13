import { workflow, node, trigger, expr } from '@n8n/workflow-sdk';

// Claudes verktyg: lägger en färdig fil i en Drive-mapp (t.ex. GOLFKUPONGER/VIDEOS/golfare-i-malmo) när Jonas ber om det.
// Ingen egen notis – "CE – Ny fil i Drive → Discord" ser filen och postar i #google-drive.
//
// 2026-11-05: filen passerar INTE längre n8n. Webhooken tar emot liten JSON {mapp, namn, mime, storlek},
// skapar en Drive resumable-session med n8n:s Google-inloggning och svarar med upload_url.
// Anroparen (scripts/drive_upload.py) PUT:ar filen direkt till Google – ingen OAuth-token behövs för det steget.
// Bakgrund: den gamla multipart-webhooken (content-engine-drive-upload) lämnade varje fil kvar som
// sourceId='temp' i PostgreSQL-tabellen binary_data (62 videor = 519 MB den 5 november).
// Ny sökväg så att gamla multipart-anrop får 404 i stället för att lagra filer.
// Lagringsinställningar enligt policyn i Notion; error=none eftersom headern innehåller nyckeln.

const hook = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'Begär uppladdning',
    parameters: { httpMethod: 'POST', path: 'content-engine-drive-session', responseMode: 'responseNode', options: {} }
  },
  output: [{ headers: { 'x-gk-drive': 'nyckel' }, body: { mapp: '1d4KZvNndRZYg6ieKmExmecSW4dSjccIE', namn: 'golfare-i-malmo_B1-slam.mp4', mime: 'video/mp4', storlek: 12000000 } }]
});

const hash = node({
  type: 'n8n-nodes-base.crypto',
  version: 2,
  config: {
    name: 'Hasha nyckeln',
    parameters: { action: 'hash', type: 'SHA256', value: expr("{{ $json.headers['x-gk-drive'] || '' }}"), dataPropertyName: 'nyckel_hash', encoding: 'hex' }
  },
  output: [{ nyckel_hash: '542a9c0f670a8fc2102887d96466fcfcf7faaab1daf00572d5ef84b4ef970c85' }]
});

const check = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Kontrollera',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `if ($input.first().json.nyckel_hash !== '542a9c0f670a8fc2102887d96466fcfcf7faaab1daf00572d5ef84b4ef970c85') throw new Error('Fel nyckel.');
const hook = $('Begär uppladdning').first();
if (hook.binary && Object.keys(hook.binary).length) throw new Error('Skicka ingen fil hit. Skicka JSON och PUT:a filen direkt till upload_url.');
const b = hook.json.body || {};
const mapp = String(b.mapp || '');
if (!/^[A-Za-z0-9_-]{20,60}$/.test(mapp)) throw new Error('mapp ska vara ett Drive-id.');
const namn = String(b.namn || '').trim();
if (!namn || namn.length > 200 || /[\\\\/]/.test(namn)) throw new Error('namn saknas eller är ogiltigt.');
const mime = String(b.mime || 'application/octet-stream');
if (!/^[a-z]+\\/[A-Za-z0-9.+-]+$/.test(mime)) throw new Error('mime är ogiltig.');
const MAX_BYTES = 2 * 1024 * 1024 * 1024; // 2 GiB per fil
const storlek = Number(b.storlek);
if (!Number.isInteger(storlek) || storlek < 1 || storlek > MAX_BYTES) throw new Error('storlek (byte) saknas eller överstiger 2 GiB.');
return [{ json: { mapp, namn, mime, storlek } }];`
    }
  },
  output: [{ mapp: '1d4KZvNndRZYg6ieKmExmecSW4dSjccIE', namn: 'golfare-i-malmo_B1-slam.mp4', mime: 'video/mp4', storlek: 12000000 }]
});

const start = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.2,
  config: {
    name: 'Starta uppladdning',
    parameters: {
      method: 'POST',
      url: 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'googleOAuth2Api',
      sendHeaders: true,
      specifyHeaders: 'keypair',
      headerParameters: { parameters: [
        { name: 'X-Upload-Content-Type', value: expr('{{ $json.mime }}') },
        { name: 'X-Upload-Content-Length', value: expr('{{ String($json.storlek) }}') }
      ] },
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ name: $json.namn, parents: [$json.mapp] }) }}'),
      options: { timeout: 30000, response: { response: { fullResponse: true } } }
    },
    credentials: { googleOAuth2Api: { id: 'g8EblI0kkFxkuMNA', name: 'Google account' } }
  },
  output: [{ headers: { location: 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=x' } }]
});

const session = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Sessionsadress',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `const location = ($input.first().json.headers || {}).location;
if (!location || !String(location).startsWith('https://www.googleapis.com/upload/drive/')) throw new Error('Drive gav ingen uppladdningsadress.');
const k = $('Kontrollera').first().json;
return [{ json: { upload_url: String(location), namn: k.namn, mapp: k.mapp, storlek: k.storlek, giltig_till: new Date(Date.now() + 6 * 24 * 3600 * 1000).toISOString() } }];`
    }
  },
  output: [{ upload_url: 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=x', namn: 'golfare-i-malmo_B1-slam.mp4', mapp: '1d4KZvNndRZYg6ieKmExmecSW4dSjccIE', storlek: 12000000 }]
});

const done = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Svar',
    parameters: {
      respondWith: 'json',
      responseBody: expr("{{ { upload_url: $json.upload_url, namn: $json.namn, mapp: $json.mapp, storlek: $json.storlek, giltig_till: $json.giltig_till, instruktion: 'PUT filens bytes till upload_url med Content-Length. Svaret innehåller id; länk: https://drive.google.com/file/d/<id>/view' } }}"),
      options: { responseCode: 200 }
    }
  }
});

export default workflow('ce-drive-upload', 'CE – Uppladdning till Drive (Claude)', {
  settings: {
    saveDataSuccessExecution: 'none',
    saveDataErrorExecution: 'none',
    saveManualExecutions: false,
    saveExecutionProgress: false,
    errorWorkflow: '64S3vgFFDl7a2yHT',
    executionTimeout: 60,
    timezone: 'Europe/Stockholm'
  }
})
  .add(hook)
  .to(hash)
  .to(check)
  .to(start)
  .to(session)
  .to(done);
