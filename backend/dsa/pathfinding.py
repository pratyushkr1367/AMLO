"""
A* Pathfinding Engine — finds the optimal AGV route on the 50x50 factory grid.

Uses the custom MinHeap (no heapq). Each step costs 1 (uniform grid).
Heuristic: Manhattan distance — admissible on a 4-directional grid.
Returns an ordered list of {"row": r, "col": c} cells for the AGV Emulator.
"""

from min_heap import MinHeap

GRID_SIZE = 50

# Machine locations from seed data — treated as impassable obstacles
DEFAULT_OBSTACLES: set[tuple[int, int]] = {
    (5, 10), (5, 20), (15, 10), (15, 25),
    (25, 15), (35, 10), (35, 30),
}

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right


def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(
    start: tuple[int, int],
    goal: tuple[int, int],
    obstacles: set[tuple[int, int]] | None = None,
) -> list[dict] | None:
    """
    Returns the shortest path from start to goal as a list of grid cells,
    or None if no path exists.

    start / goal : (row, col) tuples
    obstacles    : set of impassable (row, col) cells; defaults to machine locations
    """
    if obstacles is None:
        obstacles = DEFAULT_OBSTACLES

    if start == goal:
        return []

    # open_heap stores (f_cost, position)
    # Tuple comparison works: f_cost compared first, then position as tiebreaker
    open_heap = MinHeap()
    open_heap.push((0 + _heuristic(start, goal), start))

    g_cost: dict[tuple, int] = {start: 0}
    came_from: dict[tuple, tuple] = {}
    closed: set[tuple[int, int]] = set()

    while not open_heap.is_empty():
        _, current = open_heap.pop()

        if current in closed:
            continue
        closed.add(current)

        if current == goal:
            return _reconstruct(came_from, current)

        row, col = current
        for dr, dc in DIRECTIONS:
            neighbor = (row + dr, col + dc)
            nr, nc = neighbor

            if not (0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE):
                continue
            if neighbor in obstacles or neighbor in closed:
                continue

            tentative_g = g_cost[current] + 1
            if tentative_g < g_cost.get(neighbor, float("inf")):
                g_cost[neighbor] = tentative_g
                came_from[neighbor] = current
                f = tentative_g + _heuristic(neighbor, goal)
                open_heap.push((f, neighbor))

    return None  # no path found


def _reconstruct(came_from: dict, current: tuple) -> list[dict]:
    path = []
    while current in came_from:
        path.append({"row": current[0], "col": current[1]})
        current = came_from[current]
    path.reverse()
    return path
