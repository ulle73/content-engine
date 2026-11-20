import { workflow, node, trigger, ifElse, expr } from '@n8n/workflow-sdk';

// Content Engine "Radera" (engine/smsfilm/radera.py): lägger en publicerad fil i Drives papperskorg.
// Bara filer som ligger direkt i CONTENT/01 Publicerat (samma fasta mapp som "CE – Publicera till CONTENT") rörs.
// Papperskorgen går att återställa i 30 dagar; inget raderas permanent härifrån.
// En fil som redan är borta (404) eller redan ligger i papperskorgen räknas som klar. En fil som flyttats ut ur
// CONTENT/01 rörs inte; svaret blir resultat 'flyttad'.
// Lagringsinställningar enligt policyn i Notion; error=none eftersom headern innehåller nyckeln.

const MAPP = '1Hvtqmycw5X93UZjI1yQCehSsG_2GWjwY';

const hook = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'Begär papperskorg',
    parameters: { httpMethod: 'POST', path: 'content-engine-papperskorg', responseMode: 'responseNode', options: {} }
  },
  output: [{ headers: { 'x-gk-drive': 'nyckel' }, body: { drive_id: '1AbCdEfGhIjKlMnOpQrStUvWxYz012345' } }]
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
const b = $('Begär papperskorg').first().json.body || {};
const id = String(b.drive_id || '');
if (!/^[A-Za-z0-9_-]{20,80}$/.test(id)) throw new Error('drive_id ska vara ett Drive-id.');
return [{ json: { drive_id: id } }];`
    }
  },
  output: [{ drive_id: '1AbCdEfGhIjKlMnOpQrStUvWxYz012345' }]
});

const hamta = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.2,
  config: {
    name: 'Hämta filen',
    parameters: {
      method: 'GET',
      url: expr('{{ "https://www.googleapis.com/drive/v3/files/" + $json.drive_id + "?fields=id,name,parents,trashed&supportsAllDrives=true" }}'),
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'googleOAuth2Api',
      options: { timeout: 30000, response: { response: { fullResponse: true, neverError: true } } }
    },
    credentials: { googleOAuth2Api: { id: 'g8EblI0kkFxkuMNA', name: 'Google account' } }
  },
  output: [{ statusCode: 200, body: { id: '1AbCdEfGhIjKlMnOpQrStUvWxYz012345', name: 'x.jpg', parents: [MAPP], trashed: false } }]
});

const bedom = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Bedöm',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `const r = $input.first().json;
const id = $('Kontrollera').first().json.drive_id;
const kod = Number(r.statusCode);
if (kod === 404) return [{ json: { drive_id: id, atgard: false, resultat: 'saknas' } }];
if (kod !== 200) throw new Error('Drive svarade ' + kod + ' när filen hämtades.');
const f = r.body || {};
// En fil som flyttats från CONTENT/01 Publicerat har flyttats med avsikt och rörs aldrig härifrån.
if (!(f.parents || []).includes('${MAPP}')) return [{ json: { drive_id: id, atgard: false, resultat: 'flyttad' } }];
if (f.trashed) return [{ json: { drive_id: id, atgard: false, resultat: 'redan_i_papperskorgen' } }];
return [{ json: { drive_id: id, atgard: true, resultat: 'papperskorg' } }];`
    }
  },
  output: [{ drive_id: '1AbCdEfGhIjKlMnOpQrStUvWxYz012345', atgard: true, resultat: 'papperskorg' }]
});

const behover = ifElse({
  version: 2.2,
  config: {
    name: 'Behöver flyttas?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
        conditions: [{ leftValue: expr('{{ $json.atgard }}'), operator: { type: 'boolean', operation: 'true', singleValue: true } }],
        combinator: 'and'
      }
    }
  }
});

const papperskorg = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.2,
  config: {
    name: 'Lägg i papperskorgen',
    parameters: {
      method: 'PATCH',
      url: expr('{{ "https://www.googleapis.com/drive/v3/files/" + $json.drive_id + "?supportsAllDrives=true&fields=id,trashed" }}'),
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'googleOAuth2Api',
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: '{"trashed": true}',
      options: { timeout: 30000 }
    },
    credentials: { googleOAuth2Api: { id: 'g8EblI0kkFxkuMNA', name: 'Google account' } }
  },
  output: [{ id: '1AbCdEfGhIjKlMnOpQrStUvWxYz012345', trashed: true }]
});

const svarKlar = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Svar flyttad',
    parameters: {
      respondWith: 'json',
      responseBody: expr("{{ { ok: $json.trashed === true, drive_id: $json.id, resultat: 'papperskorg' } }}"),
      options: { responseCode: 200 }
    }
  }
});

const svarRedan = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Svar redan borta',
    parameters: {
      respondWith: 'json',
      responseBody: expr('{{ { ok: true, drive_id: $json.drive_id, resultat: $json.resultat } }}'),
      options: { responseCode: 200 }
    }
  }
});

export default workflow('ce-drive-papperskorg', 'CE – Papperskorg i CONTENT', {
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
  .to(hamta)
  .to(bedom)
  .to(behover.onTrue(papperskorg.to(svarKlar)).onFalse(svarRedan));
