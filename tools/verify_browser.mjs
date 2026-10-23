// Developer protocol test for a dedicated Arc Forever verification profile.
// Serve tests/fixtures at 127.0.0.1:19378; pass the dedicated browser CDP endpoint.
import { writeFile } from 'node:fs/promises';

const [endpoint = 'http://127.0.0.1:19383', output] = process.argv.slice(2);
const version = await (await fetch(`${endpoint}/json/version`)).json();
const socket = new WebSocket(version.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
let sequence = 0;
const pending = new Map();
socket.onmessage = event => {
  const message = JSON.parse(event.data);
  const entry = pending.get(message.id);
  if (!entry) return;
  clearTimeout(entry.timer); pending.delete(message.id);
  message.error ? entry.reject(new Error(JSON.stringify(message.error))) : entry.resolve(message.result);
};
function call(method, params = {}, sessionId) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Timed out: ${method}`)); }, 15000);
    pending.set(id, {resolve, reject, timer});
    socket.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
  });
}
async function evaluate(session, expression) {
  const result = await call('Runtime.evaluate', {expression, returnByValue: true}, session);
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function page(url, expectedTitle) {
  const {targetId} = await call('Target.createTarget', {url});
  const {sessionId} = await call('Target.attachToTarget', {targetId, flatten: true});
  for (let i = 0; i < 50; i++) {
    const info = await evaluate(sessionId, '({title:document.title,url:location.href,ready:document.readyState,secure:isSecureContext})');
    if (info.title === expectedTitle && info.ready === 'complete') return {targetId, sessionId, info};
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error(`Page did not render: ${url}`);
}
try {
  const fixture = await page('http://127.0.0.1:19378/', 'Arc Forever Verification');
  if (process.argv.includes('--reset-fixture'))
    await evaluate(fixture.sessionId, "localStorage.removeItem('arc-forever-test')");
  const before = await evaluate(fixture.sessionId, "localStorage.getItem('arc-forever-test')");
  const fixtureState = await evaluate(fixture.sessionId, `(() => {
    document.querySelector('#counter').click();
    return {javascript:document.querySelector('#state').textContent,counter:document.querySelector('#counter').textContent,
      stored:localStorage.getItem('arc-forever-test')};
  })()`);
  if (fixtureState.javascript !== 'JavaScript executed' || fixtureState.counter !== 'Clicks: 1' || fixtureState.stored !== 'persisted')
    throw new Error('Fixture interaction failed');
  const https = await page('https://example.com/', 'Example Domain');
  if (!https.info.secure) throw new Error('HTTPS secure context check failed');
  const report = {browser:version.Browser, fixture:fixtureState, persisted_before_test:before === 'persisted',
    https:https.info, target_ids:{fixture:fixture.targetId,https:https.targetId}, passed:true};
  if (output) await writeFile(output, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
  if (process.argv.includes('--close')) await call('Browser.close');
} finally {
  socket.close();
}
