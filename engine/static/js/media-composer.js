/* A tab-local draft only: never store credentials, CSRF tokens or provider jobs. */
(() => {
  const form = document.querySelector('[data-composer]');
  if (!form) return;
  const status = form.querySelector('[data-composer-status]');
  const kind = form.elements.kind.value;
  const key = form.dataset.key;
  const ttl = 2 * 60 * 60 * 1000;
  const field = name => form.elements.namedItem(name);
  const data = id => {
    try { return JSON.parse(document.getElementById(id)?.textContent || '{}'); }
    catch { return {}; }
  };
  const images = data('composer-images');
  const hints = data('composer-presets');
  const models = data('composer-models');
  let state = {version: 1, kinds: {}, baseline: form.dataset.baseline || ''};
  let storageAvailable = true;
  try {
    const saved = JSON.parse(sessionStorage.getItem(key) || 'null');
    if (saved && saved.version === 1 && saved.kinds && typeof saved.kinds === 'object' &&
        Date.now() - saved.savedAt < ttl && saved.baseline === state.baseline) state = saved;
  } catch { storageAvailable = false; }
  const restore = (name, value) => {
    const control = field(name);
    if (!control || typeof value !== 'string') return;
    if (control.tagName === 'SELECT' && !Array.from(control.options).some(option => option.value === value)) return;
    if (control.type === 'checkbox') control.checked = value === '1';
    else control.value = value;
  };
  if (form.dataset.authoritative !== '1') {
    ['brief', 'shape', 'priority', 'source_asset'].forEach(name => restore(name, state[name]));
    const perKind = state.kinds[kind] || {};
    ['preset', 'count', 'model_override', 'include_logo'].forEach(name => restore(name, perKind[name]));
    if (kind === 'video') restore('end_asset', perKind.end_asset);
    // Explicit selection/retry links win over an older tab draft.
    const query = new URLSearchParams(location.search);
    if (query.has('source')) restore('source_asset', query.get('source'));
    if (kind === 'video' && query.has('end_source')) restore('end_asset', query.get('end_source'));
  }
  const sync = () => {
    const hint = document.getElementById('composer-preset-help');
    if (hint) hint.textContent = hints[field('preset')?.value] || hints[''] || '';
    ['source_asset', 'end_asset'].forEach(name => {
      const preview = form.querySelector(`[data-frame-preview="${name}"]`);
      if (!preview) return;
      const url = images[field(name)?.value];
      preview.hidden = !url;
      const label = form.querySelector(`[data-frame-label="${name}"]`);
      if (label) label.textContent = url ? (name === 'source_asset' ? 'Startbild vald' : 'Slutbild vald') : '';
      if (url) preview.src = url;
      else preview.removeAttribute('src');
    });
    if (kind === 'video') {
      const select = field('model_override');
      const previous = select.value;
      const mode = field('source_asset').value ? 'image-to-video' : 'text-to-video';
      const endSelected = Boolean(field('end_asset').value);
      select.replaceChildren(new Option('Auto · rekommenderas', ''));
      models.filter(model => Object.hasOwn(model.modes, mode) && (!endSelected || model.modes[mode])).forEach(model => select.add(new Option(model.id, model.id)));
      if (Array.from(select.options).some(option => option.value === previous)) select.value = previous;
      else if (previous && status) status.textContent = 'Bildvalet kräver en annan modell. Auto är nu valt; granska modell och pris före start.';
      const end = field('end_asset');
      end.setCustomValidity(end.value && !field('source_asset').value ? 'Välj en startbild innan du väljer en slutbild.' : '');
    }
  };
  const save = () => {
    ['brief', 'shape', 'priority', 'source_asset'].forEach(name => { if (field(name)) state[name] = field(name).value; });
    const perKind = state.kinds[kind] || {};
    ['preset', 'count', 'model_override', 'include_logo', ...(kind === 'video' ? ['end_asset'] : [])].forEach(name => {
      const control = field(name);
      if (control) perKind[name] = control.type === 'checkbox' ? (control.checked ? '1' : '0') : control.value;
    });
    state.kinds[kind] = perKind;
    state.savedAt = Date.now();
    try { sessionStorage.setItem(key, JSON.stringify(state)); }
    catch { storageAvailable = false; }
  };
  form.addEventListener('input', () => { sync(); save(); });
  form.addEventListener('change', () => { sync(); save(); });
  form.addEventListener('submit', save);
  window.addEventListener('pagehide', save);
  document.querySelectorAll('form[action$="/accounts/logout/"]').forEach(logout => logout.addEventListener('submit', () => {
    try {
      const prefix = key.split(':').slice(0, 2).join(':') + ':';
      Object.keys(sessionStorage).filter(item => item.startsWith(prefix)).forEach(item => sessionStorage.removeItem(item));
      window.removeEventListener('pagehide', save);
    } catch { /* Storage may be blocked by the browser. */ }
  }));
  sync();
  save();
  if (status) status.textContent = storageAvailable ? 'Text och val sparas tillfälligt i den här fliken i upp till två timmar. Ingen generation startas automatiskt.' : 'Webbläsaren tillåter inte tillfällig lagring. Behåll sidan öppen tills du granskat din idé.';
  const errors = form.querySelector('.composer-errors');
  if (errors) errors.focus();
})();
