'use strict';
// Optional convenience only: all evidence, status and downloads work without JS.
document.querySelectorAll('[data-copy]').forEach((button) => {
  button.addEventListener('click', async () => {
    const field = document.getElementById(button.dataset.copy);
    const status = document.getElementById('copy-status');
    if (!field || !status) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(field.value);
      status.textContent = `${button.textContent === 'Copy name' ? 'Name' : 'Note'} copied. This research file is NOT approved for submission.`;
    } catch {
      field.focus();
      field.select();
      status.textContent = 'Clipboard is unavailable. The text is selected for copying. This file is NOT approved for submission.';
    }
  });
});
