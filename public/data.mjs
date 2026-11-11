export function validateData(data) {
  const s = data?.signal;
  if (data?.schema !== 1 || !s || !['TQQQ', 'TLT'].includes(s.signal) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(s.date) ||
      !Number.isFinite(s.volatility) || !Number.isFinite(s.drawdown) ||
      (s.shock !== null && !Number.isFinite(s.shock)) ||
      typeof s.drawdown_pass !== 'boolean' || !Array.isArray(data.calendar) ||
      data.calendar.length === 0 || !Number.isFinite(Date.parse(data.checked_at))) {
    throw new Error('The published signal file could not be validated.');
  }
  if (!data.calendar.every(row => /^\d{4}-\d{2}-\d{2}$/.test(row.date) && Number.isFinite(Date.parse(row.close)))) {
    throw new Error('The exchange calendar could not be validated.');
  }
  return data;
}

export function freshness(data, now = Date.now()) {
  const settled = data.calendar.filter(row => Date.parse(row.close) + 15 * 60_000 <= now);
  const expected = settled.at(-1)?.date;
  const expired = now > Date.parse(data.calendar.at(-1).close) + 24 * 60 * 60_000;
  return { fresh: Boolean(expected && data.signal.date >= expected && !expired), expected, expired };
}
