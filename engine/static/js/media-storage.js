(() => {
  const section = document.querySelector('[data-storage-url]');
  if (!section) return;
  const button = document.getElementById('media-storage-refresh');
  const load = async (refresh = false) => {
    button.disabled = true;
    section.setAttribute('aria-busy', 'true');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(section.dataset.storageUrl + (refresh ? '?refresh=1' : ''), {
        credentials: 'same-origin', signal: controller.signal,
      });
      if (!response.ok) throw new Error('Storage unavailable');
      const usage = await response.json();
      section.querySelectorAll('[data-storage-field]').forEach(element => {
        const value = usage[element.dataset.storageField];
        if (value !== undefined) element.textContent = String(value);
      });
    } catch {
      section.querySelector('[data-storage-field="detail"]').textContent =
        'Lagringen kunde inte uppdateras. Senaste visade värden behålls. Försök igen med Uppdatera lagring.';
      ['capacity_label', 'free_label'].forEach(field => {
        const element = section.querySelector(`[data-storage-field="${field}"]`);
        if (element.textContent === 'Hämtar…') element.textContent = 'Kan inte mätas';
      });
    } finally {
      clearTimeout(timeout);
      section.removeAttribute('aria-busy');
      button.disabled = false;
    }
  };
  button.addEventListener('click', () => load(true));
  load();
})();
