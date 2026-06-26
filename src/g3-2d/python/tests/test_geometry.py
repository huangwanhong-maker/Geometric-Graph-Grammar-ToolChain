import numpy as np

from g3_2d.geometry import (
    PolarGrid,
    Similarity,
    convex_hull_area,
    fit_similarity,
    similarity_from_edge,
)


def test_identity_apply():
    ident = Similarity.identity()
    p = np.array([[1.0, 2.0], [3.0, 4.0]])
    assert np.allclose(ident.apply(p), p)


def test_components_scale_rotation():
    T = Similarity.from_components(scale=2.0, angle=np.pi / 2, tx=1.0, ty=-1.0)
    assert np.isclose(T.scale, 2.0)
    assert np.isclose(T.rotation, np.pi / 2)
    # rotate (1,0) by 90deg, scale 2 -> (0,2), then translate (1,-1) -> (1,1)
    assert np.allclose(T.apply(np.array([1.0, 0.0])), [1.0, 1.0])


def test_compose_inverse_roundtrip():
    T = Similarity.from_components(scale=1.5, angle=0.7, tx=2.0, ty=-3.0)
    p = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, -1.0]])
    assert np.allclose(T.inverse().apply(T.apply(p)), p)
    assert np.allclose(T.compose(T.inverse()).apply(p), p)


def test_similarity_from_edge_pins_unit_segment():
    a, b = np.array([3.0, 1.0]), np.array([3.0, 4.0])  # vertical edge, length 3
    T = similarity_from_edge(a, b)
    assert np.allclose(T.apply(a), [0.0, 0.0])
    assert np.allclose(T.apply(b), [1.0, 0.0])


def test_fit_similarity_recovers_transform():
    rng = np.random.default_rng(0)
    src = rng.normal(size=(6, 2))
    T = Similarity.from_components(scale=1.7, angle=0.9, tx=-2.0, ty=5.0)
    dst = T.apply(src)
    fit, res = fit_similarity(src, dst)
    assert res < 1e-9
    assert np.allclose(fit.apply(src), dst)


def test_fit_similarity_rejects_reflection_by_default():
    src = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    dst = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, -1.0]])  # mirror across x-axis
    fit, res = fit_similarity(src, dst, allow_reflection=False)
    assert fit.is_orientation_preserving
    assert res > 0.1  # cannot match a reflection with a proper similarity


def test_convex_hull_area_square_and_triangle():
    square = [[0, 0], [1, 0], [1, 1], [0, 1]]
    assert np.isclose(convex_hull_area(square), 1.0)
    triangle = [[0, 0], [2, 0], [0, 2]]
    assert np.isclose(convex_hull_area(triangle), 2.0)
    # interior point does not change the hull area
    assert np.isclose(convex_hull_area(square + [[0.5, 0.5]]), 1.0)


def test_convex_hull_area_collinear_is_zero():
    assert convex_hull_area([[0, 0], [1, 0], [2, 0]]) == 0.0


def test_polar_grid_binning():
    grid = PolarGrid(n_angle=4, n_dist=2, max_radius=2.0)
    assert grid.cell_of([1.5, 0.0]) == (0, 1)  # angle ~0, far ring
    assert grid.cell_of([0.0, 0.5]) == (1, 0)  # angle 90deg, near ring
    assert grid.cell_of([5.0, 0.0]) is None  # outside radius
    assert grid.cell_of([0.0, 0.0]) is None  # at origin
    ai, di = grid.cell_of([1.5, 0.0])
    center = grid.cell_center(ai, di)
    assert grid.cell_of(center) == (ai, di)
