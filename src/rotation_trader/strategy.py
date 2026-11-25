from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252
CYCLICAL_SECTORS = frozenset({"XLB", "XLE", "XLF", "XLI", "XLK", "XLY"})
DEFENSIVE_SECTORS = frozenset({"XLP", "XLU", "XLV"})
SECTOR_TRANSITION_PAIRS = (
    ("XLY", "XLP"),
    ("XLI", "XLU"),
    ("XLK", "XLU"),
    ("XLF", "XLV"),
    ("XLE", "XLK"),
    ("XLB", "XLK"),
)
CONTEXT_ECHO_MAP = {
    "XLB": ("DBC", "GLD"),
    "XLE": ("DBC",),
    "XLF": ("IWM", "RSP", "HYG"),
    "XLI": ("IWM", "RSP"),
    "XLK": ("QQQ", "SMH"),
    "XLP": ("IEF", "TLT"),
    "XLU": ("IEF", "TLT"),
    "XLV": ("IEF",),
    "XLY": ("QQQ", "RSP"),
}


@dataclass(frozen=True)
class VariantSpec:
    family: str
    momentum_lookbacks: tuple[int, ...] = (126, 252)
    momentum_weights: tuple[float, ...] = (0.5, 0.5)
    top_n: int = 3
    cadence: str = "monthly"
    weighting: str = "equal"
    absolute_gate: bool = True
    sector_trend_days: int | None = None
    benchmark_trend_days: int | None = None
    acceleration_days: int = 63
    acceleration_weight: float = 0.0
    rank_velocity_days: int = 21
    rank_velocity_weight: float = 0.0
    persistence_days: int = 63
    persistence_weight: float = 0.0
    reversal_days: int = 21
    reversal_weight: float = 0.0
    group_rotation_days: int = 63
    group_rotation_weight: float = 0.0
    breadth_trend_days: int = 200
    breadth_threshold: float | None = None
    dispersion_days: int = 126
    dispersion_penalty: float = 0.0
    rank_buffer: int = 0
    minimum_holding_rebalances: int = 0
    daily_emergency_exit: bool = False
    risk_off_mode: str = "cash"
    target_volatility: float | None = None
    rank_crossing_days: int = 21
    rank_crossing_weight: float = 0.0
    pair_transition_days: int = 63
    pair_transition_weight: float = 0.0
    confirmation_min_signals: int = 0
    confirmation_weight: float = 0.0
    leader_crowding_penalty: float = 0.0
    correlation_days: int = 63
    correlation_rotation_scale: float = 0.0
    context_echo_days: int = 126
    context_echo_weight: float = 0.0
    dynamic_top_n: bool = False
    minimum_holdings: int = 2
    maximum_holdings: int = 5
    score_temperature: float = 1.0
    maximum_sector_weight: float = 1.0
    timing_mode: str = "binary"
    timing_fast_days: int = 63
    timing_slow_days: int = 200
    timing_confirmation_days: int = 5
    watch_exposure: float = 0.75
    warning_exposure: float = 0.50
    defensive_exposure: float = 0.20
    market_drawdown_limit: float | None = None
    rebalance_on_timing_transition: bool = False

    @property
    def variant_id(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        return f"{self.family}-{hashlib.sha256(payload).hexdigest()[:12]}"

    @property
    def is_rotation_specific(self) -> bool:
        return (
            any(
                value != 0.0
                for value in (
                    self.acceleration_weight,
                    self.rank_velocity_weight,
                    self.persistence_weight,
                    self.reversal_weight,
                    self.group_rotation_weight,
                    self.dispersion_penalty,
                    self.rank_crossing_weight,
                    self.pair_transition_weight,
                    self.confirmation_weight,
                    self.leader_crowding_penalty,
                    self.correlation_rotation_scale,
                    self.context_echo_weight,
                )
            )
            or self.breadth_threshold is not None
            or self.dynamic_top_n
            or self.weighting in {"score_softmax", "score_inverse_volatility"}
            or self.timing_mode == "staged"
        )


@dataclass(frozen=True)
class StrategyRun:
    target_weights: pd.DataFrame
    score: pd.DataFrame
    ranks: pd.DataFrame
    eligible: pd.DataFrame
    rebalance: pd.Series
    diagnostics: pd.DataFrame


class FeatureCache:
    def __init__(
        self,
        close: pd.DataFrame,
        benchmark: pd.Series,
        context: pd.DataFrame | None = None,
    ):
        self.close = close.astype(float)
        self.benchmark = benchmark.astype(float)
        self.context = (
            pd.DataFrame(index=self.close.index)
            if context is None
            else context.reindex(self.close.index).astype(float)
        )
        self._returns: dict[tuple[int, int], pd.DataFrame] = {}
        self._volatility: dict[int, pd.DataFrame] = {}
        self._trend: dict[int, pd.DataFrame] = {}
        self._breadth: dict[int, pd.Series] = {}
        self._benchmark_trend: dict[int, pd.Series] = {}
        self._pair_transition: dict[int, pd.DataFrame] = {}
        self._average_correlation: dict[int, pd.Series] = {}
        self._context_echo: dict[int, pd.DataFrame] = {}

    def returns(self, lookback: int, skip: int = 0) -> pd.DataFrame:
        key = (lookback, skip)
        if key not in self._returns:
            self._returns[key] = (
                self.close.shift(skip).div(self.close.shift(lookback + skip)).sub(1.0)
            )
        return self._returns[key]

    def volatility(self, days: int = 63) -> pd.DataFrame:
        if days not in self._volatility:
            self._volatility[days] = self.close.pct_change(fill_method=None).rolling(
                days
            ).std() * np.sqrt(TRADING_DAYS)
        return self._volatility[days]

    def trend(self, days: int) -> pd.DataFrame:
        if days not in self._trend:
            self._trend[days] = self.close > self.close.rolling(days).mean()
        return self._trend[days]

    def breadth(self, days: int) -> pd.Series:
        if days not in self._breadth:
            self._breadth[days] = self.trend(days).mean(axis=1)
        return self._breadth[days]

    def benchmark_trend(self, days: int) -> pd.Series:
        if days not in self._benchmark_trend:
            self._benchmark_trend[days] = self.benchmark > self.benchmark.rolling(days).mean()
        return self._benchmark_trend[days]

    def pair_transition(self, days: int) -> pd.DataFrame:
        if days not in self._pair_transition:
            self._pair_transition[days] = _pair_transition_signal(self.close, days)
        return self._pair_transition[days]

    def average_correlation(self, days: int) -> pd.Series:
        if days not in self._average_correlation:
            returns = self.close.pct_change(fill_method=None)
            pairs = [
                returns[left].rolling(days).corr(returns[right])
                for position, left in enumerate(returns.columns)
                for right in returns.columns[position + 1 :]
            ]
            self._average_correlation[days] = pd.concat(pairs, axis=1).mean(axis=1)
        return self._average_correlation[days]

    def context_echo(self, days: int) -> pd.DataFrame:
        if days not in self._context_echo:
            self._context_echo[days] = _context_echo_signal(
                self.context,
                self.close.columns,
                days,
            )
        return self._context_echo[days]


def build_strategy(
    cache: FeatureCache,
    spec: VariantSpec,
) -> StrategyRun:
    close = cache.close
    base_raw = sum(
        weight * cache.returns(lookback)
        for lookback, weight in zip(
            spec.momentum_lookbacks,
            spec.momentum_weights,
            strict=True,
        )
    )
    base_score = _cross_sectional_z(base_raw)
    score = base_score.copy()

    acceleration = cache.returns(spec.acceleration_days) - cache.returns(
        spec.acceleration_days
    ).shift(spec.acceleration_days)
    acceleration_score = _cross_sectional_z(acceleration)

    base_rank = base_raw.rank(axis=1, ascending=False, method="average")
    rank_velocity = base_rank.shift(spec.rank_velocity_days) - base_rank
    rank_velocity_score = _cross_sectional_z(rank_velocity)

    top_third = base_rank <= max(1, int(np.ceil(close.shape[1] / 3)))
    persistence = top_third.astype(float).rolling(spec.persistence_days).mean()
    persistence_score = _cross_sectional_z(persistence)

    reversal = -cache.returns(spec.reversal_days)
    reversal_score = _cross_sectional_z(reversal)

    group_signal = _group_rotation_signal(
        close,
        days=spec.group_rotation_days,
    )
    crossing = (
        (base_rank <= spec.top_n)
        & (base_rank.shift(spec.rank_crossing_days) > spec.top_n)
    ).astype(float)
    crossing -= (
        (base_rank > spec.top_n)
        & (base_rank.shift(spec.rank_crossing_days) <= spec.top_n)
    ).astype(float)
    crossing_score = _cross_sectional_z(crossing)

    pair_score = cache.pair_transition(spec.pair_transition_days)
    context_score = cache.context_echo(spec.context_echo_days)
    confirmation_count = sum(
        component.gt(0.0).astype(float)
        for component in (
            acceleration_score,
            rank_velocity_score,
            persistence_score,
            pair_score,
        )
    )
    confirmation_score = _cross_sectional_z(
        confirmation_count.where(
            confirmation_count >= spec.confirmation_min_signals,
            0.0,
        )
    )
    rotation_score = (
        spec.acceleration_weight * acceleration_score
        + spec.rank_velocity_weight * rank_velocity_score
        + spec.persistence_weight * persistence_score
        + spec.reversal_weight * reversal_score
        + spec.group_rotation_weight * group_signal
        + spec.rank_crossing_weight * crossing_score
        + spec.pair_transition_weight * pair_score
        + spec.confirmation_weight * confirmation_score
        + spec.context_echo_weight * context_score
    )
    average_correlation = cache.average_correlation(spec.correlation_days)
    correlation_multiplier = (
        1.0
        - spec.correlation_rotation_scale
        * average_correlation.clip(lower=0.0, upper=1.0)
    ).clip(lower=0.0, upper=1.0)
    score += rotation_score.mul(correlation_multiplier, axis=0)
    score -= spec.leader_crowding_penalty * _leader_crowding(base_raw, base_rank)

    eligible = close.notna() & base_raw.notna()
    if spec.absolute_gate:
        eligible &= base_raw > 0.0
    if spec.sector_trend_days is not None:
        eligible &= cache.trend(spec.sector_trend_days)

    breadth = cache.breadth(spec.breadth_trend_days)
    risk_on = pd.Series(True, index=close.index)
    if spec.benchmark_trend_days is not None:
        risk_on &= cache.benchmark_trend(spec.benchmark_trend_days).fillna(False)
    if spec.breadth_threshold is not None:
        risk_on &= breadth >= spec.breadth_threshold

    dispersion = cache.returns(spec.dispersion_days).std(axis=1)
    dispersion_z = _rolling_z(dispersion, 252)
    exposure = (1.0 - spec.dispersion_penalty * dispersion_z.clip(lower=0.0)).clip(
        lower=max(0.0, 1.0 - spec.dispersion_penalty),
        upper=1.0,
    )
    exposure = exposure.fillna(1.0)

    timing_score, timing_stage, timing_exposure = _timing_exposure(
        cache,
        base_raw,
        spec,
    )
    if spec.timing_mode == "staged":
        exposure *= timing_exposure
        risk_on &= timing_exposure > 0.0
    else:
        timing_score = risk_on.astype(float)
        timing_stage = risk_on.astype(int).mul(3)
        timing_exposure = risk_on.astype(float)

    ranks = score.where(eligible).rank(axis=1, ascending=False, method="first")
    rebalance = rebalance_mask(close.index, spec.cadence)
    if spec.rebalance_on_timing_transition:
        rebalance |= timing_stage.ne(timing_stage.shift(1)).fillna(False)
    target_count = _dynamic_holding_count(score, eligible, spec)
    selected = _stateful_selection(
        ranks,
        eligible,
        rebalance,
        risk_on,
        top_n=target_count,
        rank_buffer=spec.rank_buffer,
        minimum_holding_rebalances=spec.minimum_holding_rebalances,
        daily_emergency_exit=spec.daily_emergency_exit,
    )
    desired = _size_selected(
        selected,
        cache.volatility(63),
        score,
        spec.weighting,
        temperature=spec.score_temperature,
        maximum_weight=spec.maximum_sector_weight,
    )
    desired = desired.mul(exposure, axis=0)
    if spec.target_volatility is not None:
        desired = _apply_volatility_target(
            desired,
            close.pct_change(fill_method=None),
            spec.target_volatility,
        )
    target = _latch_weights(
        desired,
        selected,
        rebalance,
        risk_on,
        spec,
    )
    diagnostics = pd.DataFrame(
        {
            "breadth": breadth,
            "dispersion": dispersion,
            "dispersion_z": dispersion_z,
            "risk_on": risk_on,
            "exposure_scalar": exposure,
            "timing_score": timing_score,
            "timing_stage": timing_stage,
            "timing_exposure": timing_exposure,
            "target_holding_count": target_count,
            "group_rotation_signal": _group_scalar(close, spec.group_rotation_days),
            "average_sector_correlation": average_correlation,
            "rotation_signal_multiplier": correlation_multiplier,
            "confirmation_share": confirmation_count.ge(
                max(spec.confirmation_min_signals, 1)
            ).mean(axis=1),
            "context_echo_available_share": context_score.ne(0.0).mean(axis=1),
            "leader_count": (ranks <= spec.top_n).sum(axis=1),
            "eligible_count": eligible.sum(axis=1),
        }
    )
    return StrategyRun(target, score, ranks, eligible, rebalance, diagnostics)


def rebalance_mask(index: pd.DatetimeIndex, cadence: str) -> pd.Series:
    sessions = pd.Series(False, index=index)
    if cadence == "monthly":
        positions = (
            pd.Series(np.arange(len(index)), index=index).groupby([index.year, index.month]).max()
        )
        sessions.iloc[positions.to_numpy(dtype=int)] = True
    elif cadence in {"weekly", "biweekly"}:
        iso = index.isocalendar()
        positions = (
            pd.Series(np.arange(len(index)), index=index)
            .groupby([iso.year.to_numpy(), iso.week.to_numpy()])
            .max()
        )
        chosen = positions.to_numpy(dtype=int)
        if cadence == "biweekly":
            chosen = chosen[::2]
        sessions.iloc[chosen] = True
    else:
        raise ValueError(f"Unsupported cadence: {cadence}")
    return sessions


def _timing_exposure(
    cache: FeatureCache,
    base_raw: pd.DataFrame,
    spec: VariantSpec,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    index = cache.close.index
    if spec.timing_mode != "staged":
        return (
            pd.Series(1.0, index=index),
            pd.Series(3, index=index, dtype=int),
            pd.Series(1.0, index=index),
        )
    evidence = pd.concat(
        [
            cache.benchmark_trend(spec.timing_fast_days).astype(float),
            cache.benchmark_trend(spec.timing_slow_days).astype(float),
            cache.breadth(spec.timing_slow_days),
            base_raw.gt(0.0).mean(axis=1),
        ],
        axis=1,
    ).mean(axis=1)
    confirmed = evidence.rolling(
        max(1, spec.timing_confirmation_days),
        min_periods=1,
    ).mean()
    stage = pd.Series(
        np.select(
            [confirmed >= 0.75, confirmed >= 0.50, confirmed >= 0.25],
            [3, 2, 1],
            default=0,
        ),
        index=index,
        dtype=int,
    )
    exposure = stage.map(
        {
            3: 1.0,
            2: spec.watch_exposure,
            1: spec.warning_exposure,
            0: spec.defensive_exposure,
        }
    ).astype(float)
    if spec.market_drawdown_limit is not None:
        drawdown = cache.benchmark.div(cache.benchmark.cummax()).sub(1.0)
        exposure = exposure.where(
            drawdown > spec.market_drawdown_limit,
            np.minimum(exposure, spec.defensive_exposure),
        )
        stage = stage.where(drawdown > spec.market_drawdown_limit, 0)
    return confirmed, stage, exposure


def _dynamic_holding_count(
    score: pd.DataFrame,
    eligible: pd.DataFrame,
    spec: VariantSpec,
) -> pd.Series:
    if not spec.dynamic_top_n:
        return pd.Series(spec.top_n, index=score.index, dtype=int)
    positive = (score.gt(0.0) & eligible).sum(axis=1)
    available = eligible.sum(axis=1)
    desired = positive.clip(lower=spec.minimum_holdings, upper=spec.maximum_holdings)
    return desired.where(available >= desired, available).astype(int)


def _stateful_selection(
    ranks: pd.DataFrame,
    eligible: pd.DataFrame,
    rebalance: pd.Series,
    risk_on: pd.Series,
    *,
    top_n: int | pd.Series,
    rank_buffer: int,
    minimum_holding_rebalances: int,
    daily_emergency_exit: bool,
) -> pd.DataFrame:
    rank_values = ranks.to_numpy(dtype=float)
    eligible_values = eligible.to_numpy(dtype=bool)
    rebalance_values = rebalance.to_numpy(dtype=bool)
    risk_values = risk_on.to_numpy(dtype=bool)
    target_counts = (
        np.full(len(ranks.index), top_n, dtype=int)
        if isinstance(top_n, int)
        else top_n.reindex(ranks.index).fillna(0).to_numpy(dtype=int)
    )
    selected_values = np.zeros(rank_values.shape, dtype=bool)
    active = np.zeros(rank_values.shape[1], dtype=bool)
    age = np.zeros(rank_values.shape[1], dtype=int)
    for position in range(len(ranks.index)):
        if daily_emergency_exit:
            active &= eligible_values[position] & risk_values[position]
        if rebalance_values[position]:
            if not risk_values[position]:
                active[:] = False
                age[:] = 0
            else:
                row_ranks = rank_values[position]
                target_count = max(0, int(target_counts[position]))
                must_hold = age < minimum_holding_rebalances
                inside_buffer = np.isfinite(row_ranks) & (
                    row_ranks <= target_count + rank_buffer
                )
                active &= eligible_values[position] & (must_hold | inside_buffer)
                ordered = np.argsort(np.where(np.isfinite(row_ranks), row_ranks, np.inf))
                if int(active.sum()) > target_count:
                    keep = [ticker for ticker in ordered if active[ticker]][:target_count]
                    active[:] = False
                    active[keep] = True
                for ticker_position in ordered:
                    if int(active.sum()) >= target_count:
                        break
                    if (
                        not active[ticker_position]
                        and eligible_values[position, ticker_position]
                        and np.isfinite(row_ranks[ticker_position])
                    ):
                        active[ticker_position] = True
                        age[ticker_position] = 0
                age[active] += 1
                age[~active] = 0
        selected_values[position] = active
    return pd.DataFrame(selected_values, index=ranks.index, columns=ranks.columns)


def _size_selected(
    selected: pd.DataFrame,
    volatility: pd.DataFrame,
    score: pd.DataFrame,
    weighting: str,
    *,
    temperature: float,
    maximum_weight: float,
) -> pd.DataFrame:
    if weighting == "equal":
        count = selected.sum(axis=1).replace(0, np.nan)
        raw = selected.astype(float).div(count, axis=0).fillna(0.0)
    elif weighting == "inverse_volatility":
        inverse = (1.0 / volatility.where(selected)).replace([np.inf, -np.inf], np.nan)
        raw = inverse.div(inverse.sum(axis=1), axis=0).fillna(0.0)
    elif weighting in {"score_softmax", "score_inverse_volatility"}:
        scaled = score.div(max(temperature, 1e-6)).where(selected)
        shifted = scaled.sub(scaled.max(axis=1), axis=0)
        raw = np.exp(shifted).where(selected)
        if weighting == "score_inverse_volatility":
            raw = raw.div(volatility.where(selected)).replace([np.inf, -np.inf], np.nan)
        raw = raw.div(raw.sum(axis=1), axis=0).fillna(0.0)
    else:
        raise ValueError(f"Unsupported weighting: {weighting}")
    return _cap_weights(raw, maximum_weight)


def _cap_weights(weights: pd.DataFrame, maximum_weight: float) -> pd.DataFrame:
    if maximum_weight >= 1.0:
        return weights
    values = weights.to_numpy(dtype=float)
    capped = np.zeros_like(values)
    for row_position, row in enumerate(values):
        active = row > 0.0
        if not active.any():
            continue
        remaining = 1.0
        uncapped = active.copy()
        allocation = np.zeros_like(row)
        while uncapped.any() and remaining > 1e-12:
            raw = row[uncapped]
            proposal = remaining * raw / raw.sum()
            over = proposal > maximum_weight
            positions = np.flatnonzero(uncapped)
            if not over.any():
                allocation[positions] = proposal
                break
            capped_positions = positions[over]
            allocation[capped_positions] = maximum_weight
            remaining -= maximum_weight * len(capped_positions)
            uncapped[capped_positions] = False
        capped[row_position] = allocation
    return pd.DataFrame(capped, index=weights.index, columns=weights.columns)


def _latch_weights(
    desired: pd.DataFrame,
    selected: pd.DataFrame,
    rebalance: pd.Series,
    risk_on: pd.Series,
    spec: VariantSpec,
) -> pd.DataFrame:
    desired_values = desired.to_numpy(dtype=float)
    selected_values = selected.to_numpy(dtype=bool)
    rebalance_values = rebalance.to_numpy(dtype=bool)
    risk_values = risk_on.to_numpy(dtype=bool)
    target_values = np.zeros(desired_values.shape, dtype=float)
    active = np.zeros(desired_values.shape[1], dtype=float)
    defensive_positions = np.asarray(
        [
            position
            for position, ticker in enumerate(desired.columns)
            if ticker in DEFENSIVE_SECTORS
        ],
        dtype=int,
    )
    for position in range(len(desired.index)):
        if rebalance_values[position]:
            if risk_values[position]:
                active = desired_values[position].copy()
            elif spec.risk_off_mode == "defensive":
                allowed = defensive_positions[
                    selected_values[position, defensive_positions]
                    | (desired_values[position, defensive_positions] > 0.0)
                ]
                active[:] = 0.0
                if len(allowed):
                    active[allowed] = 1.0 / len(allowed)
            else:
                active[:] = 0.0
        if spec.daily_emergency_exit:
            active = np.where(selected_values[position], active, 0.0)
            if not risk_values[position] and spec.risk_off_mode == "cash":
                active[:] = 0.0
        target_values[position] = active
    return pd.DataFrame(target_values, index=desired.index, columns=desired.columns)


def _apply_volatility_target(
    weights: pd.DataFrame,
    returns: pd.DataFrame,
    target_volatility: float,
) -> pd.DataFrame:
    portfolio = (weights.shift(1) * returns).sum(axis=1)
    realized = portfolio.rolling(63).std() * np.sqrt(TRADING_DAYS)
    scale = (target_volatility / realized).clip(lower=0.0, upper=1.0).fillna(1.0)
    return weights.mul(scale, axis=0)


def _group_rotation_signal(close: pd.DataFrame, *, days: int) -> pd.DataFrame:
    scalar = _group_scalar(close, days)
    values = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for ticker in values.columns:
        if ticker in CYCLICAL_SECTORS:
            values[ticker] = scalar
        elif ticker in DEFENSIVE_SECTORS:
            values[ticker] = -scalar
    return _cross_sectional_z(values)


def _group_scalar(close: pd.DataFrame, days: int) -> pd.Series:
    cyclicals = [ticker for ticker in close.columns if ticker in CYCLICAL_SECTORS]
    defensives = [ticker for ticker in close.columns if ticker in DEFENSIVE_SECTORS]
    cyclical_index = close[cyclicals].pct_change(fill_method=None).mean(axis=1).add(1.0).cumprod()
    defensive_index = close[defensives].pct_change(fill_method=None).mean(axis=1).add(1.0).cumprod()
    relative = cyclical_index / defensive_index
    return relative.pct_change(days, fill_method=None)


def _pair_transition_signal(close: pd.DataFrame, days: int) -> pd.DataFrame:
    signal = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    counts = pd.Series(0.0, index=close.columns)
    for left, right in SECTOR_TRANSITION_PAIRS:
        if left not in close or right not in close:
            continue
        relative_return = close[left].div(close[right]).pct_change(days, fill_method=None)
        signal[left] = signal[left].add(relative_return, fill_value=0.0)
        signal[right] = signal[right].sub(relative_return, fill_value=0.0)
        counts[left] += 1.0
        counts[right] += 1.0
    signal = signal.div(counts.replace(0.0, np.nan), axis=1).fillna(0.0)
    return _cross_sectional_z(signal)


def _context_echo_signal(
    context: pd.DataFrame,
    sectors: pd.Index,
    days: int,
) -> pd.DataFrame:
    signal = pd.DataFrame(0.0, index=context.index, columns=sectors)
    if context.empty:
        return signal
    proxy_returns = context.div(context.shift(days)).sub(1.0)
    proxy_scores = _cross_sectional_z(proxy_returns)
    for sector in sectors:
        available = [ticker for ticker in CONTEXT_ECHO_MAP.get(sector, ()) if ticker in proxy_scores]
        if available:
            signal[sector] = proxy_scores[available].mean(axis=1).fillna(0.0)
    return _cross_sectional_z(signal)


def _leader_crowding(base_raw: pd.DataFrame, base_rank: pd.DataFrame) -> pd.DataFrame:
    ordered = np.sort(base_raw.to_numpy(dtype=float), axis=1)
    gap = pd.Series(ordered[:, -1] - ordered[:, -2], index=base_raw.index)
    scale = base_raw.std(axis=1).replace(0.0, np.nan)
    normalized_gap = gap.div(scale).clip(lower=0.0, upper=3.0).fillna(0.0)
    return base_rank.eq(1.0).astype(float).mul(normalized_gap, axis=0)


def _cross_sectional_z(frame: pd.DataFrame) -> pd.DataFrame:
    mean = frame.mean(axis=1)
    std = frame.std(axis=1).replace(0.0, np.nan)
    return frame.sub(mean, axis=0).div(std, axis=0).fillna(0.0)


def _rolling_z(series: pd.Series, days: int) -> pd.Series:
    mean = series.rolling(days).mean()
    std = series.rolling(days).std().replace(0.0, np.nan)
    return (series - mean) / std
