/* No provider calls: browser previews use the shared server-side compiler. */
(() => {
  'use strict';
  const form = document.getElementById('creator-form');
  if (!form) return;
  const catalog = JSON.parse(document.getElementById('creator-catalog').textContent);
  const field = name => form.elements.namedItem(name);
  const value = name => field(name)?.value || '';
  const storageKey = `ce:creator:v1:${form.dataset.stateKey}`;
  const status = document.getElementById('creator-plan-status');
  const prompt = document.getElementById('creator-compiled-prompt');
  const promptDetails = document.getElementById('creator-prompt-details');
  const picker = document.getElementById('creator-reference-picker');
  const pickerStatus = document.getElementById('creator-picker-status');
  const grid = document.getElementById('creator-reference-grid');
  const search = document.getElementById('creator-search');
  const more = document.getElementById('creator-more');
  const submit = document.getElementById('creator-submit');
  let timer, searchTimer, planController, assetController, frameRole, opener, nextPage, uploading = false;
  let requestNumber = 0;
  const currentKind = form.dataset.kind;
  const fields = [...form.querySelectorAll('[data-creator-field]')];
  form.classList.add('creator-enhanced');
  // The no-JavaScript select is server-filtered for current references; dynamic
  // editing may unlock other verified choices when references change.
  catalog.models.forEach(model => {
    const select = field('model_override');
    if (![...select.options].some(o => o.value === model.id)) select.add(new Option(model.label, model.id));
  });

  function remember() {
    try {
      const previous = JSON.parse(sessionStorage.getItem(storageKey) || '{}');
      const values = {...previous.values};
      fields.forEach(el => { values[el.name] = el.type === 'checkbox' ? el.checked : el.value; });
      sessionStorage.setItem(storageKey, JSON.stringify({kind: currentKind, values}));
    } catch (_) { /* Private mode/storage limits must not break creation. */ }
  }
  if (form.dataset.restore === 'true') {
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey) || '{}');
      const params = new URLSearchParams(location.search);
      fields.forEach(el => {
        if (!(el.name in (saved.values || {}))) return;
        if (el.name === 'source_asset' && params.has('source')) return;
        if (el.name === 'end_asset' && params.has('end_source')) return;
        if (el.name === 'model_override' && saved.kind !== currentKind) return;
        const restored = saved.values[el.name];
        if (el.name === 'model_override' && restored && ![...el.options].some(o => o.value === restored)) {
          el.add(new Option(`${restored} (inte tillg\u00e4nglig)`, restored));
        }
        if (el.type === 'checkbox') el.checked = restored === true;
        else if (el.tagName !== 'SELECT' || [...el.options].some(o => o.value === restored)) el.value = restored;
      });
    } catch (_) { /* The server-rendered form remains usable. */ }
  }

  function assetUrl(id) {
    return /^[0-9a-f-]{36}$/i.test(id) ? form.dataset.assetUrl.replace('00000000-0000-0000-0000-000000000000', id) : '';
  }
  function showFrames() {
    form.querySelectorAll('[data-frame]').forEach(box => {
      const id = value(box.dataset.frame), image = box.querySelector('img');
      image.hidden = !id;
      if (id) image.src = assetUrl(id); else image.removeAttribute('src');
      box.querySelector('.creator-frame-empty').hidden = !!id;
      box.querySelector('[data-remove-frame]').hidden = !id;
      const end = box.dataset.frame === 'end_asset';
      box.querySelector('[data-open-frame]').textContent = `${id ? 'Byt' : 'V\u00e4lj'} ${end ? 'slutbild' : 'startbild'}`;
    });
    const swap = document.getElementById('creator-swap');
    if (swap) swap.hidden = !value('source_asset') || !value('end_asset');
  }
  function setFrame(role, id, label) {
    const select = field(role);
    if (!select) return;
    if (id && ![...select.options].some(o => o.value === id)) select.add(new Option(label || 'Bild', id));
    select.value = id;
    changed();
  }
  function closePicker() { picker.hidden = true; opener?.focus(); }
  form.querySelectorAll('[data-open-frame]').forEach(button => button.addEventListener('click', () => {
    frameRole = button.dataset.openFrame; opener = button;
    picker.hidden = false;
    document.getElementById('creator-picker-title').textContent = frameRole === 'end_asset' ? 'V\u00e4lj slutbild' : 'V\u00e4lj startbild';
    search.value = ''; loadAssets(); search.focus();
  }));
  form.querySelectorAll('[data-remove-frame]').forEach(button => button.addEventListener('click', () => setFrame(button.dataset.removeFrame, '')));
  document.getElementById('creator-picker-close').addEventListener('click', closePicker);
  picker.addEventListener('keydown', event => { if (event.key === 'Escape') { event.preventDefault(); closePicker(); } });
  document.getElementById('creator-swap')?.addEventListener('click', () => {
    const start = value('source_asset'), end = value('end_asset');
    const startLabel = field('source_asset').selectedOptions[0]?.textContent;
    const endLabel = field('end_asset').selectedOptions[0]?.textContent;
    setFrame('source_asset', end, endLabel); setFrame('end_asset', start, startLabel);
  });

  async function loadAssets(page = 0) {
    assetController?.abort(); assetController = new AbortController();
    pickerStatus.textContent = 'H\u00e4mtar dina bilder...'; more.disabled = true;
    const url = new URL(form.dataset.referencesUrl, location.origin);
    url.searchParams.set('q', search.value); url.searchParams.set('page', page);
    try {
      const response = await fetch(url, {signal: assetController.signal, headers: {'Accept': 'application/json'}});
      if (!response.ok) throw new Error('Bilderna kunde inte h\u00e4mtas. St\u00e4ng och \u00f6ppna bildvalet igen.');
      const data = await response.json();
      if (!page) grid.replaceChildren();
      data.assets.forEach(asset => {
        const button = document.createElement('button'); button.type = 'button';
        button.dataset.assetId = asset.id; button.title = asset.label;
        const image = document.createElement('img'); image.src = assetUrl(asset.id); image.alt = ''; image.loading = 'lazy';
        const text = document.createElement('span'); text.textContent = asset.label;
        button.append(image, text);
        button.addEventListener('click', () => { setFrame(frameRole, asset.id, asset.label); closePicker(); });
        grid.append(button);
      });
      nextPage = data.next_page; more.hidden = nextPage === null;
      pickerStatus.textContent = grid.children.length ? `${grid.children.length} bilder. V\u00e4lj en bild eller ladda upp en ny.` : 'Inga bilder matchar. Prova ett annat s\u00f6kord eller ladda upp.';
    } catch (error) { if (error.name !== 'AbortError') pickerStatus.textContent = error.message; }
    finally { more.disabled = false; }
  }
  search.addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => loadAssets(), 250); });
  search.addEventListener('keydown', event => { if (event.key === 'Enter') event.preventDefault(); });
  more.addEventListener('click', () => { if (nextPage !== null) loadAssets(nextPage); });
  document.getElementById('creator-upload').addEventListener('change', async event => {
    const file = event.target.files[0]; if (!file || uploading) return;
    if (file.size > 8 * 1024 * 1024) { pickerStatus.textContent = 'Bilden f\u00e5r vara h\u00f6gst 8 MB.'; return; }
    uploading = true; submit.disabled = true; pickerStatus.textContent = 'Laddar upp bilden...';
    const selectedRole = frameRole;
    const body = new FormData(); body.set('file', file); body.set('alt_text', file.name.slice(0, 500));
    body.set('csrfmiddlewaretoken', value('csrfmiddlewaretoken'));
    try {
      const response = await fetch(form.dataset.uploadUrl, {method: 'POST', body, headers: {'X-Creator-Upload': '1', 'Accept': 'application/json'}});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Uppladdningen misslyckades.');
      setFrame(selectedRole, data.id, data.label); closePicker();
    } catch (error) { pickerStatus.textContent = error.message || 'Uppladdningen misslyckades.'; }
    finally { uploading = false; submit.disabled = false; event.target.value = ''; }
  });

  function compatibleChoices() {
    const roles = [value('source_asset') && 'START_IMAGE', currentKind === 'video' && value('end_asset') && 'END_IMAGE'].filter(Boolean);
    const mode = currentKind === 'video' ? (roles.includes('START_IMAGE') ? 'image-to-video' : 'text-to-video') : (roles.length ? 'image-to-image' : 'text-to-image');
    const recipe = catalog.recipes.find(r => r.id === value('recipe_id'));
    const base = catalog.models.filter(m => m.mode === mode && roles.every(r => m.roles.includes(r)) && m.required.every(r => roles.includes(r)) && (!recipe || recipe.capabilities.every(c => m.capabilities.includes(c))));
    function restrict(select, allowed) {
      if (!select) return;
      [...select.options].forEach(option => {
        const valid = !option.value || option.value === 'auto' || allowed.has(option.value);
        // Never silently discard an incompatible choice. Keep it selected so the
        // authoritative server validation can explain how to resolve it.
        option.hidden = !valid && option.value !== select.value;
        option.disabled = !valid && option.value !== select.value;
      });
    }
    const duration = Number(value('duration_seconds'));
    const models = base.filter(m => (!duration || m.durations.includes(duration)) && (!value('resolution') || value('resolution') === 'auto' || m.resolutions.includes(value('resolution'))) && (value('audio') !== 'native' || m.audio));
    restrict(field('model_override'), new Set(models.map(m => m.id)));
    const chosen = value('model_override');
    const settings = chosen ? base.filter(m => m.id === chosen) : base;
    restrict(field('duration_seconds'), new Set(settings.flatMap(m => m.durations.map(String))));
    restrict(field('resolution'), new Set(settings.flatMap(m => m.resolutions)));
    restrict(field('audio'), new Set(['none', ...(settings.some(m => m.audio) ? ['native'] : [])]));
    restrict(field('recipe_id'), new Set(catalog.recipes.filter(r => r.modes.includes(mode) && r.required.every(role => roles.includes(role)) && roles.every(role => r.roles.includes(role))).map(r => r.id)));
    restrict(field('ending'), new Set(['close_up', 'hero', ...(roles.includes('END_IMAGE') ? ['match_end'] : [])]));
    const description = document.getElementById('creator-recipe-description');
    if (description) description.textContent = recipe?.description || 'En mall hj\u00e4lper med uppl\u00e4gget. Dina bilder och din id\u00e9 styr inneh\u00e5llet.';
  }
  async function preview() {
    planController?.abort(); planController = new AbortController(); const number = ++requestNumber;
    promptDetails.hidden = true;
    status.parentElement.classList.remove('is-error');
    if (!value('brief').trim()) { status.textContent = 'Beskriv din id\u00e9. Ingen betald generation startas h\u00e4r.'; return; }
    status.textContent = 'Anpassar instruktionen till dina val...';
    try {
      const response = await fetch(form.dataset.planUrl, {method: 'POST', body: new FormData(form), signal: planController.signal, headers: {'Accept': 'application/json'}});
      const data = await response.json(); if (number !== requestNumber) return;
      if (!response.ok) {
        const errors = Object.values(data.errors || {}).flat().map(e => e.message);
        throw new Error(data.error || errors.join(' ') || 'Planen kunde inte kontrolleras. Din id\u00e9 finns kvar.');
      }
      const details = [data.duration && `${data.duration} sekunder`, data.aspect_ratio !== 'auto' && data.aspect_ratio].filter(Boolean);
      status.textContent = `${value('model_override') ? 'Vald modell' : 'Auto rekommenderar'}: ${data.model}${details.length ? ' \u00b7 ' + details.join(' \u00b7 ') : ''}.\n${(data.warnings || []).join('\n')}`.trim();
      prompt.textContent = data.prompt; promptDetails.hidden = false;
    } catch (error) {
      if (error.name !== 'AbortError' && number === requestNumber) { status.textContent = error.message; status.parentElement.classList.add('is-error'); }
    }
  }
  function changed() { requestNumber++; promptDetails.hidden = true; showFrames(); compatibleChoices(); remember(); clearTimeout(timer); planController?.abort(); timer = setTimeout(preview, 450); }
  form.addEventListener('input', event => { if (event.target.matches('[data-creator-field]')) changed(); });
  form.addEventListener('change', event => { if (event.target.matches('[data-creator-field]')) changed(); });
  form.addEventListener('submit', event => {
    if (uploading) { event.preventDefault(); pickerStatus.textContent = 'V\u00e4nta tills bilden har laddats upp.'; return; }
    remember();
    if (event.submitter === submit) setTimeout(() => { submit.disabled = true; }, 0);
  });
  window.addEventListener('pageshow', () => { submit.disabled = false; });
  showFrames(); compatibleChoices();
  if (form.querySelector('.creator-errors')) form.querySelector('.creator-errors').focus();
  else if (value('brief').trim()) preview();
})();
