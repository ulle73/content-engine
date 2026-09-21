document.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-copy-prompt]');
  if (!button) return;
  const input = document.getElementById(button.dataset.copyPrompt);
  const status = button.closest('form').querySelector('[data-copy-status]');
  try {
    await navigator.clipboard.writeText(input.value);
    status.textContent = 'Prompten är kopierad.';
  } catch {
    input.focus(); input.select();
    status.textContent = 'Texten är markerad. Kopiera med tangentbordet eller telefonens meny.';
  }
});
