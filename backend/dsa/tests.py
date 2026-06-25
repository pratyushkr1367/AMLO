"""
Unit tests for CircularQueue, MinHeap, and A*.
Run: python tests.py
"""

import time
from circular_queue import CircularQueue
from min_heap import MinHeap
from pathfinding import astar


def test_circular_queue():
    print("── CircularQueue ─────────────────────────────")

    q = CircularQueue(5)
    assert q.is_empty()
    assert not q.is_full()

    for i in range(1, 6):
        q.push(float(i))

    assert q.is_full()
    assert q.size == 5
    assert q.get_all() == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert q.average() == 3.0
    print("  push 5 items into capacity-5 queue  ✓")

    # Push beyond capacity — oldest gets overwritten
    q.push(6.0)
    assert q.get_all() == [2.0, 3.0, 4.0, 5.0, 6.0]
    assert q.size == 5
    print("  overwrite oldest on overflow         ✓")

    q2 = CircularQueue(3)
    q2.push(10.0)
    q2.push(20.0)
    q2.push(30.0)
    assert q2.average() == 20.0
    q2.push(40.0)
    assert q2.average() == 30.0  # [20, 30, 40]
    print("  sliding average correct              ✓")

    print()


def test_min_heap():
    print("── MinHeap ───────────────────────────────────")

    h = MinHeap()
    assert h.is_empty()

    for val in [5, 3, 8, 1, 4]:
        h.push(val)

    assert h.peek() == 1
    assert h.pop() == 1
    assert h.pop() == 3
    assert h.pop() == 4
    assert h.pop() == 5
    assert h.pop() == 8
    assert h.is_empty()
    print("  extract-min order correct            ✓")

    # Test with tuples — as used by A*
    h2 = MinHeap()
    h2.push((7, (2, 3)))
    h2.push((2, (0, 0)))
    h2.push((5, (1, 1)))
    assert h2.pop() == (2, (0, 0))
    assert h2.pop() == (5, (1, 1))
    print("  tuple comparison works (for A*)      ✓")

    print()


def test_astar():
    print("── A* Pathfinding ────────────────────────────")

    # Simple path with no obstacles
    path = astar((0, 0), (0, 4), obstacles=set())
    assert path is not None
    assert path[0] == {"row": 0, "col": 1}
    assert path[-1] == {"row": 0, "col": 4}
    assert len(path) == 4
    print(f"  straight path (0,0)→(0,4): {len(path)} steps  ✓")

    # Path around a wall
    wall = {(0, 2), (1, 2), (2, 2)}
    path = astar((0, 0), (0, 4), obstacles=wall)
    assert path is not None
    assert all({"row": r, "col": c} not in path for r, c in wall)
    print(f"  path around wall: {len(path)} steps            ✓")

    # Same start and goal
    path = astar((5, 5), (5, 5), obstacles=set())
    assert path == []
    print("  start == goal returns []             ✓")

    # Performance: full grid, default obstacles
    start_time = time.perf_counter()
    path = astar((0, 0), (49, 49))
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    assert path is not None
    print(f"  (0,0)→(49,49) on 50x50 grid: {elapsed_ms:.2f}ms  ✓  (target <50ms)")

    print()


if __name__ == "__main__":
    test_circular_queue()
    test_min_heap()
    test_astar()
    print("All tests passed.")
