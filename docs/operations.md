# Operations

## Initial setup

```bash
poetry install --sync
```

## Daily completed-session run

```bash
poetry run rotation-trader run
poetry run rotation-trader audit
```

The run downloads through the latest completed regular session, executes the registered
research, writes hash-locked artifacts, and records an idempotent shadow decision. It
does not place or authorize a trade.

## Separate steps

```bash
poetry run rotation-trader fetch-data
poetry run rotation-trader research
poetry run rotation-trader record-shadow
poetry run rotation-trader show
```

## Dashboard

```bash
poetry run rotation-trader dashboard --port 8503
```

Open `http://localhost:8503`. Stop the foreground process with `Ctrl-C`.

## Failure behavior

- Missing or stale primary-sector data stops the run.
- A hash mismatch stops research loading or shadow recording.
- A run without a selected candidate cannot create a shadow decision.
- Repeating a shadow command for the same date, variant, and protocol is idempotent.
- Failed historical gates remain visible; no fallback strategy is silently substituted.

## Verification

```bash
poetry run pytest -q
poetry run ruff check .
poetry run rotation-trader audit
```
