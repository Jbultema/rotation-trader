from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

REPORT_DIR = Path(os.environ.get("ROTATION_TRADER_REPORT_DIR", "reports/latest"))


def _load_json(name: str) -> dict[str, object]:
    return json.loads((REPORT_DIR / name).read_text(encoding="utf-8"))


def _percent(value: float) -> str:
    return f"{value:.1%}"


st.set_page_config(page_title="Rotation Trader", page_icon="RT", layout="wide")
st.title("Rotation Trader")

if not (REPORT_DIR / "research_summary.json").exists():
    st.error("No audited research run is available.")
    st.stop()

summary = _load_json("research_summary.json")
decision = summary.get("latest_decision")
if not isinstance(decision, dict):
    st.error("The latest research run produced no candidate decision.")
    st.stop()

status = str(summary["promotion_status"])
if status == "historical_gates_passed_prospective_shadow_required":
    st.warning("Historical gates passed. Prospective shadow evidence is still required.")
else:
    st.info("Research candidate only. No trade is authorized.")

top = st.columns(5)
top[0].metric("As of close", str(decision["as_of_close"]))
top[1].metric("Leadership state", str(decision["leadership_state"]).replace("_", " ").title())
top[2].metric("Breadth", _percent(float(decision["breadth"])))
top[3].metric("Cash target", _percent(float(decision["cash_weight"])))
top[4].metric("Variants tested", f"{int(summary['variants_tested']):,}")

st.subheader("Current Sector Read")
left, right = st.columns([1.2, 1.0])
targets = pd.Series(decision["target_weights"], dtype=float).sort_values(ascending=True)
allocation = px.bar(
    targets.rename_axis("sector").reset_index(name="weight"),
    x="weight",
    y="sector",
    orientation="h",
    color="sector",
    color_discrete_sequence=px.colors.qualitative.Safe,
    labels={"weight": "Target weight", "sector": "Sector"},
)
allocation.update_layout(showlegend=False, height=300, margin={"l": 10, "r": 10, "t": 20, "b": 10})
allocation.update_xaxes(tickformat=".0%", range=[0, 1])
left.plotly_chart(allocation, width="stretch")

ranks = pd.Series(decision["sector_ranks"], dtype=float).sort_values()
rank_chart = px.bar(
    ranks.rename_axis("sector").reset_index(name="rank"),
    x="sector",
    y="rank",
    color="rank",
    color_continuous_scale="RdYlGn_r",
    labels={"rank": "Leadership rank", "sector": "Sector"},
)
rank_chart.update_yaxes(autorange="reversed", dtick=1)
rank_chart.update_layout(
    height=300, margin={"l": 10, "r": 10, "t": 20, "b": 10}, coloraxis_showscale=False
)
right.plotly_chart(rank_chart, width="stretch")

challenger = summary.get("allocation_timing_challenger")
if isinstance(challenger, dict):
    challenger_decision = challenger["latest_decision"]
    st.subheader("Allocation and Timing Challenger")
    timing_labels = {3: "Risk On", 2: "Watch", 1: "Warning", 0: "Defensive"}
    challenger_metrics = st.columns(4)
    challenger_metrics[0].metric("Family", str(challenger["family"]).replace("_", " ").title())
    challenger_metrics[1].metric(
        "Timing stage",
        timing_labels[int(challenger_decision["timing_stage"])],
    )
    challenger_metrics[2].metric(
        "Sleeve exposure",
        _percent(float(challenger_decision["sleeve_exposure"])),
    )
    challenger_metrics[3].metric(
        "Target holdings",
        str(int(challenger_decision["target_holding_count"])),
    )
    challenger_targets = pd.Series(
        challenger_decision["target_weights"],
        dtype=float,
    ).sort_values(ascending=True)
    challenger_chart = px.bar(
        challenger_targets.rename_axis("sector").reset_index(name="weight"),
        x="weight",
        y="sector",
        orientation="h",
        color="sector",
        color_discrete_sequence=px.colors.qualitative.Safe,
        labels={"weight": "Target weight", "sector": "Sector"},
    )
    challenger_chart.update_layout(
        showlegend=False,
        height=300,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )
    challenger_chart.update_xaxes(tickformat=".0%", range=[0, 1])
    st.plotly_chart(challenger_chart, width="stretch")

regime_challenger = summary.get("regime_robust_challenger")
if isinstance(regime_challenger, dict):
    regime_decision = regime_challenger["latest_decision"]
    st.subheader("Normal and Break Regime Challenger")
    regime_metrics = st.columns(4)
    regime_metrics[0].metric(
        "Family",
        str(regime_challenger["family"]).replace("_", " ").title(),
    )
    regime_metrics[1].metric(
        "Substantial-edge gate",
        "Passed" if regime_challenger["preholdout_gate_passed"] else "Failed",
    )
    regime_metrics[2].metric(
        "Sleeve exposure",
        _percent(float(regime_decision["sleeve_exposure"])),
    )
    regime_metrics[3].metric(
        "Cash",
        _percent(float(regime_decision["cash_weight"])),
    )
    regime_targets = pd.Series(regime_decision["target_weights"], dtype=float).sort_values()
    regime_allocation = px.bar(
        regime_targets.rename_axis("sector").reset_index(name="weight"),
        x="weight",
        y="sector",
        orientation="h",
        color="sector",
        color_discrete_sequence=px.colors.qualitative.Safe,
        labels={"weight": "Target weight", "sector": "Sector"},
    )
    regime_allocation.update_layout(
        showlegend=False,
        height=300,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )
    regime_allocation.update_xaxes(tickformat=".0%", range=[0, 1])
    st.plotly_chart(regime_allocation, width="stretch")

st.subheader("Candidate vs Controls")
comparison = pd.read_parquet(REPORT_DIR / "comparison_returns.parquet").fillna(0.0)
window = st.segmented_control(
    "Window",
    options=["Full", "2012+", "2019+", "2024+"],
    default="2019+",
)
starts = {"Full": None, "2012+": "2012-01-01", "2019+": "2019-01-01", "2024+": "2024-01-01"}
start = starts[window]
shown = comparison if start is None else comparison.loc[start:]
growth = (1.0 + shown).cumprod()
growth = growth.div(growth.iloc[0])
equity = go.Figure()
palette = {
    "rotation_candidate": "#0072B2",
    "allocation_timing_challenger": "#CC79A7",
    "regime_robust_challenger": "#D55E00",
    "swing_sector_control": "#E69F00",
    "spy_buy_hold": "#009E73",
    "qqq_buy_hold": "#56B4E9",
    "rsp_buy_hold": "#F0E442",
    "equal_weight_sectors": "#6B7280",
}
for column in growth:
    equity.add_scatter(
        x=growth.index,
        y=growth[column],
        mode="lines",
        name=column.replace("_", " ").title(),
        line={"color": palette[column], "width": 2.4 if column == "rotation_candidate" else 1.8},
    )
equity.update_layout(
    yaxis_title="Growth of $1",
    xaxis_title=None,
    height=430,
    margin={"l": 10, "r": 10, "t": 20, "b": 10},
    legend={"orientation": "h", "y": -0.2},
)
st.plotly_chart(equity, width="stretch")

st.subheader("Simple Buy-and-Hold Benchmarks")
buy_hold = pd.read_csv(REPORT_DIR / "simple_buy_hold_metrics.csv")
buy_hold_period = st.segmented_control(
    "Benchmark period",
    options=["full_history", "development", "validation", "holdout", "forward_diagnostic"],
    default="full_history",
    format_func=lambda value: str(value).replace("_", " ").title(),
)
buy_hold_shown = buy_hold.loc[buy_hold["period"].eq(buy_hold_period)].copy()
buy_hold_shown["benchmark"] = buy_hold_shown["variant_id"].str.removeprefix("benchmark_")
st.dataframe(
    buy_hold_shown[
        ["benchmark", "cagr", "sharpe_zero_rf", "max_drawdown", "annualized_volatility"]
    ].sort_values("cagr", ascending=False),
    hide_index=True,
    width="stretch",
    column_config={
        "benchmark": "Buy and hold",
        "cagr": st.column_config.NumberColumn("CAGR", format="percent"),
        "sharpe_zero_rf": st.column_config.NumberColumn("Sharpe", format="%.2f"),
        "max_drawdown": st.column_config.NumberColumn("Max drawdown", format="percent"),
        "annualized_volatility": st.column_config.NumberColumn("Volatility", format="percent"),
    },
)

distinct = summary["behavioral_distinctness"]
comparison_cols = st.columns(3)
comparison_cols[0].metric(
    "Return correlation to Swing control", f"{float(distinct['return_correlation']):.3f}"
)
comparison_cols[1].metric("Mean weight overlap", _percent(float(distinct["mean_weight_overlap"])))
comparison_cols[2].metric(
    "Different-weight days", _percent(float(distinct["different_weight_day_share"]))
)

st.subheader("What Worked, When")
regimes = pd.read_csv(REPORT_DIR / "regime_comparison.csv")
regime_returns = regimes.pivot(index="regime", columns="strategy", values="cagr")
regime_returns = regime_returns.reset_index().melt(
    id_vars="regime", var_name="strategy", value_name="cagr"
)
regime_chart = px.bar(
    regime_returns,
    x="regime",
    y="cagr",
    color="strategy",
    barmode="group",
    color_discrete_map=palette,
    labels={"cagr": "CAGR", "regime": "Regime", "strategy": "Strategy"},
)
regime_chart.update_yaxes(tickformat=".0%")
regime_chart.update_layout(height=430, margin={"l": 10, "r": 10, "t": 20, "b": 10})
st.plotly_chart(regime_chart, width="stretch")

st.subheader("Point-in-Time Normal vs Regime Change")
states = pd.read_csv(REPORT_DIR / "state_conditioned_comparison.csv")
state_chart = px.bar(
    states,
    x="market_state",
    y="annualized_arithmetic_return",
    color="strategy",
    barmode="group",
    category_orders={"market_state": ["normal", "transition", "break"]},
    color_discrete_map=palette,
    labels={
        "market_state": "Point-in-time market state",
        "annualized_arithmetic_return": "Conditional annualized return",
        "strategy": "Strategy",
    },
)
state_chart.update_yaxes(tickformat=".0%")
state_chart.update_layout(height=430, margin={"l": 10, "r": 10, "t": 20, "b": 10})
st.plotly_chart(state_chart, width="stretch")

st.subheader("Rolling Outperformance Durability")
rolling = pd.read_csv(REPORT_DIR / "rolling_outperformance.csv")
st.dataframe(
    rolling[
        [
            "strategy",
            "benchmark",
            "window_sessions",
            "beat_share",
            "median_annualized_excess",
            "p10_annualized_excess",
            "latest_annualized_excess",
        ]
    ],
    hide_index=True,
    width="stretch",
    column_config={
        "strategy": "Strategy",
        "benchmark": "Buy and hold",
        "window_sessions": "Sessions",
        "beat_share": st.column_config.NumberColumn("Beat rate", format="percent"),
        "median_annualized_excess": st.column_config.NumberColumn(
            "Median excess", format="percent"
        ),
        "p10_annualized_excess": st.column_config.NumberColumn(
            "10th percentile", format="percent"
        ),
        "latest_annualized_excess": st.column_config.NumberColumn(
            "Latest excess", format="percent"
        ),
    },
)

st.subheader("Detected Break Episodes")
events = pd.read_csv(REPORT_DIR / "regime_break_events.csv")
breaks = events.loc[events["phase"].eq("break")].copy()
break_summary = (
    breaks.groupby("strategy")
    .agg(
        episodes=("event", "nunique"),
        median_break_return=("return", "median"),
        median_excess_vs_spy=("excess_vs_spy", "median"),
        worst_episode_drawdown=("max_drawdown", "min"),
    )
    .reset_index()
)
break_chart = px.bar(
    break_summary,
    x="strategy",
    y="median_excess_vs_spy",
    color="strategy",
    color_discrete_map=palette,
    labels={"strategy": "Strategy", "median_excess_vs_spy": "Median break excess vs SPY"},
)
break_chart.update_yaxes(tickformat=".0%")
break_chart.update_layout(
    showlegend=False,
    height=360,
    margin={"l": 10, "r": 10, "t": 20, "b": 10},
)
st.plotly_chart(break_chart, width="stretch")

st.subheader("Research Robustness")
family = pd.read_csv(REPORT_DIR / "family_preholdout_evidence.csv")
family = family.loc[~family["family"].str.startswith("comparator_")].copy()
family["pass_rate"] = family["preholdout_gate_pass_rate"]
family_chart = px.scatter(
    family,
    x="best_robust_score",
    y="median_robust_score",
    size="variants",
    color="research_wave",
    hover_name="family",
    hover_data=["preholdout_gate_pass_count", "pass_rate"],
    color_continuous_scale="Viridis",
    labels={
        "best_robust_score": "Best variant score",
        "median_robust_score": "Median family score",
        "research_wave": "Wave",
    },
)
family_chart.update_layout(height=400, margin={"l": 10, "r": 10, "t": 20, "b": 10})
st.plotly_chart(family_chart, width="stretch")

gates = pd.Series(summary["promotion_gates"], name="passed").rename_axis("gate").reset_index()
gates["status"] = gates["passed"].map({True: "Passed", False: "Failed"})
st.dataframe(
    gates[["gate", "status"]],
    hide_index=True,
    width="stretch",
    column_config={"gate": "Historical gate", "status": "Status"},
)

st.caption(
    f"Protocol: {summary['protocol_phase']} | Selected: {summary['selected_variant_id']} | "
    "Human execution only | No broker connection"
)
