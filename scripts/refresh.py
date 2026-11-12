"""Publish the confirmed QQQ gate and exchange-calendar freshness information."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import stdev
from zoneinfo import ZoneInfo
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

import exchange_calendars as xcals

ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo('America/New_York')


def exchange_calendar(now):
    return xcals.get_calendar('XNYS', start='1985-01-01',
                              end=(now + timedelta(days=400)).date().isoformat())


def latest_completed(calendar, now):
    settled = calendar.schedule[calendar.schedule['close'] <= now - timedelta(minutes=15)]
    return settled.index[-1].date().isoformat()


def settled_meta_row(result, now, completed, calendar):
    meta = result.get('meta') or {}
    stamp, price = meta.get('regularMarketTime'), meta.get('regularMarketPrice')
    if not isinstance(stamp, (int, float)) or not isinstance(price, (int, float)) or not math.isfinite(stamp) or not math.isfinite(price) or price <= 0:
        return None
    when = datetime.fromtimestamp(stamp, timezone.utc)
    close = calendar.session_close(completed)
    if when.astimezone(NY).date().isoformat() != completed or when < close or when > now or now < close + timedelta(minutes=15):
        return None
    return completed, float(price)


def read_yahoo(now, completed, symbol='QQQ', events=False):
    end = int((now + timedelta(days=1)).timestamp())
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol, safe="")}?period1=0&period2={end}&interval=1d&events=splits'
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 QQQ-Signal/3.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)['chart']['result'][0]
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    recovered = settled_meta_row(result, now, completed, exchange_calendar(now))
    rows = []
    for stamp, value in zip(result['timestamp'], result['indicators']['quote'][0]['close']):
        day = datetime.fromtimestamp(stamp, timezone.utc).astimezone(NY).date().isoformat()
        if value is None and recovered and day == completed:
            value = recovered[1]
        if day <= completed and value is not None:
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'Invalid QQQ close on {day}')
            rows.append((day, float(value)))
    if recovered and rows and rows[-1][0] < completed:
        rows.append(recovered)
    if len(rows) < 252 or len({day for day, _ in rows}) != len(rows):
        raise ValueError('QQQ history is incomplete or contains duplicate sessions')
    if events:
        splits = [dict(date=datetime.fromtimestamp(item['date'], timezone.utc).astimezone(NY).date().isoformat(), ratio=item['numerator'] / item['denominator']) for item in result.get('events', {}).get('splits', {}).values()]
        return rows, sorted(splits, key=lambda item: item['date'])
    return rows


def compute(rows):
    closes = [value for _, value in rows]
    returns = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    if len(returns) < 251:
        raise ValueError('Need at least 252 daily closes for two confirmed observations')
    protection = True
    previous = None
    streak = 0
    target = None
    changed = None
    changed_index = None
    history = []
    for i in range(250, len(closes)):
        fast = stdev(returns[i - 20:i])
        slow = stdev(returns[i - 250:i])
        volatility = fast * math.sqrt(252)
        ratio = fast / slow if slow > 1e-12 else None
        drawdown = closes[i] / max(closes[i - 249:i + 1]) - 1
        if drawdown < -.20:
            protection = False
        elif drawdown > -.10:
            protection = True
        checks = [volatility < .35, ratio is not None and ratio < 1.10, protection]
        verdict = all(checks)
        streak = min(streak + 1, 2) if previous == verdict else 1
        previous = verdict
        if streak == 2 and target != verdict:
            target = verdict
            changed = rows[i][0]
            changed_index = i
        history.append(dict(date=rows[i][0], target=target, volatility=volatility,
                            shock=ratio, drawdown=drawdown, drawdown_pass=protection,
                            raw_verdict=verdict, confirmation_count=streak))
    latest = history[-1]
    if target is None:
        raise ValueError('The signal has not completed its confirmation period')
    latest.update(signal='TQQQ' if target else 'TLT', changed_on=changed,
                  sessions_in_state=len(closes) - changed_index,
                  pending=latest['raw_verdict'] != target)
    return latest, history


def publish(now=None):
    now = now or datetime.now(timezone.utc)
    calendar = exchange_calendar(now)
    completed = latest_completed(calendar, now)
    rows = read_yahoo(now, completed)
    observed = rows[-1][0]
    expected_rows = calendar.sessions_in_range(rows[-300][0], observed)
    if [session.date().isoformat() for session in expected_rows] != [day for day, _ in rows[-300:]]:
        raise ValueError('A recent QQQ session is missing. Retaining the last published signal.')
    tqqq, splits = read_yahoo(now, completed, 'TQQQ', events=True)
    if tqqq[-1][0] != observed:
        raise ValueError('TQQQ and QQQ closes are not aligned')
    signal, history = compute(rows)
    next_session = calendar.next_session(signal['changed_on'])
    signal['execution_open'] = calendar.session_open(next_session).isoformat()
    signal['next_execution_open'] = calendar.session_open(calendar.next_session(observed)).isoformat()
    destination = ROOT / 'public/qqq-data.json'
    if destination.exists():
        prior = json.loads(destination.read_text())
        if prior['signal']['date'] > observed:
            raise ValueError('Provider history regressed. Retaining the newer published signal.')
    schedule = calendar.schedule.loc[(now - timedelta(days=450)).date().isoformat():
                                    (now + timedelta(days=370)).date().isoformat()]
    payload = dict(schema=4, source='Yahoo Finance', symbol='QQQ', execution='next_session_open',
                   source_label='Invesco QQQ ETF (QQQ)', checked_at=now.isoformat(),
                   expected_close=completed, fresh=observed == completed,
                   signal=signal, tqqq=dict(date=observed, close=tqqq[-1][1], splits=splits),
                   calendar=[dict(date=day.date().isoformat(), open=row['open'].isoformat(), close=row['close'].isoformat())
                             for day, row in schedule.iterrows()],
                   recent=history[-8:])
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    os.replace(temporary, destination)
    shock_text = f'{signal["shock"]:.3f}' if signal['shock'] is not None else 'undefined'
    print(f'{observed}: {signal["signal"]}; vol {signal["volatility"]:.2%}; '
          f'shock {shock_text}; QQQ drawdown {signal["drawdown"]:.2%}', flush=True)
    if observed != completed:
        print(f'::warning::Provider is behind the latest completed session, {completed}. The page will show a data warning.')


if __name__ == '__main__':
    try:
        publish()
    except Exception as error:
        print(f'Signal refresh failed: {error}', file=sys.stderr)
        sys.exit(1)
