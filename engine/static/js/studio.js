/* Progressive enhancement. Native forms and server validation remain authoritative. */
(() => {
  const status = document.getElementById('interaction-status');
  const main = document.querySelector('main');
  if (main) { main.id = 'main-content'; main.tabIndex = -1; }
  const announce = (message) => {
    status.textContent = message;
    status.hidden = false;
  };
  function reveal(element) {
    for (let parent = element?.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
  }
  function revealHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    reveal(target);
    if (target.tagName === 'DETAILS') target.open = true;
    target.scrollIntoView({block: 'start'});
  }
  window.addEventListener('hashchange', revealHash);
  if (location.hash) revealHash();
  document.addEventListener('invalid', event => reveal(event.target), true);
  document.querySelectorAll('textarea[maxlength]').forEach(field => {
    const counter = document.createElement('p');
    counter.className = 'field-counter';
    counter.id = `${field.id}-count`;
    field.setAttribute('aria-describedby', [field.getAttribute('aria-describedby'), counter.id].filter(Boolean).join(' '));
    field.after(counter);
    const update = () => { counter.textContent = `${field.value.length.toLocaleString('sv-SE')} / ${field.maxLength.toLocaleString('sv-SE')} tecken`; };
    field.addEventListener('input', update);
    update();
  });
  document.querySelectorAll('.app-nav-link.is-active, .mobile-nav-link.is-active').forEach(link => link.setAttribute('aria-current', 'page'));
  const activeForms = new Map();
  const editor = document.querySelector('.review-page form[enctype="multipart/form-data"]');
  const initial = editor ? new URLSearchParams(new FormData(editor)).toString() : null;
  let submittingEditor = false;
  if (editor) {
    const hint = editor.querySelector('.editor-footer .small');
    editor.addEventListener('input', () => {
      const dirty = new URLSearchParams(new FormData(editor)).toString() !== initial;
      if (hint) {
        hint.textContent = dirty ? 'Du har osparade ändringar.' : 'Ändringar sparas i Content Engine.';
        hint.classList.toggle('editor-dirty', dirty);
      }
    });
    window.addEventListener('beforeunload', event => {
      if (!submittingEditor && new URLSearchParams(new FormData(editor)).toString() !== initial) {
        event.preventDefault();
        event.returnValue = '';
      }
    });
  }
  document.addEventListener('submit', event => {
    const form = event.target;
    // Polling / HTMX forms own their lifecycle. Never disable their retry controls.
    if (event.defaultPrevented || form.matches('[hx-post], [hx-get], #job-poll, #poll-import')) return;
    if (activeForms.has(form)) { event.preventDefault(); return; }
    const submitter = event.submitter;
    activeForms.set(form, submitter?.textContent);
    if (form === editor) submittingEditor = true;
    form.setAttribute('aria-busy', 'true');
    announce(form.dataset.loading || 'Arbetar med din förfrågan…');
    // Preserve named submitter values in the browser's native form submission.
    if (submitter) submitter.setAttribute('aria-disabled', 'true');
  });
  window.addEventListener('pageshow', () => {
    activeForms.forEach((_, form) => {
      form.removeAttribute('aria-busy');
      form.querySelectorAll('[aria-disabled]').forEach(button => button.removeAttribute('aria-disabled'));
    });
    activeForms.clear();
    status.hidden = true;
  });
  document.body.addEventListener('htmx:beforeRequest', event => {
    if (event.detail.target?.id === 'ad-detail-panel') {
      event.detail.target.setAttribute('aria-busy', 'true');
      announce('Hämtar originalannons och analys…');
    }
  });
  document.body.addEventListener('htmx:afterRequest', event => {
    event.detail.target?.removeAttribute('aria-busy');
    if (!event.detail.successful) announce('Annonsen kunde inte hämtas. Välj annonsen igen för att försöka på nytt.');
    else status.hidden = true;
  });
  document.body.addEventListener('htmx:afterSwap', event => {
    if (event.detail.target?.id !== 'ad-detail-panel') return;
    const url = event.detail.requestConfig?.path;
    document.querySelectorAll('.ad-intel-row').forEach(row => {
      const selected = row.getAttribute('hx-get') === url;
      row.classList.toggle('is-selected', selected);
      if (selected) row.setAttribute('aria-current', 'true');
      else row.removeAttribute('aria-current');
    });
    event.detail.target.tabIndex = -1;
    event.detail.target.focus({preventScroll: true});
  });
})();
