import numpy as np
import pandas as pd
import pytest

from rotation_trader.backtest import run_backtest


@pytest.mark.parametrize("cost", [0., 10., 100.])
def test_funded_execution_matches_independent_share_ledger(cost):
    rng = np.random.default_rng(713)
    dates = pd.bdate_range("2026-01-05", periods=120)
    p = 100 * np.exp(np.cumsum(rng.normal(0, .04, (120, 3)), axis=0))
    targets = np.repeat(rng.dirichlet([1., 1., 1., 1.], size=12)[:, :3], 10, axis=0)
    prices = pd.DataFrame(p, index=dates)
    weights = pd.DataFrame(targets, index=dates)
    result = run_backtest(prices, weights, one_way_cost_bps=cost)
    units, cash, previous = np.zeros(3), 1., np.zeros(3)
    values = []
    for i in range(len(p)):
        desired = targets[i-1] if i else np.zeros(3)
        pre = float(units @ p[i] + cash)
        if not np.array_equal(desired, previous):
            low, high = 0., pre
            for _ in range(70):
                post = (low + high) / 2
                balance = post + cost/10000 * np.abs(desired*post - units*p[i]).sum()
                if balance > pre:
                    high = post
                else:
                    low = post
            units = desired * post / p[i]
            cash = post * (1-desired.sum())
        previous = desired.copy()
        values.append(float(units @ p[i] + cash))
    np.testing.assert_allclose(result.equity, values, rtol=1e-11, atol=1e-12)
