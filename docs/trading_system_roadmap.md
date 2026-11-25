# Trading System Roadmap

## Common comparison layer

Each independent trader should publish a versioned result contract rather than import
another trader's strategy implementation. Required fields are:

- system and mandate;
- completed-session timestamp and data provenance;
- research, shadow, or production status;
- investable universe and human-executable target weights;
- earliest valid execution time and assumed costs;
- development, validation, holdout, and forward metrics;
- uncertainty, multiple-testing, and stability diagnostics;
- overlap and return correlation to existing systems;
- explicit `action_authorized` state, which remains false until a separate policy layer
  is deliberately designed.

The future comparison service should align contracts by session, replay combined
portfolios without lookahead, report marginal contribution and conflict, and refuse to
combine stale or unaudited records. It should not optimize ensemble weights against the
same holdouts used to create the component systems.

## Candidate independent systems

1. **Reversion Trader**: 2-20 session long-only mean reversion in liquid ETFs and large
   caps. This is explicitly different from Swing Trader's momentum horizon.
2. **Fundamental Trader**: quarterly quality, value, and profitability selection from
   point-in-time SEC filings, with filing-date lags and delisting-aware universes.
3. **Event Drift Trader**: human-executable post-earnings and public-filing drift with
   strict event timestamps; no pre-event prediction and no paid estimates required.
4. **Carry and Income Trader**: cash, Treasury, credit, and dividend ETF allocation based
   on observable yield carry and drawdown constraints, without derivatives.
5. **Global Allocation Trader**: country, region, and style ETF relative value with a
   monthly horizon; plain momentum remains a control so it does not duplicate Swing.

## Build order

Reversion Trader is the strongest next orthogonal experiment because its horizon and
economic mechanism differ from all three current systems. Fundamental Trader should
follow after a reliable point-in-time filing dataset and universe history are designed.
Event Drift requires the same timestamp discipline. Carry and Global Allocation are
lower priority because they risk greater overlap with Trade-bot and Swing Trader.

Every new repository must start with a frozen protocol, named controls, a survivor-bias
statement, a full failed-hypothesis registry, and a serialized comparison contract.
