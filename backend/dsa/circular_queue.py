"""
Circular Queue — fixed-size ring buffer with O(1) push and average.

Slots are pre-allocated. When full, the oldest value is silently overwritten.
No shifting, no reallocation — constant time regardless of capacity.
"""


class CircularQueue:
    def __init__(self, capacity: int):
        self._buf = [None] * capacity
        self._capacity = capacity
        self._head = 0   # index of the oldest element
        self._tail = 0   # index where the next element will be written
        self._size = 0

    def push(self, value: float):
        self._buf[self._tail] = value
        self._tail = (self._tail + 1) % self._capacity
        if self._size < self._capacity:
            self._size += 1
        else:
            # Buffer full — advance head to discard the oldest entry
            self._head = (self._head + 1) % self._capacity

    def get_all(self) -> list[float]:
        return [
            self._buf[(self._head + i) % self._capacity]
            for i in range(self._size)
        ]

    def average(self) -> float:
        vals = self.get_all()
        return sum(vals) / len(vals) if vals else 0.0

    def is_full(self) -> bool:
        return self._size == self._capacity

    def is_empty(self) -> bool:
        return self._size == 0

    @property
    def size(self) -> int:
        return self._size

    @property
    def capacity(self) -> int:
        return self._capacity
