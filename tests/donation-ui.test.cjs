const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { JSDOM, VirtualConsole } = require('jsdom');

// Deliberately synthetic destinations: this fixture can never collect donations.
const fixture = `<!doctype html><html><body>
<main data-donation-widget data-default-method="card">
  <div data-method-toggle hidden aria-label="Payment method">
    <button type="button" data-method="card" aria-pressed="false">Card</button>
    <button type="button" data-method="crypto" aria-pressed="false">Crypto</button>
  </div>
  <section data-method-panel="card"><a href="https://example.invalid/checkout">Donate by card</a></section>
  <section data-method-panel="crypto">
    <div data-crypto-controls hidden>
      <label>Network <select data-network-select>
        <option value="network-one">Network one</option>
        <option value="network-two">Network two</option>
      </select></label>
      <div aria-label="Asset">
        <button type="button" data-asset="one-native" data-network="network-one" aria-pressed="false">ONE</button>
        <button type="button" data-asset="one-token" data-network="network-one" aria-pressed="false">TOKEN</button>
        <button type="button" data-asset="two-native" data-network="network-two" aria-pressed="false">TWO</button>
        <button type="button" data-asset="two-token" data-network="network-two" aria-pressed="false">TOKEN</button>
      </div>
    </div>
    <article data-wallet-panel="one-native" data-network="network-one">
      <input data-wallet-address readonly value="fixture-address-ONE">
      <button type="button" data-copy-address hidden>Copy address</button>
      <span data-copy-status role="status" aria-live="polite"></span>
    </article>
    <article data-wallet-panel="one-token" data-network="network-one">
      <input data-wallet-address readonly value="fixture-address-one-TOKEN">
      <button type="button" data-copy-address hidden>Copy address</button>
      <span data-copy-status role="status" aria-live="polite"></span>
    </article>
    <article data-wallet-panel="two-native" data-network="network-two">
      <input data-wallet-address readonly value="fixture-address-TWO">
      <button type="button" data-copy-address hidden>Copy address</button>
      <span data-copy-status role="status" aria-live="polite"></span>
    </article>
    <article data-wallet-panel="two-token" data-network="network-two">
      <input data-wallet-address readonly value="fixture-address-two-TOKEN">
      <button type="button" data-copy-address hidden>Copy address</button>
      <span data-copy-status role="status" aria-live="polite"></span>
    </article>
  </section>
</main>
</body></html>`;

async function boot(t, { clipboard, html = fixture, secureContext = true } = {}) {
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', (error) => errors.push(error));
  const dom = new JSDOM(html, {
    url: 'https://example.invalid/donate/',
    runScripts: 'outside-only',
    virtualConsole,
  });
  t.after(() => {
    dom.window.close();
    assert.deepEqual(errors, [], 'Donation event handlers must not throw uncaught errors');
  });
  const { window } = dom;
  const { document } = window;
  // jsdom does not expose this browser property, even for an HTTPS URL.
  Object.defineProperty(window, 'isSecureContext', { value: secureContext });
  if (clipboard !== undefined) {
    Object.defineProperty(window.navigator, 'clipboard', { value: clipboard });
  }
  // Interactions must never contact a payment service or submit a donation.
  window.fetch = t.mock.fn(() => {
    assert.fail('Donation selection and address copying must not make network requests');
  });
  // Let jsdom finish loading before explicitly starting the application once.
  await new Promise((resolve) => document.addEventListener('DOMContentLoaded', resolve, { once: true }));
  window.eval(fs.readFileSync(path.join(__dirname, '../themes/secemp/static/js/donate.js'), 'utf8'));
  document.dispatchEvent(new window.Event('DOMContentLoaded'));
  return { window, document, find: (selector) => document.querySelector(selector) };
}

function visibleValues(document, attribute) {
  // Prediction: exactly the configured active network's assets, or one active wallet, remain visible.
  return Array.from(document.querySelectorAll(`[${attribute}]`))
    .filter((element) => !element.hidden)
    .map((element) => element.getAttribute(attribute));
}

function selectNetwork(ui, network) {
  const select = ui.find('[data-network-select]');
  select.value = network;
  select.dispatchEvent(new ui.window.Event('change', { bubbles: true }));
}

function selectCrypto(ui) {
  ui.find('[data-method="crypto"]').click();
}

function wallet(ui, id) {
  return ui.find(`[data-wallet-panel="${id}"]`);
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

// Clipboard callbacks settle in the microtask queue, without a timed sleep.
async function settle() {
  await Promise.resolve();
  await Promise.resolve();
}

test('enhancement defaults to the configured method, first network, and first asset', async (t) => {
  const ui = await boot(t);
  assert.equal(ui.find('[data-method-toggle]').hidden, false);
  assert.equal(ui.find('[data-crypto-controls]').hidden, false);
  assert.equal(ui.find('[data-method="card"]').getAttribute('aria-pressed'), 'true');
  assert.equal(ui.find('[data-method="crypto"]').getAttribute('aria-pressed'), 'false');
  assert.equal(ui.find('[data-method-panel="card"]').hidden, false);
  assert.equal(ui.find('[data-method-panel="crypto"]').hidden, true);
  assert.equal(ui.find('[data-network-select]').value, 'network-one');
  assert.deepEqual(visibleValues(ui.document, 'data-asset'), ['one-native', 'one-token']);
  assert.deepEqual(visibleValues(ui.document, 'data-wallet-panel'), ['one-native']);
  assert.equal(ui.find('[data-asset="one-native"]').getAttribute('aria-pressed'), 'true');
  assert.equal(ui.find('[data-asset="one-token"]').getAttribute('aria-pressed'), 'false');
});

test('method switches update visibility and accessible pressed state', async (t) => {
  const ui = await boot(t);
  selectCrypto(ui);
  assert.equal(ui.find('[data-method="crypto"]').getAttribute('aria-pressed'), 'true');
  assert.equal(ui.find('[data-method="card"]').getAttribute('aria-pressed'), 'false');
  assert.equal(ui.find('[data-method-panel="crypto"]').hidden, false);
  assert.equal(ui.find('[data-method-panel="card"]').hidden, true);
  ui.find('[data-method="card"]').click();
  assert.equal(ui.find('[data-method="card"]').getAttribute('aria-pressed'), 'true');
  assert.equal(ui.find('[data-method="crypto"]').getAttribute('aria-pressed'), 'false');
  assert.equal(ui.find('[data-method-panel="card"]').hidden, false);
  assert.equal(ui.find('[data-method-panel="crypto"]').hidden, true);
  assert.equal(ui.window.fetch.mock.callCount(), 0);
});

test('network changes reset to that network’s first asset and asset selection follows it', async (t) => {
  const ui = await boot(t);
  selectCrypto(ui);
  ui.find('[data-asset="one-token"]').click();
  assert.deepEqual(visibleValues(ui.document, 'data-wallet-panel'), ['one-token']);
  selectNetwork(ui, 'network-two');
  assert.deepEqual(visibleValues(ui.document, 'data-asset'), ['two-native', 'two-token']);
  assert.deepEqual(visibleValues(ui.document, 'data-wallet-panel'), ['two-native']);
  assert.equal(ui.find('[data-asset="one-token"]').getAttribute('aria-pressed'), 'false');
  assert.equal(ui.find('[data-asset="two-native"]').getAttribute('aria-pressed'), 'true');
  ui.find('[data-asset="two-token"]').click();
  assert.deepEqual(visibleValues(ui.document, 'data-wallet-panel'), ['two-token']);
  assert.equal(ui.find('[data-asset="two-token"]').getAttribute('aria-pressed'), 'true');
  assert.equal(ui.find('[data-asset="two-native"]').getAttribute('aria-pressed'), 'false');
  selectNetwork(ui, 'network-one');
  assert.deepEqual(visibleValues(ui.document, 'data-wallet-panel'), ['one-native']);
  assert.equal(ui.window.fetch.mock.callCount(), 0);
});

test('copy writes the selected wallet’s exact address and announces only copying', async (t) => {
  const writeText = t.mock.fn(async () => {});
  const ui = await boot(t, { clipboard: { writeText } });
  selectCrypto(ui);
  selectNetwork(ui, 'network-two');
  ui.find('[data-asset="two-token"]').click();
  const panel = wallet(ui, 'two-token');
  const copy = panel.querySelector('[data-copy-address]');
  const status = panel.querySelector('[data-copy-status]');
  assert.equal(copy.hidden, false);
  copy.click();
  await settle();
  assert.equal(writeText.mock.callCount(), 1);
  assert.deepEqual(writeText.mock.calls[0].arguments, ['fixture-address-two-TOKEN']);
  assert.match(status.textContent, /copied/i);
  assert.doesNotMatch(status.textContent, /paid|donation received|payment successful/i);
  assert.equal(status.getAttribute('role'), 'status');
  assert.equal(status.getAttribute('aria-live'), 'polite');
  assert.equal(ui.window.fetch.mock.callCount(), 0);
  ui.find('[data-asset="two-native"]').click();
  assert.equal(status.textContent, '');
});

test('clipboard rejection focuses and selects the visible exact address for manual copying', async (t) => {
  const ui = await boot(t, { clipboard: { writeText: async () => { throw new Error('Permission denied'); } } });
  selectCrypto(ui);
  ui.find('[data-asset="one-token"]').click();
  const panel = wallet(ui, 'one-token');
  const input = panel.querySelector('[data-wallet-address]');
  panel.querySelector('[data-copy-address]').click();
  await settle();
  assert.equal(ui.document.activeElement, input);
  assert.equal(input.selectionStart, 0);
  assert.equal(input.selectionEnd, input.value.length);
  assert.equal(input.value, 'fixture-address-one-TOKEN');
  assert.equal(panel.querySelector('[data-copy-status]').textContent, 'Select and copy the address above.');
});

test('unavailable Clipboard API keeps copy controls hidden and addresses selectable', async (t) => {
  const ui = await boot(t);
  selectCrypto(ui);
  const panel = wallet(ui, 'one-native');
  const input = panel.querySelector('[data-wallet-address]');
  assert.equal(panel.hidden, false);
  assert.equal(panel.querySelector('[data-copy-address]').hidden, true);
  assert.equal(input.readOnly, true);
  assert.equal(input.disabled, false);
  input.focus();
  input.select();
  assert.equal(ui.document.activeElement, input);
  assert.equal(input.value.slice(input.selectionStart, input.selectionEnd), 'fixture-address-ONE');
});

test('insecure contexts preserve manual copying without enabling Clipboard API controls', async (t) => {
  const writeText = t.mock.fn(async () => {});
  const ui = await boot(t, { clipboard: { writeText }, secureContext: false });
  selectCrypto(ui);
  const panel = wallet(ui, 'one-native');
  assert.equal(panel.querySelector('[data-copy-address]').hidden, true);
  assert.equal(panel.querySelector('[data-wallet-address]').disabled, false);
  assert.equal(writeText.mock.callCount(), 0);
});

test('copy completion after switching wallets cannot leave a stale success message', async (t) => {
  const pending = deferred();
  const ui = await boot(t, { clipboard: { writeText: () => pending.promise } });
  selectCrypto(ui);
  const previous = wallet(ui, 'one-native');
  previous.querySelector('[data-copy-address]').click();
  selectNetwork(ui, 'network-two');
  pending.resolve();
  await settle();
  assert.equal(previous.querySelector('[data-copy-status]').textContent, '');
  assert.equal(wallet(ui, 'two-native').querySelector('[data-copy-status]').textContent, '');
  selectNetwork(ui, 'network-one');
  assert.equal(previous.querySelector('[data-copy-status]').textContent, '');
});

test('copy failure after switching wallets cannot focus a hidden address or show a stale error', async (t) => {
  const pending = deferred();
  const ui = await boot(t, { clipboard: { writeText: () => pending.promise } });
  selectCrypto(ui);
  const previous = wallet(ui, 'one-native');
  previous.querySelector('[data-copy-address]').click();
  ui.find('[data-asset="one-token"]').click();
  const activeInput = wallet(ui, 'one-token').querySelector('[data-wallet-address]');
  activeInput.focus();
  pending.reject(new Error('Permission denied'));
  await settle();
  assert.equal(ui.document.activeElement, activeInput);
  assert.equal(previous.querySelector('[data-copy-status]').textContent, '');
  assert.equal(wallet(ui, 'one-token').querySelector('[data-copy-status]').textContent, '');
});

test('switching away and back still cancels an earlier clipboard announcement', async (t) => {
  const pending = deferred();
  const ui = await boot(t, { clipboard: { writeText: () => pending.promise } });
  selectCrypto(ui);
  const original = wallet(ui, 'one-native');
  original.querySelector('[data-copy-address]').click();
  ui.find('[data-asset="one-token"]').click();
  ui.find('[data-asset="one-native"]').click();
  pending.resolve();
  await settle();
  assert.equal(original.querySelector('[data-copy-status]').textContent, '');
});

test('a crypto-only configuration defaults to its available method', async (t) => {
  const html = fixture
    .replace('data-default-method="card"', 'data-default-method="crypto"')
    .replace('<button type="button" data-method="card" aria-pressed="false">Card</button>', '')
    .replace('<section data-method-panel="card"><a href="https://example.invalid/checkout">Donate by card</a></section>', '');
  const ui = await boot(t, { html });
  assert.equal(ui.find('[data-method-panel="crypto"]').hidden, false);
  assert.deepEqual(visibleValues(ui.document, 'data-wallet-panel'), ['one-native']);
});

test('a page without donation configuration initializes without errors or network access', async (t) => {
  const ui = await boot(t, { html: '<!doctype html><html><body><main>Payment details coming soon.</main></body></html>' });
  assert.equal(ui.find('[data-donation-widget]'), null);
  assert.equal(ui.window.fetch.mock.callCount(), 0);
});
