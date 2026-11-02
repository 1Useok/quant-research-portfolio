"""Smoke test: engine runs on the synthetic sample and returns sane numbers.

Run from this folder:  python test_portfolio_engine.py
"""
import numpy as np

from portfolio_engine import calculate_portfolio_data, load_sample_panel


def main():
    panel = load_sample_panel()
    assert {'Date', 'Ticker', 'daily_ret', 'strategy_score', 'Size Decile'} <= set(panel.columns)

    for position in (1, -1, 0):
        out = calculate_portfolio_data(n_stocks=2, position=position, refund_period='monthly',
                                       n_months=12, current_date='2025-06-30', panel=panel)
        assert 'error' not in out, out
        m = out['metrics']
        assert m['maxDrawdown'] <= 0
        assert np.isfinite(m['yearlyAvgReturn']) and np.isfinite(m['sharpeRatio'])
        assert len(out['navHistory']) > 50
        assert out['navHistory'][0]['nav_value'] == 1000.0
        print(f'position={position:+d} ok  CAGR={m["yearlyAvgReturn"]:.2f}%  MDD={m["maxDrawdown"]:.2f}%')

    print('all checks passed')


if __name__ == '__main__':
    main()
