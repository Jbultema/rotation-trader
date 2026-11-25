from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from rotation_trader.strategy import VariantSpec


def generate_registered_variants() -> tuple[VariantSpec, ...]:
    variants: list[VariantSpec] = [
        VariantSpec(
            family="comparator_swing_dual_momentum",
            momentum_lookbacks=(252,),
            momentum_weights=(1.0,),
            top_n=3,
            cadence="monthly",
            weighting="equal",
            absolute_gate=True,
        ),
        VariantSpec(
            family="comparator_sector_momentum",
            momentum_lookbacks=(126, 252),
            momentum_weights=(0.5, 0.5),
            top_n=3,
            cadence="monthly",
            weighting="equal",
            absolute_gate=False,
        ),
    ]
    base_templates = (
        ((63, 126), (0.4, 0.6)),
        ((126, 252), (0.5, 0.5)),
        ((63, 126, 252), (0.2, 0.4, 0.4)),
    )
    top_values = (2, 3)
    cadences = ("monthly", "biweekly")
    weightings = ("equal", "inverse_volatility")

    for lookbacks, momentum_weights in base_templates:
        for top_n in top_values:
            for cadence in cadences:
                for weighting in weightings:
                    for absolute_gate in (False, True):
                        for days in (21, 63):
                            for strength in (0.25, 0.5, 0.75):
                                variants.append(
                                    VariantSpec(
                                        family="acceleration",
                                        momentum_lookbacks=lookbacks,
                                        momentum_weights=momentum_weights,
                                        top_n=top_n,
                                        cadence=cadence,
                                        weighting=weighting,
                                        absolute_gate=absolute_gate,
                                        acceleration_days=days,
                                        acceleration_weight=strength,
                                    )
                                )
                                variants.append(
                                    VariantSpec(
                                        family="rank_migration",
                                        momentum_lookbacks=lookbacks,
                                        momentum_weights=momentum_weights,
                                        top_n=top_n,
                                        cadence=cadence,
                                        weighting=weighting,
                                        absolute_gate=absolute_gate,
                                        rank_velocity_days=days,
                                        rank_velocity_weight=strength,
                                        rank_buffer=1,
                                    )
                                )
                        for persistence_days in (42, 63, 126):
                            for strength in (0.25, 0.5):
                                variants.append(
                                    VariantSpec(
                                        family="leadership_persistence",
                                        momentum_lookbacks=lookbacks,
                                        momentum_weights=momentum_weights,
                                        top_n=top_n,
                                        cadence=cadence,
                                        weighting=weighting,
                                        absolute_gate=absolute_gate,
                                        persistence_days=persistence_days,
                                        persistence_weight=strength,
                                        minimum_holding_rebalances=1,
                                    )
                                )
                        for strength in (0.2, 0.4):
                            variants.append(
                                VariantSpec(
                                    family="reversal_transition",
                                    momentum_lookbacks=lookbacks,
                                    momentum_weights=momentum_weights,
                                    top_n=top_n,
                                    cadence=cadence,
                                    weighting=weighting,
                                    absolute_gate=absolute_gate,
                                    reversal_weight=strength,
                                )
                            )
                        for rotation_days in (42, 63, 126):
                            for strength in (0.25, 0.5):
                                variants.append(
                                    VariantSpec(
                                        family="cyclical_defensive_transition",
                                        momentum_lookbacks=lookbacks,
                                        momentum_weights=momentum_weights,
                                        top_n=top_n,
                                        cadence=cadence,
                                        weighting=weighting,
                                        absolute_gate=absolute_gate,
                                        group_rotation_days=rotation_days,
                                        group_rotation_weight=strength,
                                    )
                                )

    combination_templates = (
        {"acceleration_weight": 0.5, "rank_velocity_weight": 0.5},
        {"acceleration_weight": 0.5, "persistence_weight": 0.5},
        {"rank_velocity_weight": 0.5, "persistence_weight": 0.5},
        {
            "acceleration_weight": 0.35,
            "rank_velocity_weight": 0.35,
            "persistence_weight": 0.3,
        },
        {
            "acceleration_weight": 0.4,
            "group_rotation_weight": 0.4,
            "persistence_weight": 0.2,
        },
    )
    for lookbacks, momentum_weights in base_templates:
        for top_n in top_values:
            for cadence in cadences:
                for weighting in weightings:
                    for template in combination_templates:
                        for buffer in (0, 1, 2):
                            variants.append(
                                VariantSpec(
                                    family="transition_ensemble",
                                    momentum_lookbacks=lookbacks,
                                    momentum_weights=momentum_weights,
                                    top_n=top_n,
                                    cadence=cadence,
                                    weighting=weighting,
                                    rank_buffer=buffer,
                                    **template,
                                )
                            )

    for lookbacks, momentum_weights in base_templates:
        for top_n in top_values:
            for weighting in weightings:
                for trend_days in (100, 150, 200):
                    for threshold in (4 / 9, 5 / 9, 6 / 9):
                        variants.append(
                            VariantSpec(
                                family="breadth_transition",
                                momentum_lookbacks=lookbacks,
                                momentum_weights=momentum_weights,
                                top_n=top_n,
                                weighting=weighting,
                                breadth_trend_days=trend_days,
                                breadth_threshold=threshold,
                                acceleration_weight=0.35,
                                rank_velocity_weight=0.35,
                                risk_off_mode="cash",
                            )
                        )
                for penalty in (0.25, 0.5, 0.75):
                    variants.append(
                        VariantSpec(
                            family="dispersion_conditioned",
                            momentum_lookbacks=lookbacks,
                            momentum_weights=momentum_weights,
                            top_n=top_n,
                            weighting=weighting,
                            acceleration_weight=0.5,
                            dispersion_penalty=penalty,
                        )
                    )

    # Wave 2 was registered after the first sealed holdout had been opened. These
    # variants are adversarial diagnostics and cannot restore pristine-holdout status.
    for lookbacks, momentum_weights in base_templates:
        for top_n in top_values:
            for cadence in cadences:
                for weighting in weightings:
                    for days in (21, 42):
                        for strength in (0.25, 0.5):
                            variants.append(
                                VariantSpec(
                                    family="rank_crossing_event",
                                    momentum_lookbacks=lookbacks,
                                    momentum_weights=momentum_weights,
                                    top_n=top_n,
                                    cadence=cadence,
                                    weighting=weighting,
                                    rank_crossing_days=days,
                                    rank_crossing_weight=strength,
                                    rank_buffer=1,
                                )
                            )
                    for days in (42, 84):
                        for strength in (0.25, 0.5):
                            variants.append(
                                VariantSpec(
                                    family="sector_pair_transition",
                                    momentum_lookbacks=lookbacks,
                                    momentum_weights=momentum_weights,
                                    top_n=top_n,
                                    cadence=cadence,
                                    weighting=weighting,
                                    pair_transition_days=days,
                                    pair_transition_weight=strength,
                                )
                            )

            for weighting in weightings:
                for minimum_signals in (2, 3):
                    for strength in (0.25, 0.5):
                        variants.append(
                            VariantSpec(
                                family="confirmed_transition",
                                momentum_lookbacks=lookbacks,
                                momentum_weights=momentum_weights,
                                top_n=top_n,
                                weighting=weighting,
                                acceleration_weight=0.25,
                                rank_velocity_weight=0.25,
                                persistence_weight=0.25,
                                pair_transition_weight=0.25,
                                confirmation_min_signals=minimum_signals,
                                confirmation_weight=strength,
                            )
                        )
                for penalty in (0.15, 0.3, 0.5):
                    variants.append(
                        VariantSpec(
                            family="leadership_crowding",
                            momentum_lookbacks=lookbacks,
                            momentum_weights=momentum_weights,
                            top_n=top_n,
                            weighting=weighting,
                            acceleration_weight=0.35,
                            rank_velocity_weight=0.35,
                            leader_crowding_penalty=penalty,
                        )
                    )
                for days in (42, 84):
                    for scale in (0.25, 0.5):
                        variants.append(
                            VariantSpec(
                                family="correlation_conditioned_rotation",
                                momentum_lookbacks=lookbacks,
                                momentum_weights=momentum_weights,
                                top_n=top_n,
                                weighting=weighting,
                                acceleration_weight=0.5,
                                rank_velocity_weight=0.5,
                                correlation_days=days,
                                correlation_rotation_scale=scale,
                            )
                        )
                for days in (63, 126):
                    for strength in (0.2, 0.4):
                        variants.append(
                            VariantSpec(
                                family="context_echo_confirmation",
                                momentum_lookbacks=lookbacks,
                                momentum_weights=momentum_weights,
                                top_n=top_n,
                                weighting=weighting,
                                acceleration_weight=0.35,
                                rank_velocity_weight=0.35,
                                context_echo_days=days,
                                context_echo_weight=strength,
                            )
                        )

                adversarial_ensembles = (
                    {
                        "rank_crossing_weight": 0.25,
                        "pair_transition_weight": 0.25,
                        "confirmation_min_signals": 2,
                        "confirmation_weight": 0.25,
                    },
                    {
                        "pair_transition_weight": 0.3,
                        "leader_crowding_penalty": 0.2,
                        "correlation_rotation_scale": 0.25,
                    },
                    {
                        "rank_crossing_weight": 0.2,
                        "pair_transition_weight": 0.2,
                        "context_echo_weight": 0.2,
                    },
                    {
                        "confirmation_min_signals": 3,
                        "confirmation_weight": 0.35,
                        "leader_crowding_penalty": 0.2,
                    },
                )
                for template in adversarial_ensembles:
                    variants.append(
                        VariantSpec(
                            family="adversarial_transition_ensemble",
                            momentum_lookbacks=lookbacks,
                            momentum_weights=momentum_weights,
                            top_n=top_n,
                            weighting=weighting,
                            acceleration_weight=0.25,
                            rank_velocity_weight=0.25,
                            persistence_weight=0.2,
                            **template,
                        )
                    )

    timing_profiles = (
        (0.85, 0.60, 0.25),
        (0.75, 0.50, 0.20),
        (0.65, 0.40, 0.00),
    )
    for lookbacks, momentum_weights in base_templates:
        for cadence in cadences:
            for weighting in ("score_softmax", "score_inverse_volatility"):
                for temperature in (0.5, 1.0):
                    for maximum_weight in (0.45, 0.60):
                        for dynamic in (False, True):
                            variants.append(
                                VariantSpec(
                                    family="adaptive_confidence_allocation",
                                    momentum_lookbacks=lookbacks,
                                    momentum_weights=momentum_weights,
                                    top_n=3,
                                    cadence=cadence,
                                    weighting=weighting,
                                    dynamic_top_n=dynamic,
                                    minimum_holdings=2,
                                    maximum_holdings=5,
                                    score_temperature=temperature,
                                    maximum_sector_weight=maximum_weight,
                                    acceleration_weight=0.35,
                                    rank_velocity_weight=0.35,
                                    persistence_weight=0.30,
                                    rank_buffer=1,
                                )
                            )

            for weighting in ("equal", "inverse_volatility", "score_inverse_volatility"):
                for fast_days in (42, 63):
                    for slow_days in (150, 200):
                        for watch, warning, defensive in timing_profiles:
                            for transition_rebalance in (False, True):
                                variants.append(
                                    VariantSpec(
                                        family="staged_market_timing",
                                        momentum_lookbacks=lookbacks,
                                        momentum_weights=momentum_weights,
                                        top_n=3,
                                        cadence=cadence,
                                        weighting=weighting,
                                        acceleration_weight=0.35,
                                        rank_velocity_weight=0.35,
                                        persistence_weight=0.30,
                                        timing_mode="staged",
                                        timing_fast_days=fast_days,
                                        timing_slow_days=slow_days,
                                        timing_confirmation_days=5,
                                        watch_exposure=watch,
                                        warning_exposure=warning,
                                        defensive_exposure=defensive,
                                        rebalance_on_timing_transition=transition_rebalance,
                                    )
                                )

            for weighting in ("score_softmax", "score_inverse_volatility"):
                for temperature in (0.5, 1.0):
                    for watch, warning, defensive in timing_profiles[:2]:
                        for drawdown_limit in (None, -0.12):
                            for transition_rebalance in (False, True):
                                variants.append(
                                    VariantSpec(
                                        family="adaptive_timed_rotation",
                                        momentum_lookbacks=lookbacks,
                                        momentum_weights=momentum_weights,
                                        top_n=3,
                                        cadence=cadence,
                                        weighting=weighting,
                                        dynamic_top_n=True,
                                        minimum_holdings=2,
                                        maximum_holdings=5,
                                        score_temperature=temperature,
                                        maximum_sector_weight=0.50,
                                        acceleration_weight=0.35,
                                        rank_velocity_weight=0.35,
                                        persistence_weight=0.30,
                                        timing_mode="staged",
                                        timing_fast_days=63,
                                        timing_slow_days=200,
                                        timing_confirmation_days=5,
                                        watch_exposure=watch,
                                        warning_exposure=warning,
                                        defensive_exposure=defensive,
                                        market_drawdown_limit=drawdown_limit,
                                        rebalance_on_timing_transition=transition_rebalance,
                                    )
                                )

            for confirmation_days in (3, 5, 10):
                for fast_days in (42, 63):
                    for drawdown_limit in (None, -0.10, -0.15):
                        for weighting in ("inverse_volatility", "score_inverse_volatility"):
                            variants.append(
                                VariantSpec(
                                    family="fast_defensive_reentry",
                                    momentum_lookbacks=lookbacks,
                                    momentum_weights=momentum_weights,
                                    top_n=3,
                                    cadence=cadence,
                                    weighting=weighting,
                                    acceleration_weight=0.35,
                                    rank_velocity_weight=0.35,
                                    timing_mode="staged",
                                    timing_fast_days=fast_days,
                                    timing_slow_days=150,
                                    timing_confirmation_days=confirmation_days,
                                    watch_exposure=0.75,
                                    warning_exposure=0.50,
                                    defensive_exposure=0.0,
                                    market_drawdown_limit=drawdown_limit,
                                    rebalance_on_timing_transition=True,
                                )
                            )

        for weighting in ("equal", "inverse_volatility", "score_inverse_volatility"):
            for target_volatility in (0.10, 0.13, 0.16):
                for dispersion_penalty in (0.0, 0.25, 0.50):
                    for staged in (False, True):
                        variants.append(
                            VariantSpec(
                                family="volatility_managed_rotation",
                                momentum_lookbacks=lookbacks,
                                momentum_weights=momentum_weights,
                                top_n=3,
                                cadence="monthly",
                                weighting=weighting,
                                acceleration_weight=0.35,
                                rank_velocity_weight=0.35,
                                persistence_weight=0.30,
                                target_volatility=target_volatility,
                                dispersion_penalty=dispersion_penalty,
                                timing_mode="staged" if staged else "binary",
                                timing_fast_days=63,
                                timing_slow_days=200,
                                timing_confirmation_days=5,
                                watch_exposure=0.75,
                                warning_exposure=0.50,
                                defensive_exposure=0.20,
                            )
                        )
    unique = {variant.variant_id: variant for variant in variants}
    return tuple(unique[key] for key in sorted(unique))


def registry_frame(variants: tuple[VariantSpec, ...]) -> pd.DataFrame:
    wave_two_families = {
        "rank_crossing_event",
        "sector_pair_transition",
        "confirmed_transition",
        "leadership_crowding",
        "correlation_conditioned_rotation",
        "context_echo_confirmation",
        "adversarial_transition_ensemble",
    }
    wave_three_families = {
        "adaptive_confidence_allocation",
        "staged_market_timing",
        "adaptive_timed_rotation",
        "fast_defensive_reentry",
        "volatility_managed_rotation",
    }
    rows = [
        {
            "variant_id": variant.variant_id,
            "research_wave": 3
            if variant.family in wave_three_families
            else 2
            if variant.family in wave_two_families
            else 1,
            **asdict(variant),
        }
        for variant in variants
    ]
    return pd.DataFrame(rows)
