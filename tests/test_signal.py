from datetime import datetime, timezone
from pathlib import Path
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh import compute, exchange_calendar, latest_completed, settled_meta_row


class SignalTests(unittest.TestCase):
    def test_null_bar_recovery_requires_a_settled_regular_close(self):
        now = datetime(2026, 11, 27, 18, 16, tzinfo=timezone.utc)
        calendar = exchange_calendar(now)
        close = calendar.session_close('2026-11-27')
        result = {'meta': {'regularMarketTime': close.timestamp(), 'regularMarketPrice': 123.45}}
        self.assertEqual(settled_meta_row(result, now, '2026-11-27', calendar), ('2026-11-27', 123.45))
        self.assertIsNone(settled_meta_row(result, now.replace(minute=14), '2026-11-27', calendar))
        result['meta']['regularMarketTime'] -= 60
        self.assertIsNone(settled_meta_row(result, now, '2026-11-27', calendar))
        result['meta']['regularMarketPrice'] = float('nan')
        self.assertIsNone(settled_meta_row(result, now, '2026-11-27', calendar))

    def rows(self, closes):
        return [(f'{2000 + i // 300:04d}-{1 + (i % 300) // 25:02d}-{1 + i % 25:02d}', value)
                for i, value in enumerate(closes)]

    def test_sample_volatility_and_confirmation(self):
        closes = [100.0]
        for i in range(270):
            closes.append(closes[-1] * (1 + (.005 if i % 2 else -.005)))
        signal, history = compute(self.rows(closes))
        self.assertEqual(signal['signal'], 'TQQQ')
        returns = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))][-20:]
        mean = sum(returns) / len(returns)
        expected = math.sqrt(sum((r-mean)**2 for r in returns) / 19) * math.sqrt(252)
        self.assertAlmostEqual(signal['volatility'], expected)
        closes.append(closes[-1] * .90)
        first, _ = compute(self.rows(closes))
        self.assertEqual(first['signal'], 'TQQQ')
        self.assertTrue(first['pending'])
        closes.append(closes[-1] * .90)
        second, _ = compute(self.rows(closes))
        self.assertEqual(second['signal'], 'TLT')

    def test_drawdown_state_retains_its_prior_value(self):
        closes = [100 + (i % 2) * .1 for i in range(270)]
        closes.extend([75, 88, 92])
        _, history = compute(self.rows(closes))
        self.assertEqual([row['drawdown_pass'] for row in history[-3:]], [False, False, True])

    def test_flat_history_fails_closed(self):
        signal, _ = compute(self.rows([100.] * 270))
        self.assertEqual(signal['signal'], 'TLT')
        self.assertIsNone(signal['shock'])

    def test_holiday_early_close_and_settlement_buffer(self):
        now = datetime(2026, 11, 27, 18, 14, tzinfo=timezone.utc)
        calendar = exchange_calendar(now)
        self.assertEqual(latest_completed(calendar, now), '2026-11-25')
        self.assertEqual(calendar.session_open(calendar.next_session('2026-11-25')).isoformat(), '2026-11-27T14:30:00+00:00')
        self.assertEqual(latest_completed(calendar, now.replace(minute=16)), '2026-11-27')


if __name__ == '__main__':
    unittest.main()
