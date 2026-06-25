"""
Min-Heap — binary heap where the smallest element is always at the root.

Built from scratch on a Python list. No heapq.
Insert and extract-min are both O(log n).
Used by A* to always expand the lowest-cost node next.
"""


class MinHeap:
    def __init__(self):
        self._heap: list = []

    def push(self, item):
        self._heap.append(item)
        self._sift_up(len(self._heap) - 1)

    def pop(self):
        if not self._heap:
            raise IndexError("pop from empty heap")
        self._swap(0, len(self._heap) - 1)
        item = self._heap.pop()
        if self._heap:
            self._sift_down(0)
        return item

    def peek(self):
        if not self._heap:
            raise IndexError("peek at empty heap")
        return self._heap[0]

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def __len__(self) -> int:
        return len(self._heap)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _sift_up(self, i: int):
        while i > 0:
            parent = (i - 1) // 2
            if self._heap[i] < self._heap[parent]:
                self._swap(i, parent)
                i = parent
            else:
                break

    def _sift_down(self, i: int):
        n = len(self._heap)
        while True:
            smallest = i
            left, right = 2 * i + 1, 2 * i + 2
            if left < n and self._heap[left] < self._heap[smallest]:
                smallest = left
            if right < n and self._heap[right] < self._heap[smallest]:
                smallest = right
            if smallest != i:
                self._swap(i, smallest)
                i = smallest
            else:
                break

    def _swap(self, i: int, j: int):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
