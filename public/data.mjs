export function validateData(data) {
  const s = data?.signal;
  if (data?.schema !== 4 || data.symbol !== 'QQQ' || data.execution !== 'next_session_open' || !s || !['TQQQ', 'TLT'].includes(s.signal) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(s.date) ||
      !Number.isFinite(s.volatility) || !Number.isFinite(s.drawdown) ||
      (s.shock !== null && !Number.isFinite(s.shock)) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(s.changed_on) ||
      !Number.isFinite(Date.parse(`${s.date}T12:00:00Z`)) ||
      !Number.isFinite(Date.parse(`${s.changed_on}T12:00:00Z`)) ||
      !Number.isFinite(Date.parse(s.execution_open)) ||
      typeof s.pending !== 'boolean' || typeof s.target !== 'boolean' ||
      s.target !== (s.signal === 'TQQQ') || s.volatility < 0 || s.drawdown <= -1 || s.drawdown > 0 ||
      (s.shock !== null && s.shock < 0) ||
      typeof s.drawdown_pass !== 'boolean' || !Array.isArray(data.calendar) ||
      data.calendar.length === 0 || !Number.isFinite(Date.parse(data.checked_at))) {
    throw new Error('The published signal file could not be validated.');
  }
  if (!data.calendar.every((row, i) => /^\d{4}-\d{2}-\d{2}$/.test(row.date) &&
      Number.isFinite(Date.parse(row.open)) && Number.isFinite(Date.parse(row.close)) && Date.parse(row.open) < Date.parse(row.close) && (i === 0 || row.date > data.calendar[i - 1].date))) {
    throw new Error('The exchange calendar could not be validated.');
  }
  return data;
}

export function freshness(data, now = Date.now()) {
  const settled = data.calendar.filter(row => Date.parse(row.close) + 15 * 60_000 <= now);
  const expected = settled.at(-1)?.date;
  const expired = now > Date.parse(data.calendar.at(-1).close) + 24 * 60 * 60_000;
  return { fresh: Boolean(expected && data.signal.date === expected && !expired), expected, expired };
}
