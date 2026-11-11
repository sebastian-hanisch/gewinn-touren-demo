"""Kern gegen Handrechnung: Instanz, Bewertung, Greedy, Lokalsuche (Zugart-Schalter) und ILS (DEMO-PLAYBOOK §1b)."""

import pytest

import gwt_algorithm as A
import gwt_scenario as S


def test_instance_is_deterministic_and_triangle_inequality_holds():
    a, b = S.make_instance(20, 2, 7, 0.4, "lognormal"), S.make_instance(20, 2, 7, 0.4, "lognormal")
    assert a.T == b.T and a.prize == b.prize and a.tmax == b.tmax
    T = a.T
    assert all(T[i][k] <= T[i][j] + T[j][k] for i in range(21) for j in range(21) for k in range(21))


def test_prize_types_share_locations_and_budget():
    a, b = S.make_instance(20, 2, 7, 0.4, "lognormal"), S.make_instance(20, 2, 7, 0.4, "fern")
    assert a.xy == b.xy and a.tmax == b.tmax and a.prize != b.prize
    assert set(S.make_instance(15, 1, 3, 0.5, "gleich").prize[1:]) == {10}


def test_unknown_prize_type_is_rejected():
    with pytest.raises(ValueError):
        S.make_instance(15, 1, 3, 0.5, "unbekannt")


def test_route_time_by_hand(hand):
    assert S.route_time(hand, [1, 2]) == 10 and S.route_time(hand, [3]) == 13 and S.route_time(hand, [2]) == 9
    assert S.route_time(hand, [1, 3]) == 14 and S.route_time(hand, [1, 2, 3]) == 15 and S.route_time(hand, []) == 0


def test_validator_rejects_infeasible_plans(hand):
    for bad in ([[3]], [[1, 2, 3]], [[1], [2]], [[1, 1]], [[4]]):
        with pytest.raises(AssertionError):
            S.validate(hand, bad)
    assert S.validate(hand, [[1, 2]]) == 13


def test_greedy_ratio_finds_the_hand_optimum(hand):
    assert S.validate(hand, A.greedy_ratio(hand)) == 13


def test_greedy_prize_skips_customers_that_do_not_fit(hand):
    routes = A.greedy_prize(hand)  # Kunde 3 (Prämie 9) passt nicht, dann 2 (8), dann 1 (5): beide passen zusammen
    assert S.validate(hand, routes) == 13


def test_stage_invariants_on_random_instances():
    for seed in range(12):
        inst = S.make_instance(25, 1 + seed % 3, 40 + seed, [0.3, 0.5, 0.8][seed % 3], ["lognormal", "fern", "gleich"][seed % 3])
        r0 = A.greedy_ratio(inst)
        s0 = {c for r in r0 for c in r}
        a = A.local_search(inst, r0, A.ROUTE_MOVES)
        b = A.local_search(inst, r0, A.ROUTE_INSERT)
        c = A.local_search(inst, r0, A.ALL_MOVES)
        assert {x for r in a for x in r} == s0 and S.total_time(inst, a) <= S.total_time(inst, r0)   # Routenzüge ändern die Menge nie
        assert s0 <= {x for r in b for x in r}                                                         # Einfügen behält alle Kunden
        keys = [A.key_of(inst, r) for r in (r0, a, b, c)]
        assert keys == sorted(keys)                                                                    # Stufen monoton (Prämie hoch, Zeit niedrig)
        assert A.key_of(inst, A.local_search(inst, c)) == keys[-1]                                     # Lokalsuche idempotent
        assert c == A.local_search(inst, r0)                                                           # alle Züge = Standardaufruf
        for r in (a, b, c):
            S.validate(inst, r)


def test_ils_is_reproducible_valid_and_never_worse_than_local_search():
    inst = S.make_instance(25, 2, 5, 0.4, "lognormal")
    r0 = A.greedy_ratio(inst)
    first, second = A.ils(inst, r0, 80, 3), A.ils(inst, r0, 80, 3)
    assert first == second
    assert A.key_of(inst, S.validate(inst, first) and first) >= A.key_of(inst, A.local_search(inst, r0))


def test_replace_does_nothing_for_equal_prizes():
    for seed in range(8):
        inst = S.make_instance(25, 2, 60 + seed, 0.5, "gleich")
        r0 = A.greedy_ratio(inst)
        assert S.prize_of(inst, A.local_search(inst, r0, A.ALL_MOVES)) == S.prize_of(inst, A.local_search(inst, r0, A.ROUTE_INSERT))
