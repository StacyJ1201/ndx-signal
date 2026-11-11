import assert from 'node:assert/strict';
import test from 'node:test';
import { freshness, validateData } from '../public/data.mjs';

const fixture = {
  schema: 1, checked_at: '2026-11-27T18:20:00Z',
  signal: { signal: 'TLT', target: false, pending: false, date: '2026-11-25',
    changed_on: '2026-11-25', execution_close: '2026-11-27T18:00:00Z',
    volatility: .30, shock: 1.3, drawdown: -.1, drawdown_pass: true },
  calendar: [
    { date: '2026-11-25', close: '2026-11-25T21:00:00Z' },
    { date: '2026-11-27', close: '2026-11-27T18:00:00Z' },
    { date: '2026-11-30', close: '2026-11-30T21:00:00Z' },
  ],
};

test('holiday and early-close freshness use exchange sessions', () => {
  assert.equal(freshness(fixture, Date.parse('2026-11-27T18:14:00Z')).fresh, true);
  assert.equal(freshness(fixture, Date.parse('2026-11-27T18:16:00Z')).fresh, false);
});
test('outdated calendars fail closed', () => {
  assert.equal(freshness(fixture, Date.parse('2027-01-01T00:00:00Z')).fresh, false);
});
test('malformed or non-finite signal data is rejected', () => {
  assert.equal(validateData(fixture), fixture);
  assert.throws(() => validateData({ ...fixture, signal: { ...fixture.signal, volatility: Infinity } }));
  assert.throws(() => validateData({ ...fixture, signal: { ...fixture.signal, target: true } }));
  assert.throws(() => validateData({ ...fixture, signal: { ...fixture.signal, execution_close: 'invalid' } }));
  assert.throws(() => validateData({ ...fixture, calendar: [{ date: '2026-11-27', close: 'invalid' }] }));
});
