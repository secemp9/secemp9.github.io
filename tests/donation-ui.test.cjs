const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { JSDOM, VirtualConsole } = require('jsdom');

// Deliberately synthetic destinations: this fixture can never collect donations.
const fixture = `<!doctype html><html><body>
<main data-donation-widget data-default-method="card" data-default-frequency="once">
  <div data-frequency-toggle hidden role="group" aria-label="Donation frequency">
    <button type="button" data-frequency="once" aria-pressed="false" aria-controls="donate-once">One-time</button>
    <button type="button" data-frequency="monthly" aria-pressed="false" aria-controls="donate-monthly">Monthly</button>
  </div>
  <section id="donate-once" data-frequency-panel="once">
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
  </section>
  <section id="donate-monthly" data-frequency-panel="monthly">
    <h2>Monthly</h2>
    <a data-monthly-plan href="https://example.invalid/monthly-five">€5 / month</a>
    <a data-monthly-plan href="https://example.invalid/monthly-ten">€10 / month</a>
    <a data-monthly-plan href="https://example.invalid/monthly-twenty">€20 / month</a>
    <p>Billed every month until you cancel.</p>
    <a data-monthly-custom href="https://example.invalid/monthly-custom" aria-describedby="monthly-custom-help">Other monthly amount</a>
    <p id="monthly-custom-help">Choose a quantity at checkout. Each unit is 1 EUR per month.</p>
    <a href="https://example.invalid/sponsors">GitHub Sponsors</a>
  </section>
  <a data-manage-monthly href="https://example.invalid/customer-portal">Manage or cancel monthly support</a>
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

function selectFrequency(ui, frequency) {
  ui.find(`[data-frequency="${frequency}"]`).click();
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

test('enhancement defaults to one-time donations and exposes the frequency controls', async (t) => {
  const ui = await boot(t);
  assert.equal(ui.find('[data-frequency-toggle]').hidden, false);
  assert.equal(ui.find('[data-frequency="once"]').getAttribute('aria-pressed'), 'true');
  assert.equal(ui.find('[data-frequency="monthly"]').getAttribute('aria-pressed'), 'false');
  assert.equal(ui.find('[data-frequency-panel="once"]').hidden, false);
  assert.equal(ui.find('[data-frequency-panel="monthly"]').hidden, true);
  assert.equal(ui.find('[data-manage-monthly]').closest('[hidden]'), null);
  assert.equal(ui.window.fetch.mock.callCount(), 0);
});

test('frequency switches update the controlled panels and keep subscription management available', async (t) => {
  const ui = await boot(t);
  const onceButton = ui.find('[data-frequency="once"]');
  const monthlyButton = ui.find('[data-frequency="monthly"]');
  const oncePanel = ui.document.getElementById(onceButton.getAttribute('aria-controls'));
  const monthlyPanel = ui.document.getElementById(monthlyButton.getAttribute('aria-controls'));
  const management = ui.find('[data-manage-monthly]');
  selectFrequency(ui, 'monthly');
  assert.equal(onceButton.getAttribute('aria-pressed'), 'false');
  assert.equal(monthlyButton.getAttribute('aria-pressed'), 'true');
  assert.equal(oncePanel.hidden, true);
  assert.equal(monthlyPanel.hidden, false);
  assert.equal(management.closest('[hidden]'), null);
  selectFrequency(ui, 'once');
  assert.equal(onceButton.getAttribute('aria-pressed'), 'true');
  assert.equal(monthlyButton.getAttribute('aria-pressed'), 'false');
  assert.equal(oncePanel.hidden, false);
  assert.equal(monthlyPanel.hidden, true);
  assert.equal(management.closest('[hidden]'), null);
  assert.equal(management.href, 'https://example.invalid/customer-portal');
  assert.equal(ui.window.fetch.mock.callCount(), 0);
});

test('each monthly amount retains its own checkout URL through method and frequency changes', async (t) => {
  const ui = await boot(t);
  // Prediction: selecting a payment view never rewrites any of the three fixed monthly checkout destinations.
  const plans = () => Array.from(ui.document.querySelectorAll('[data-monthly-plan]'))
    .map((link) => [link.textContent, link.href]);
  const expected = [
    ['€5 / month', 'https://example.invalid/monthly-five'],
    ['€10 / month', 'https://example.invalid/monthly-ten'],
    ['€20 / month', 'https://example.invalid/monthly-twenty'],
  ];
  assert.deepEqual(plans(), expected);
  selectFrequency(ui, 'monthly');
  assert.deepEqual(plans(), expected);
  selectFrequency(ui, 'once');
  selectCrypto(ui);
  selectNetwork(ui, 'network-two');
  selectFrequency(ui, 'monthly');
  assert.deepEqual(plans(), expected);
  assert.equal(ui.find('[data-method-panel="card"] a').href, 'https://example.invalid/checkout');
  assert.equal(ui.window.fetch.mock.callCount(), 0);
});

test('custom monthly checkout stays static and accessible through frequency changes', async (t) => {
  const ui = await boot(t);
  const custom = ui.find('[data-monthly-custom]');
  assert.notEqual(custom.closest('[hidden]'), null);
  selectFrequency(ui, 'monthly');
  assert.equal(custom.closest('[hidden]'), null);
  assert.equal(custom.href, 'https://example.invalid/monthly-custom');
  assert.equal(ui.document.getElementById(custom.getAttribute('aria-describedby')).textContent,
    'Choose a quantity at checkout. Each unit is 1 EUR per month.');
  selectFrequency(ui, 'once');
  selectCrypto(ui);
  selectFrequency(ui, 'monthly');
  assert.equal(custom.href, 'https://example.invalid/monthly-custom');
  assert.equal(ui.find('[data-manage-monthly]').closest('[hidden]'), null);
  assert.equal(ui.window.fetch.mock.callCount(), 0);
});

test('a custom-only monthly option works without fixed tiers or backend calls', async (t) => {
  const html = fixture.replace(/    <a data-monthly-plan[^\n]+\n/g, '');
  const ui = await boot(t, { html });
  selectFrequency(ui, 'monthly');
  assert.equal(ui.document.querySelectorAll('[data-monthly-plan]').length, 0);
  assert.equal(ui.find('[data-monthly-custom]').closest('[hidden]'), null);
  assert.equal(ui.find('[data-manage-monthly]').closest('[hidden]'), null);
  assert.equal(ui.window.fetch.mock.callCount(), 0);
});

test('returning from monthly restores the previous one-time method, network, and asset', async (t) => {
  const ui = await boot(t);
  selectCrypto(ui);
  selectNetwork(ui, 'network-two');
  ui.find('[data-asset="two-token"]').click();
  selectFrequency(ui, 'monthly');
  assert.notEqual(wallet(ui, 'two-token').closest('[hidden]'), null);
  selectFrequency(ui, 'once');
  assert.equal(ui.find('[data-method="crypto"]').getAttribute('aria-pressed'), 'true');
  assert.equal(ui.find('[data-method-panel="crypto"]').hidden, false);
  assert.equal(ui.find('[data-network-select]').value, 'network-two');
  assert.equal(ui.find('[data-asset="two-token"]').getAttribute('aria-pressed'), 'true');
  assert.deepEqual(visibleValues(ui.document, 'data-wallet-panel'), ['two-token']);
  assert.equal(wallet(ui, 'two-token').closest('[hidden]'), null);
  assert.equal(ui.window.fetch.mock.callCount(), 0);
});

test('changing frequency clears a completed copy announcement', async (t) => {
  const ui = await boot(t, { clipboard: { writeText: async () => {} } });
  selectCrypto(ui);
  const panel = wallet(ui, 'one-native');
  const status = panel.querySelector('[data-copy-status]');
  panel.querySelector('[data-copy-address]').click();
  await settle();
  assert.equal(status.textContent, 'Address copied.');
  selectFrequency(ui, 'monthly');
  assert.equal(status.textContent, '');
  selectFrequency(ui, 'once');
  assert.equal(status.textContent, '');
});

test('copy completion after choosing monthly cannot announce success in a hidden one-time panel', async (t) => {
  const pending = deferred();
  const ui = await boot(t, { clipboard: { writeText: () => pending.promise } });
  selectCrypto(ui);
  const previous = wallet(ui, 'one-native');
  previous.querySelector('[data-copy-address]').click();
  selectFrequency(ui, 'monthly');
  pending.resolve();
  await settle();
  assert.notEqual(previous.closest('[hidden]'), null);
  assert.equal(previous.querySelector('[data-copy-status]').textContent, '');
  selectFrequency(ui, 'once');
  assert.equal(previous.querySelector('[data-copy-status]').textContent, '');
});

test('copy failure after choosing monthly cannot focus a hidden address or displace the monthly link', async (t) => {
  const pending = deferred();
  const ui = await boot(t, { clipboard: { writeText: () => pending.promise } });
  selectCrypto(ui);
  const previous = wallet(ui, 'one-native');
  previous.querySelector('[data-copy-address]').click();
  selectFrequency(ui, 'monthly');
  const monthlyLink = ui.find('[data-monthly-plan]');
  monthlyLink.focus();
  pending.reject(new Error('Permission denied'));
  await settle();
  assert.notEqual(previous.closest('[hidden]'), null);
  assert.equal(ui.document.activeElement, monthlyLink);
  assert.equal(previous.querySelector('[data-copy-status]').textContent, '');
});

test('returning from monthly before an earlier copy completes still invalidates its announcement', async (t) => {
  const pending = deferred();
  const ui = await boot(t, { clipboard: { writeText: () => pending.promise } });
  selectCrypto(ui);
  const original = wallet(ui, 'one-native');
  original.querySelector('[data-copy-address]').click();
  selectFrequency(ui, 'monthly');
  selectFrequency(ui, 'once');
  pending.resolve();
  await settle();
  assert.equal(original.closest('[hidden]'), null);
  assert.equal(original.querySelector('[data-copy-status]').textContent, '');
});

test('returning from monthly before an earlier copy fails cannot steal focus', async (t) => {
  const pending = deferred();
  const ui = await boot(t, { clipboard: { writeText: () => pending.promise } });
  selectCrypto(ui);
  const original = wallet(ui, 'one-native');
  original.querySelector('[data-copy-address]').click();
  selectFrequency(ui, 'monthly');
  selectFrequency(ui, 'once');
  const frequencyButton = ui.find('[data-frequency="once"]');
  frequencyButton.focus();
  pending.reject(new Error('Permission denied'));
  await settle();
  assert.equal(original.closest('[hidden]'), null);
  assert.equal(ui.document.activeElement, frequencyButton);
  assert.equal(original.querySelector('[data-copy-status]').textContent, '');
});

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
  // Arguments originate in jsdom's realm; compare their count and exact string.
  assert.equal(writeText.mock.calls[0].arguments.length, 1);
  assert.equal(writeText.mock.calls[0].arguments[0], 'fixture-address-two-TOKEN');
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
