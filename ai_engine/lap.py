from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

__version__ = "0.5.12-fallback"


def lapjv(cost_matrix, extend_cost: bool = True, cost_limit: float = np.inf):
    """Minimal SciPy-backed fallback for Ultralytics BYTETrack.

    This mirrors the subset of the `lap` API that Ultralytics uses:
    it returns `(total_cost, x, y)` where `x[row] = col` and `y[col] = row`,
    or `-1` when a row/column remains unmatched.
    """
    matrix = np.asarray(cost_matrix, dtype=float)

    if matrix.ndim != 2:
        raise ValueError("cost_matrix must be 2-dimensional")

    rows_count, cols_count = matrix.shape
    x = np.full(rows_count, -1, dtype=int)
    y = np.full(cols_count, -1, dtype=int)

    if matrix.size == 0:
        return 0.0, x, y

    rows, cols = linear_sum_assignment(matrix)

    total_cost = 0.0
    for row, col in zip(rows, cols):
        cost = float(matrix[row, col])
        if cost <= cost_limit:
            x[row] = col
            y[col] = row
            total_cost += cost

    return total_cost, x, y
