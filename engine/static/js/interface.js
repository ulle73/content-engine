/* Presentation only: reveal linked sections and give native form submissions feedback. */
(() => {
  function revealTarget() {
    const target = document.getElementById(location.hash.slice(1));
    if (!target) return;
    let parent = target;
    while (parent) {
      if (parent.tagName === 'DETAILS') parent.open = true;
      parent = parent.parentElement;
    }
    target.scrollIntoView({ block: 'start' });
  }
  window.addEventListener('hashchange', revealTarget);
  revealTarget();

  document.querySelectorAll('form[data-busy-label]').forEach(form => {
    form.addEventListener('submit', event => {
      if (form.dataset.busy) { event.preventDefault(); return; }
      form.dataset.busy = 'true';
      form.setAttribute('aria-busy', 'true');
      const button = event.submitter;
      if (button) {
        button.dataset.originalHtml = button.innerHTML;
        button.textContent = form.dataset.busyLabel;
        button.setAttribute('aria-disabled', 'true');
        button.disabled = true;
      }
    });
  });
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('form[data-busy-label]').forEach(form => {
      delete form.dataset.busy;
      form.removeAttribute('aria-busy');
      form.querySelectorAll('[data-original-html]').forEach(button => {
        button.innerHTML = button.dataset.originalHtml;
        delete button.dataset.originalHtml;
        button.removeAttribute('aria-disabled');
        button.disabled = false;
      });
    });
  });

  // Native validation cannot focus a required input inside a closed disclosure.
  document.addEventListener('invalid', event => {
    let parent = event.target.parentElement;
    while (parent) {
      if (parent.tagName === 'DETAILS') parent.open = true;
      parent = parent.parentElement;
    }
  }, true);

  let unsaved = false;
  document.querySelectorAll('form[data-track-changes]').forEach(form => {
    form.addEventListener('input', () => { unsaved = true; });
    form.addEventListener('submit', () => { unsaved = false; });
  });
  window.addEventListener('beforeunload', event => {
    if (!unsaved) return;
    event.preventDefault();
    event.returnValue = '';
  });
})();
