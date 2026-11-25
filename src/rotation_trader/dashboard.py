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
left.plotly_chart(allocation, use_container_width=True)

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
right.plotly_chart(rank_chart, use_container_width=True)

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
    "swing_sector_control": "#E69F00",
    "spy_buy_hold": "#009E73",
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
st.plotly_chart(equity, use_container_width=True)

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
st.plotly_chart(regime_chart, use_container_width=True)

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
st.plotly_chart(family_chart, use_container_width=True)

gates = pd.Series(summary["promotion_gates"], name="passed").rename_axis("gate").reset_index()
gates["status"] = gates["passed"].map({True: "Passed", False: "Failed"})
st.dataframe(
    gates[["gate", "status"]],
    hide_index=True,
    use_container_width=True,
    column_config={"gate": "Historical gate", "status": "Status"},
)

st.caption(
    f"Protocol: {summary['protocol_phase']} | Selected: {summary['selected_variant_id']} | "
    "Human execution only | No broker connection"
)
