from rotation_trader.hypotheses import generate_registered_variants, registry_frame


def test_registry_is_large_unique_and_rotation_specific_outside_controls() -> None:
    variants = generate_registered_variants()
    ids = [variant.variant_id for variant in variants]

    assert len(variants) >= 2000
    assert len(ids) == len(set(ids))
    assert all(
        variant.is_rotation_specific
        for variant in variants
        if not variant.family.startswith("comparator_")
    )

    registry = registry_frame(variants)
    assert set(registry["research_wave"]) == {1, 2}
    assert {
        "rank_crossing_event",
        "sector_pair_transition",
        "confirmed_transition",
        "leadership_crowding",
        "correlation_conditioned_rotation",
        "context_echo_confirmation",
        "adversarial_transition_ensemble",
    }.issubset(set(registry.loc[registry["research_wave"].eq(2), "family"]))
