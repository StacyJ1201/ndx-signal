import { validateData, freshness } from './data.mjs';

const $ = id => document.getElementById(id);
let published;
let busy = false;
const percent = value => `${(value * 100).toFixed(2)}%`;
const fullDate = day => new Date(`${day}T12:00:00Z`).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'America/New_York' });

function render() {
  if (!published) return;
  const s = published.signal;
  const status = freshness(published);
  const allowed = s.signal === 'TQQQ';
  const volPass = s.volatility < .35;
  const shockPass = s.shock !== null && s.shock < 1.10;
  $('vol-value').textContent = percent(s.volatility);
  $('shock-value').textContent = s.shock === null ? 'Unavailable' : `${s.shock.toFixed(2)}×`;
  $('drawdown-value').textContent = percent(s.drawdown);
  $('vol-value').className = volPass ? '' : 'fail';
  $('shock-value').className = shockPass ? '' : 'fail';
  $('drawdown-value').className = s.drawdown_pass ? '' : 'fail';
  $('close-date').textContent = `Close ${s.date}`;
  $('signal-card').className = `signal-card ${status.fresh ? (allowed ? 'go' : 'stop') : 'waiting'}`;
  $('signal-card').setAttribute('aria-busy', 'false');
  $('signal-name').textContent = status.fresh ? (allowed ? 'Hold TQQQ' : 'Hold TLT') : 'Waiting for fresh data';
  $('signal-scope').textContent = status.fresh ? 'Confirmed base allocation' : `Last available signal · ${s.signal}`;
  $('gate-pills').replaceChildren();
  for (const [text, passes] of [
    [`Vol ${percent(s.volatility)} ${volPass ? '<' : '≥'} 35%`, volPass],
    [s.shock === null ? 'Shock unavailable' : `Shock ${s.shock.toFixed(2)} ${shockPass ? '<' : '≥'} 1.10`, shockPass],
    [`QQQ drawdown ${percent(s.drawdown)}`, s.drawdown_pass],
  ]) {
    const pill = document.createElement('span');
    pill.className = `pill ${passes ? '' : 'fail'}`;
    pill.textContent = text;
    $('gate-pills').append(pill);
  }
  const blocked = [];
  if (!volPass) blocked.push('absolute volatility');
  if (!shockPass) blocked.push('volatility shock');
  if (!s.drawdown_pass) blocked.push('drawdown protection');
  let explanation = allowed ? 'The confirmed rule allows TQQQ.' : 'The confirmed rule holds the defensive allocation in TLT.';
  if (s.pending) explanation += ' An opposite verdict has appeared for one close. A second consecutive close is needed to change the allocation.';
  else explanation += blocked.length ? ` Currently blocked by ${blocked.join(' and ')}.` : ' All three gates pass together.';
  explanation += ` This allocation was confirmed on ${fullDate(s.changed_on)}.`;
  $('signal-explanation').textContent = explanation;
  const execution = new Date(s.execution_open);
  $('signal-timing').textContent = `That change's execution open was ${execution.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York', timeZoneName: 'short' })}. New confirmed changes use the following trading session's open.`;
  $('data-warning').hidden = status.fresh;
  if (!status.fresh) {
    $('data-warning').textContent = status.expired ? 'The published calendar has expired. A data refresh is required before using this signal.' : `Latest available close is ${fullDate(s.date)}. The completed ${status.expected ? fullDate(status.expected) : 'latest'} session has not been published yet. Refresh later before using the signal.`;
  }
  const checked = new Date(published.checked_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York', timeZoneName: 'short' });
  $('last-checked').textContent = `${published.source_label} · ${published.source} · Last remote check ${checked}. Scheduled refreshes run twice after U.S. trading hours.`;
}

async function load() {
  if (busy) return;
  busy = true;
  $('refresh').disabled = true;
  $('refresh').textContent = 'Checking…';
  try {
    const url = new URL('./qqq-data.json', import.meta.url);
    url.searchParams.set('checked', Date.now());
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) throw new Error('The published signal could not be loaded.');
    published = validateData(await response.json());
    render();
  } catch (error) {
    $('data-warning').hidden = false;
    $('data-warning').textContent = `${error.message} Refresh again when your connection is available.`;
    $('signal-card').className = 'signal-card waiting';
    $('signal-card').setAttribute('aria-busy', 'false');
    $('signal-name').textContent = 'Signal unavailable';
    $('signal-explanation').textContent = published ? `The last file used close ${published.signal.date}. A fresh check is needed.` : 'An updated signal is needed before acting.';
  } finally {
    busy = false;
    $('refresh').disabled = false;
    $('refresh').textContent = 'Refresh signal';
  }
}

$('refresh').addEventListener('click', load);
document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
setInterval(() => { if (!document.hidden) load(); }, 300_000);
load();
