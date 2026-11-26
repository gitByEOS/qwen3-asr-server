"""装箱以穷举、原始动态规划和候选计数验收。"""

from __future__ import annotations

import itertools
import random
import unittest

from src.audio.silence import Atom, pack_atoms


def make_atoms(lengths: list[float], gaps: list[float] | None = None) -> list[Atom]:
    atoms: list[Atom] = []
    cursor = 0.0
    for index, length in enumerate(lengths):
        if index and gaps is not None:
            cursor += gaps[index - 1]
        atoms.append(Atom(cursor, cursor + length))
        cursor += length
    return atoms


def packing_key(
    atoms: list[Atom], groups: list[tuple[int, int]], target: float,
) -> tuple[float, int, float]:
    durations = [atoms[end - 1].end - atoms[start].start for start, end in groups]
    return sum((duration - target) ** 2 for duration in durations), len(groups), -min(durations)


def exhaustive_key(atoms: list[Atom], target: float) -> tuple[float, int, float]:
    keys = []
    for mask in range(1 << (len(atoms) - 1)):
        stops = [index + 1 for index in range(len(atoms) - 1) if mask & (1 << index)]
        stops.append(len(atoms))
        keys.append(packing_key(atoms, list(zip([0] + stops, stops)), target))
    return min(keys)


def original_pack_atoms(atoms: list[Atom], target: float) -> list[tuple[int, int]]:
    """保留剪枝前的比较顺序，验证浮点容差内的平局行为。"""
    count = len(atoms)
    best_cost = [float("inf")] * (count + 1)
    best_groups = [0] * (count + 1)
    best_short = [float("inf")] * (count + 1)
    nxt = [count] * (count + 1)
    best_cost[count] = 0.0
    for start in range(count - 1, -1, -1):
        for end in range(start + 1, count + 1):
            duration = atoms[end - 1].end - atoms[start].start
            cost = (duration - target) ** 2 + best_cost[end]
            groups = 1 + best_groups[end]
            short = duration if end == count else min(duration, best_short[end])
            chosen = best_cost[start] == float("inf")
            if not chosen and cost < best_cost[start] - 1e-9:
                chosen = True
            elif not chosen and abs(cost - best_cost[start]) <= 1e-9:
                if groups < best_groups[start] or (
                    groups == best_groups[start] and short > best_short[start]
                ):
                    chosen = True
            if not chosen:
                continue
            best_cost[start] = cost
            best_groups[start] = groups
            best_short[start] = short
            nxt[start] = end
    packed = []
    cursor = 0
    while cursor < count:
        packed.append((cursor, nxt[cursor]))
        cursor = nxt[cursor]
    return packed


class CandidateBudgetExceeded(AssertionError):
    pass


class CandidateCounter:
    """按组时长计算次数计费，不以机器运行速度判断复杂度。"""

    def __init__(self, limit: int) -> None:
        self.visits = 0
        self.limit = limit

    def endpoint(self, value: float) -> float:
        counter = self

        class CountedEndpoint(float):
            def __sub__(self, other: float) -> float:
                counter.visits += 1
                if counter.visits > counter.limit:
                    raise CandidateBudgetExceeded(f"候选访问超过预算 {counter.limit}")
                return float.__sub__(self, other)

        return CountedEndpoint(value)


class TestAudioPacking(unittest.TestCase):
    def test_empty_and_single_overlong_atom(self) -> None:
        self.assertEqual(pack_atoms([]), [])
        self.assertEqual(pack_atoms([Atom(7.0, 137.0)]), [(0, 1)])
        atoms = make_atoms([130.0, 10.0, 20.0])
        self.assertEqual(pack_atoms(atoms), [(0, 1), (1, 3)])

    def test_small_integer_samples_match_exhaustive_objective(self) -> None:
        for count in range(1, 7):
            for lengths in itertools.product((3.0, 12.0, 33.0), repeat=count):
                atoms = make_atoms(list(lengths), [1.0] * (count - 1))
                with self.subTest(lengths=lengths):
                    actual = pack_atoms(atoms)
                    self.assertEqual(packing_key(atoms, actual, 30.0), exhaustive_key(atoms, 30.0))
                    self.assertEqual(actual, original_pack_atoms(atoms, 30.0))

    def test_random_fractional_samples_match_original(self) -> None:
        randomizer = random.Random(20261126)
        for _ in range(400):
            count = randomizer.randrange(1, 25)
            lengths = [randomizer.uniform(0.001, 95.0) for _ in range(count)]
            gaps = [randomizer.uniform(0.35, 8.0) for _ in range(count - 1)]
            target = randomizer.choice((10.0, 30.0, 45.0))
            atoms = make_atoms(lengths, gaps)
            with self.subTest(lengths=lengths, target=target):
                self.assertEqual(pack_atoms(atoms, target), original_pack_atoms(atoms, target))

    def test_equal_cost_prefers_fewer_groups(self) -> None:
        atoms = make_atoms([15.0, 30.0])
        self.assertEqual(pack_atoms(atoms), [(0, 2)])

    def test_equal_cost_and_group_count_maximizes_shortest_group(self) -> None:
        atoms = make_atoms([18.0, 18.0, 12.0, 9.0, 24.0])
        actual = pack_atoms(atoms)
        self.assertEqual(actual, [(0, 2), (2, 4), (4, 5)])
        self.assertEqual(packing_key(atoms, actual, 30.0), (153.0, 3, -21.0))
        self.assertEqual(packing_key(atoms, actual, 30.0), exhaustive_key(atoms, 30.0))

    def test_near_equal_float_cost_keeps_original_tolerance(self) -> None:
        atoms = make_atoms([5.0, 10.0 + 1e-11])
        self.assertEqual(pack_atoms(atoms, 10.0), [(0, 2)])
        self.assertEqual(pack_atoms(atoms, 10.0), original_pack_atoms(atoms, 10.0))

    def test_ten_thousand_atoms_avoid_quadratic_candidate_visits(self) -> None:
        visits = []
        for count in (5000, 10000):
            counter = CandidateCounter(limit=count * 200)
            atoms = [
                Atom(index * 0.5, counter.endpoint(index * 0.5 + 0.1))
                for index in range(count)
            ]
            groups = pack_atoms(atoms)
            visits.append(counter.visits)
            self.assertEqual(groups[0][0], 0)
            self.assertEqual(groups[-1][1], count)
            self.assertEqual([end for _, end in groups[:-1]], [start for start, _ in groups[1:]])
        self.assertLess(visits[1], visits[0] * 2.5)


if __name__ == "__main__":
    unittest.main()
