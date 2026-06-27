"""Offline tests for the EEG phase-space-reconstruction module (no network)."""

import numpy as np

from g3_2d.eeg import (
    bandpass,
    eeg_psr_graph,
    estimate_tau,
    phase_space_2d,
    synthetic_eeg,
    trajectory_graph,
)


def test_synthetic_eeg_shape():
    x, fs = synthetic_eeg(n=1000, fs=160.0)
    assert x.shape == (1000,)
    assert fs == 160.0


def test_estimate_tau_on_sine_is_quarter_period():
    fs = 160.0
    t = np.arange(2000) / fs
    x = np.sin(2 * np.pi * 10 * t)  # 10 Hz -> period 16 samples -> quarter ~ 4
    tau = estimate_tau(x)
    assert 3 <= tau <= 5


def test_phase_space_2d_shapes_and_normalization():
    x = np.arange(100, dtype=float)
    pts = phase_space_2d(x, tau=5, normalize=True)
    assert pts.shape == (95, 2)
    assert abs(pts[:, 0].mean()) < 1e-9 and abs(pts[:, 0].std() - 1.0) < 1e-6


def test_bandpass_keeps_in_band_rejects_out_of_band():
    fs = 160.0
    t = np.arange(4000) / fs
    x = np.sin(2 * np.pi * 10 * t) + np.sin(2 * np.pi * 40 * t)  # 10 Hz (keep) + 40 Hz (reject)
    y = bandpass(x, fs, 8, 13)
    target = np.sin(2 * np.pi * 10 * t)
    # filtered signal should track the 10 Hz component closely (ignore edge transients)
    err = np.abs(y[200:-200] - target[200:-200]).mean()
    assert err < 0.1


def test_trajectory_graph_is_a_path():
    pts = np.random.default_rng(0).normal(size=(50, 2))
    g = trajectory_graph(pts, count=30)
    assert g.num_vertices == 30
    assert g.num_edges == 29
    assert g.degree(0) == 1 and g.degree(15) == 2  # endpoints degree 1, interior degree 2


def test_eeg_psr_graph_synthetic_end_to_end():
    g, meta = eeg_psr_graph(source="synthetic", count=200, band=(8, 13))
    assert g.num_vertices == 200
    assert meta["source"] == "synthetic" and meta["band"] == (8, 13)
