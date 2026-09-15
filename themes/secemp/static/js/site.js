document.addEventListener('DOMContentLoaded', function () {
  if (window.hljs) window.hljs.highlightAll();

  var copyButton = document.querySelector('[data-copy-link]');
  if (!copyButton || !navigator.clipboard || !window.isSecureContext) return;
  copyButton.hidden = false;
  copyButton.addEventListener('click', async function () {
    try {
      var url = new URL(window.location.href);
      url.hash = '';
      url.search = '';
      await navigator.clipboard.writeText(url.href);
      copyButton.textContent = 'Copied!';
    } catch (error) {
      copyButton.textContent = 'Copy from address bar';
    }
  });
});
