"""Gemeinsame Fixtures: die Handinstanz, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gwt_scenario import Inst  # noqa: E402


@pytest.fixture
def hand():
    """Drei Kunden auf einer Geraden (Abstand 2, 4, 6 vom Depot), Service 1, ein Fahrzeug, Budget 10, Prämien 5, 8, 9.

    Handrechnung: Tour [1, 2] dauert 2 + 2 + 4 Fahrt + 2 Service = 10 (zulässig), [3] allein 6 + 6 + 1 = 13 (unzulässig), [2] allein 9, [1] allein 5,
    [1, 3] 2 + 4 + 6 + 2 = 14, [1, 2, 3] 12 + 3 = 15. Optimum ist [1, 2] mit Prämie 13."""
    return Inst(n=3, K=1, tmax=10, serv=1, T=[[0, 2, 4, 6], [2, 0, 2, 4], [4, 2, 0, 2], [6, 4, 2, 0]], prize=[0, 5, 8, 9],
                xy=[(0, 0), (2, 0), (4, 0), (6, 0)])
