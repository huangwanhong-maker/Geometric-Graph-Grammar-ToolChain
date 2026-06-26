"""2D geometric primitives: similarity transforms, convex hull, polar grid.

All routines are deterministic and self-contained (NumPy only) so the C++ port can mirror them
exactly. Points are NumPy arrays of shape ``(2,)`` or ``(N, 2)``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ArrayLike = np.ndarray
EPS = 1e-12


def as_points(p: ArrayLike) -> np.ndarray:
    """Coerce to a float ``(N, 2)`` array."""
    a = np.asarray(p, dtype=float)
    if a.ndim == 1:
        a = a.reshape(1, 2)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError(f"expected (N, 2) points, got shape {a.shape}")
    return a


def centroid(points: ArrayLike) -> np.ndarray:
    pts = as_points(points)
    return pts.mean(axis=0)


# --------------------------------------------------------------------------------------------------
# Similarity transform:  x -> s * R(theta) @ x + t   (orientation-preserving by default)
# --------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Similarity:
    """A 2D similarity transform stored as a 2x2 linear part ``A`` and translation ``b``.

    For a proper (orientation-preserving) similarity, ``A = s * R(theta)``. Reflection is allowed
    only when constructed explicitly; the default learning pipeline never uses it.
    """

    A: np.ndarray  # shape (2, 2)
    b: np.ndarray  # shape (2,)

    def __post_init__(self) -> None:
        object.__setattr__(self, "A", np.asarray(self.A, dtype=float).reshape(2, 2))
        object.__setattr__(self, "b", np.asarray(self.b, dtype=float).reshape(2))

    @staticmethod
    def identity() -> Similarity:
        return Similarity(np.eye(2), np.zeros(2))

    @staticmethod
    def from_components(
        scale: float = 1.0, angle: float = 0.0, tx: float = 0.0, ty: float = 0.0,
        *, reflect: bool = False,
    ) -> Similarity:
        c, s = np.cos(angle), np.sin(angle)
        R = np.array([[c, -s], [s, c]])
        if reflect:
            R = R @ np.array([[1.0, 0.0], [0.0, -1.0]])
        return Similarity(scale * R, np.array([tx, ty]))

    @property
    def scale(self) -> float:
        return float(np.sqrt(abs(np.linalg.det(self.A))))

    @property
    def rotation(self) -> float:
        return float(np.arctan2(self.A[1, 0], self.A[0, 0]))

    @property
    def is_orientation_preserving(self) -> bool:
        return np.linalg.det(self.A) > 0

    def apply(self, points: ArrayLike) -> np.ndarray:
        pts = as_points(points)
        out = pts @ self.A.T + self.b
        return out[0] if np.ndim(points) == 1 else out

    def compose(self, other: Similarity) -> Similarity:
        """Return the transform equivalent to ``self(other(x))``."""
        return Similarity(self.A @ other.A, self.A @ other.b + self.b)

    def inverse(self) -> Similarity:
        Ai = np.linalg.inv(self.A)
        return Similarity(Ai, -Ai @ self.b)


def similarity_from_edge(a: ArrayLike, b: ArrayLike) -> Similarity:
    """The unique proper similarity mapping ``a -> (0, 0)`` and ``b -> (1, 0)``.

    This is the canonical frame used by isomorphism normalization: it removes translation, rotation
    and scale by pinning a directed edge to the unit segment on the +x axis.
    """
    a = np.asarray(a, dtype=float).reshape(2)
    b = np.asarray(b, dtype=float).reshape(2)
    d = b - a
    length = float(np.hypot(d[0], d[1]))
    if length < EPS:
        raise ValueError("degenerate edge: endpoints coincide")
    angle = np.arctan2(d[1], d[0])
    inv = Similarity.from_components(scale=1.0 / length, angle=-angle)
    # translate a to origin first, then rotate/scale
    return inv.compose(Similarity(np.eye(2), -a))


def fit_similarity(
    src: ArrayLike, dst: ArrayLike, *, allow_reflection: bool = False
) -> tuple[Similarity, float]:
    """Least-squares similarity (Umeyama) mapping ``src -> dst``.

    Returns ``(transform, rms_residual)``. Requires at least 2 points.
    """
    X = as_points(src)
    Y = as_points(dst)
    if X.shape != Y.shape:
        raise ValueError("src and dst must have the same shape")
    n = X.shape[0]
    if n < 2:
        raise ValueError("need at least 2 point correspondences")

    mx, my = X.mean(axis=0), Y.mean(axis=0)
    Xc, Yc = X - mx, Y - my
    var_x = float((Xc**2).sum() / n)
    cov = (Yc.T @ Xc) / n  # 2x2

    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(2)
    if not allow_reflection and np.linalg.det(U @ Vt) < 0:
        S[1, 1] = -1.0
    R = U @ S @ Vt
    scale = 1.0 if var_x < EPS else float((D * np.diag(S)).sum() / var_x)
    A = scale * R
    b = my - A @ mx
    transform = Similarity(A, b)
    residual = float(np.sqrt(((transform.apply(X) - Y) ** 2).sum() / n))
    return transform, residual


# --------------------------------------------------------------------------------------------------
# Convex hull (Andrew's monotone chain) + polygon area.  Self-implemented for exact, deterministic
# 2D behaviour; 3D will delegate to qhull.
# --------------------------------------------------------------------------------------------------
def _cross(o: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points: ArrayLike) -> np.ndarray:
    """Return the convex hull vertices in counter-clockwise order (no repeated last point)."""
    pts = as_points(points)
    # unique + lexicographic sort (x, then y) for determinism
    uniq = np.unique(np.round(pts, 12), axis=0)
    uniq = uniq[np.lexsort((uniq[:, 1], uniq[:, 0]))]
    if len(uniq) <= 2:
        return uniq.copy()

    lower: list[np.ndarray] = []
    for p in uniq:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[np.ndarray] = []
    for p in uniq[::-1]:
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = np.array(lower[:-1] + upper[:-1])
    return hull


def polygon_area(polygon: ArrayLike) -> float:
    """Absolute area of a simple polygon via the shoelace formula."""
    poly = as_points(polygon)
    if len(poly) < 3:
        return 0.0
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def convex_hull_area(points: ArrayLike) -> float:
    """Area of the convex hull of the given points (0 for < 3 non-collinear points)."""
    return polygon_area(convex_hull(points))


# --------------------------------------------------------------------------------------------------
# Polar grid (the discretization used by vertex expansion, paper Fig. 6).
# --------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class PolarGrid:
    """Discretizes the neighbourhood of the origin into ``n_angle x n_dist`` polar cells.

    Angle bins span ``[0, 2*pi)``; distance bins span ``(0, max_radius]``. The paper uses 10 x 12.
    """

    n_angle: int = 10
    n_dist: int = 12
    max_radius: float = 1.0

    def cell_of(self, point: ArrayLike) -> tuple[int, int] | None:
        """Polar cell ``(angle_index, dist_index)`` of a point, or ``None`` if outside radius."""
        p = np.asarray(point, dtype=float).reshape(2)
        r = float(np.hypot(p[0], p[1]))
        if r < EPS or r > self.max_radius:
            return None
        theta = float(np.arctan2(p[1], p[0])) % (2.0 * np.pi)
        ai = min(int(theta / (2.0 * np.pi) * self.n_angle), self.n_angle - 1)
        di = min(int(r / self.max_radius * self.n_dist), self.n_dist - 1)
        return ai, di

    def cell_center(self, ai: int, di: int) -> np.ndarray:
        theta = (ai + 0.5) / self.n_angle * 2.0 * np.pi
        r = (di + 0.5) / self.n_dist * self.max_radius
        return np.array([r * np.cos(theta), r * np.sin(theta)])
