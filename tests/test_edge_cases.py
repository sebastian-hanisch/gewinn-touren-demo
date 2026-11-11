"""Randfälle: kein Kunde erreichbar, genau einer, Budget für alle, ein und vier Fahrzeuge, Gleichstände, n = 1 und n = 2."""

import gwt_algorithm as A
import gwt_evaluation as E
import gwt_scenario as S


def _line(n, K=1, tmax=100, prizes=None, serv=1):
    """n Kunden auf einer Geraden im Abstand 2, 4, ... vom Depot."""
    pos = [0] + [2 * (i + 1) for i in range(n)]
    T = [[abs(a - b) for b in pos] for a in pos]
    return S.Inst(n=n, K=K, tmax=tmax, serv=serv, T=T, prize=[0] + (prizes or [5] * n), xy=[(x, 0) for x in pos])


def test_no_customer_reachable_gives_the_empty_plan():
    inst = S.make_instance(10, 2, 1, 0.01, "lognormal")
    for routes in (A.greedy_ratio(inst), A.greedy_prize(inst), A.local_search(inst, A.greedy_ratio(inst)), A.ils(inst, A.greedy_ratio(inst), 20, 1)):
        assert S.prize_of(inst, routes) == 0 and S.validate(inst, routes) == 0
    assert E.share(0, 0) == 100.0   # leere Instanz: nichts zu vergleichen, keine Division durch 0


def test_single_customer_n1():
    inst = _line(1, tmax=10)
    assert S.validate(inst, A.greedy_ratio(inst)) == 5
    assert S.validate(inst, A.ils(inst, A.greedy_ratio(inst), 10, 0)) == 5
    assert S.validate(_line(1, tmax=4), A.greedy_ratio(_line(1, tmax=4))) == 0   # 2 + 2 + 1 = 5 > 4


def test_two_customers_n2_budget_exactly_at_the_limit():
    inst = _line(2, tmax=9, serv=1)       # [1, 2]: 2 + 2 + 4 + 2 = 10 > 9; nur ein Kunde passt
    assert S.route_time(inst, [1, 2]) == 10
    assert S.validate(inst, A.greedy_ratio(inst)) == 5
    inst = _line(2, tmax=10, serv=1)      # inklusive Grenze: genau 10 ist zulässig
    assert S.validate(inst, A.greedy_ratio(inst)) == 10


def test_equal_prizes_tie_break_is_deterministic():
    inst = _line(6, K=2, tmax=14, prizes=[7] * 6)
    assert A.greedy_ratio(inst) == A.greedy_ratio(inst) and A.ils(inst, A.greedy_ratio(inst), 30, 2) == A.ils(inst, A.greedy_ratio(inst), 30, 2)


def test_budget_for_everyone_serves_all_customers():
    inst = _line(5, K=1, tmax=10 ** 4)
    assert sorted(c for r in A.greedy_ratio(inst) for c in r) == [1, 2, 3, 4, 5]


def test_one_and_four_vehicles_are_valid_on_the_measured_sizes():
    for K in (1, 4):
        inst = S.make_instance(40, K, 9, 0.4, "lognormal")
        routes = A.local_search(inst, A.greedy_ratio(inst))
        assert len(routes) == K and S.validate(inst, routes) > 0


def test_schedule_of_an_empty_route_is_empty():
    assert E.schedule(_line(3), []) == []
