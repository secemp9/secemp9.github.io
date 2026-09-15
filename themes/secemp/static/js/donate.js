document.addEventListener('DOMContentLoaded', function () {
  'use strict';

  var widget = document.querySelector('[data-donation-widget]');
  if (!widget) return;
  var frequencyToggle = widget.querySelector('[data-frequency-toggle]');
  var frequencyButtons = Array.from(widget.querySelectorAll('[data-frequency]'));
  var frequencyPanels = Array.from(widget.querySelectorAll('[data-frequency-panel]'));
  var currentFrequency = widget.dataset.defaultFrequency || 'once';
  var methodToggle = widget.querySelector('[data-method-toggle]');
  var methodButtons = Array.from(widget.querySelectorAll('[data-method]'));
  var methodPanels = Array.from(widget.querySelectorAll('[data-method-panel]'));
  var cryptoControls = widget.querySelector('[data-crypto-controls]');
  var networkSelect = widget.querySelector('[data-network-select]');
  var assetButtons = Array.from(widget.querySelectorAll('[data-asset]'));
  var walletPanels = Array.from(widget.querySelectorAll('[data-wallet-panel]'));
  var currentMethod = widget.dataset.defaultMethod || 'card';
  var currentWallet = null;
  var selectionVersion = 0;

  function clearCopyFeedback() {
    selectionVersion += 1;
    // Selection changes must clear feedback for every previous address.
    walletPanels.forEach(function (panel) {
      var status = panel.querySelector('[data-copy-status]');
      if (status) status.textContent = '';
    });
  }

  function selectMethod(method) {
    currentMethod = method;
    clearCopyFeedback();
    // Exactly the selected method panel is visible after enhancement.
    methodButtons.forEach(function (button) {
      button.setAttribute('aria-pressed', String(button.dataset.method === method));
    });
    methodPanels.forEach(function (panel) {
      panel.hidden = panel.dataset.methodPanel !== method;
    });
  }

  function selectFrequency(frequency) {
    currentFrequency = frequency;
    clearCopyFeedback();
    // Only the chosen cadence is visible; existing one-time choices are retained.
    frequencyButtons.forEach(function (button) {
      button.setAttribute('aria-pressed', String(button.dataset.frequency === frequency));
    });
    frequencyPanels.forEach(function (panel) {
      panel.hidden = panel.dataset.frequencyPanel !== frequency;
    });
  }

  function selectWallet(walletId) {
    currentWallet = walletId;
    clearCopyFeedback();
    // The selected wallet alone supplies the visible address and QR code.
    assetButtons.forEach(function (button) {
      button.setAttribute('aria-pressed', String(button.dataset.asset === walletId));
    });
    walletPanels.forEach(function (panel) {
      panel.hidden = panel.dataset.walletPanel !== walletId;
    });
  }

  function selectNetwork() {
    var network = networkSelect.value;
    var firstAsset = null;
    // A network exposes only its configured assets and selects its first one.
    assetButtons.forEach(function (button) {
      var matches = button.dataset.network === network;
      button.hidden = !matches;
      if (matches && !firstAsset) firstAsset = button.dataset.asset;
    });
    selectWallet(firstAsset);
  }

  // Each frequency control selects its own cadence without changing payment URLs.
  frequencyButtons.forEach(function (button) {
    button.addEventListener('click', function () { selectFrequency(button.dataset.frequency); });
  });
  // Each native method button selects its own panel.
  methodButtons.forEach(function (button) {
    button.addEventListener('click', function () { selectMethod(button.dataset.method); });
  });
  if (networkSelect && assetButtons.length) {
    networkSelect.addEventListener('change', selectNetwork);
    // Each asset selects its pre-rendered wallet within the selected network.
    assetButtons.forEach(function (button) {
      button.addEventListener('click', function () { selectWallet(button.dataset.asset); });
    });
    selectNetwork();
    if (cryptoControls) cryptoControls.hidden = false;
  }

  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function' && window.isSecureContext) {
    // Each copy control must copy precisely its own panel's receiving address.
    walletPanels.forEach(function (panel) {
      var button = panel.querySelector('[data-copy-address]');
      var address = panel.querySelector('[data-wallet-address]');
      var status = panel.querySelector('[data-copy-status]');
      if (!button || !address || !status) return;
      button.hidden = false;
      button.addEventListener('click', async function () {
        var version = selectionVersion;
        var walletId = panel.dataset.walletPanel;
        status.textContent = '';
        try {
          await navigator.clipboard.writeText(address.value);
          if (version === selectionVersion && currentWallet === walletId && currentMethod === 'crypto' && currentFrequency === 'once') {
            status.textContent = 'Address copied.';
          }
        } catch (error) {
          if (version !== selectionVersion || currentWallet !== walletId || currentMethod !== 'crypto' || currentFrequency !== 'once') return;
          address.focus();
          address.select();
          status.textContent = 'Select and copy the address above.';
        }
      });
    });
  }

  widget.classList.add('is-enhanced');
  selectMethod(currentMethod);
  selectFrequency(currentFrequency);
  if (methodToggle) methodToggle.hidden = false;
  if (frequencyToggle) frequencyToggle.hidden = false;
});
