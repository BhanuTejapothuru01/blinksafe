"""
SleepGuard — Math / Calculation Utilities

Shared geometric computations consumed by detection modules.
Detection modules import from here; this module never imports from detection/.
"""

import numpy as np


def euclidean_distance(point_a, point_b):
    """Euclidean distance between two 2D/3D points (tuples or arrays)."""
    a = np.array(point_a, dtype=np.float64)
    b = np.array(point_b, dtype=np.float64)
    return float(np.linalg.norm(a - b))


def calculate_ear(eye_points: list) -> float:
    """
    Calculate Eye Aspect Ratio (EAR) given 6 eye landmark points:
    [p1, p2, p3, p4, p5, p6]
    where p1, p4 are horizontal corners and (p2, p6), (p3, p5) are vertical pairs.

    EAR = (||p2 - p6|| + ||p3 - p5||) / (2.0 * ||p1 - p4||)
    """
    if not eye_points or len(eye_points) != 6:
        return 0.0

    p1, p2, p3, p4, p5, p6 = eye_points
    v1 = euclidean_distance(p2, p6)
    v2 = euclidean_distance(p3, p5)
    horiz = euclidean_distance(p1, p4)

    if horiz == 0.0:
        return 0.0

    ear = (v1 + v2) / (2.0 * horiz)
    return float(ear)


def calculate_mar(mouth_points: list) -> float:
    """
    Calculate Mouth Aspect Ratio (MAR) given mouth landmark points:
    [p1, p2, p3, p4, p5, p6, p7, p8]
    where p1, p5 are corners (left, right), (p2, p8), (p3, p7), (p4, p6) are top/bottom vertical pairs.

    MAR = (||p2 - p8|| + ||p3 - p7|| + ||p4 - p6||) / (2.0 * ||p1 - p5||)
    """
    if not mouth_points or len(mouth_points) != 8:
        return 0.0

    p1, p2, p3, p4, p5, p6, p7, p8 = mouth_points
    v1 = euclidean_distance(p2, p8)
    v2 = euclidean_distance(p3, p7)
    v3 = euclidean_distance(p4, p6)
    horiz = euclidean_distance(p1, p5)

    if horiz == 0.0:
        return 0.0

    mar = (v1 + v2 + v3) / (2.0 * horiz)
    return float(mar)
