"""Phase-space reconstruction (PSR) of a single EEG channel into a 2D geometric graph.

A scalar time series ``x(t)`` is embedded into 2D by time-delay coordinates (Takens):
``P[i] = (x[i], x[i + tau])``. Consecutive embedded points are joined into a trajectory path, giving
a geometric graph whose shape is the channel's 2D phase-space attractor. Recurring waveform patterns
(e.g. an alpha rhythm) become recurring loops in that trajectory - exactly the kind of repeated
geometric structure the grammar learner detects.

EEG is read from EDF (a minimal stdlib reader, no MNE dependency); a synthetic EEG-like signal is
provided as an offline fallback.
"""

from __future__ import annotations

import struct
import urllib.request

import numpy as np

from .graph import GeometricGraph

# A real 64-channel EEG record from PhysioNet's EEG Motor Movement/Imagery DB. R02 is the
# eyes-closed baseline, where the occipital alpha rhythm is strong (clean phase-space loops).
PHYSIONET_EDF = "https://physionet.org/files/eegmmidb/1.0.0/S001/S001R02.edf"


# --------------------------------------------------------------------------------------------------
# Minimal EDF reader
# --------------------------------------------------------------------------------------------------
def read_edf_channel(data: bytes, channel: int = 0) -> tuple[np.ndarray, float]:
    """Read one channel from EDF bytes; returns ``(signal, sampling_rate_hz)``."""
    ns = int(data[252:256])
    n_records = int(data[236:244])
    rec_duration = float(data[244:252])

    off = 256
    labels = [data[off + i * 16:off + (i + 1) * 16].decode("latin1").strip() for i in range(ns)]
    off += ns * 16 + ns * 80 + ns * 8  # skip transducers + physical dimensions

    def block(width: int) -> list[str]:
        nonlocal off
        vals = [data[off + i * width:off + (i + 1) * width].decode("latin1").strip()
                for i in range(ns)]
        off += ns * width
        return vals

    phys_min = [float(v) for v in block(8)]
    phys_max = [float(v) for v in block(8)]
    dig_min = [float(v) for v in block(8)]
    dig_max = [float(v) for v in block(8)]
    off += ns * 80  # prefiltering
    spr = [int(v) for v in block(8)]  # samples per data record, per signal
    off += ns * 32  # reserved -> end of header

    if not 0 <= channel < ns:
        raise IndexError(f"channel {channel} out of range (0..{ns - 1}); labels={labels[:ns]}")

    record_samples = sum(spr)
    out = np.empty(n_records * spr[channel], dtype=np.float64)
    scale = (phys_max[channel] - phys_min[channel]) / (dig_max[channel] - dig_min[channel])
    pos = off
    start_in_record = sum(spr[:channel])
    write = 0
    for _ in range(n_records):
        base = pos + start_in_record * 2
        raw = struct.unpack_from(f"<{spr[channel]}h", data, base)
        seg = (np.asarray(raw) - dig_min[channel]) * scale + phys_min[channel]
        out[write:write + spr[channel]] = seg
        write += spr[channel]
        pos += record_samples * 2
    return out, spr[channel] / rec_duration


def download_eeg(url: str = PHYSIONET_EDF, channel: int = 0, *, timeout: int = 120
                 ) -> tuple[np.ndarray, float]:
    req = urllib.request.Request(url, headers={"User-Agent": "g3-2d-eeg/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted endpoint)
        return read_edf_channel(resp.read(), channel)


def synthetic_eeg(n: int = 4000, fs: float = 160.0, seed: int = 0) -> tuple[np.ndarray, float]:
    """An EEG-like signal: alpha + theta rhythms over 1/f-ish noise (offline fallback)."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / fs
    alpha = np.sin(2 * np.pi * 10 * t) * (1 + 0.3 * np.sin(2 * np.pi * 0.5 * t))
    theta = 0.5 * np.sin(2 * np.pi * 5 * t + 0.7)
    noise = np.cumsum(rng.normal(0, 0.05, n))  # brown-ish background
    return alpha + theta + 0.5 * noise, fs


# --------------------------------------------------------------------------------------------------
# Phase-space reconstruction
# --------------------------------------------------------------------------------------------------
def bandpass(x: np.ndarray, fs: float, lo: float, hi: float) -> np.ndarray:
    """Zero-phase FFT band-pass filter (e.g. ``lo,hi = 8,13`` isolates the EEG alpha rhythm)."""
    spectrum = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1.0 / fs)
    spectrum[(freqs < lo) | (freqs > hi)] = 0.0
    return np.fft.irfft(spectrum, n=len(x))


def estimate_tau(x: np.ndarray, max_lag: int = 100) -> int:
    """Estimate the embedding delay as the first zero crossing of the autocorrelation."""
    x = x - x.mean()
    denom = float(np.dot(x, x)) or 1.0
    for lag in range(1, min(max_lag, len(x) - 1)):
        if float(np.dot(x[:-lag], x[lag:])) / denom <= 0.0:
            return lag
    return max(1, max_lag // 4)


def phase_space_2d(x: np.ndarray, tau: int, *, normalize: bool = True) -> np.ndarray:
    """Time-delay embed ``x`` into 2D: rows are ``(x[i], x[i + tau])``."""
    pts = np.column_stack([x[:-tau], x[tau:]])
    if normalize:
        pts = (pts - pts.mean(axis=0)) / (pts.std(axis=0) + 1e-12)
    return pts


def trajectory_graph(points: np.ndarray, *, start: int = 0, count: int | None = None
                     ) -> GeometricGraph:
    """Connect a contiguous window of embedded points into a trajectory path graph."""
    if count is not None:
        points = points[start:start + count]
    else:
        points = points[start:]
    g = GeometricGraph()
    for i, p in enumerate(points):
        g.add_vertex(i, (float(p[0]), float(p[1])))
    for i in range(len(points) - 1):
        g.add_edge(i, i + 1)
    return g


def eeg_psr_graph(
    *, source: str = "download", channel: int = 0, tau: int | None = None,
    count: int = 600, start: int = 0, band: tuple[float, float] | None = None,
    url: str = PHYSIONET_EDF,
) -> tuple[GeometricGraph, dict]:
    """End-to-end: get a single EEG channel, PSR-embed it, return a trajectory graph + metadata.

    ``band=(lo, hi)`` band-passes the channel first (e.g. ``(8, 13)`` for the alpha rhythm), which
    turns the noisy broadband attractor into clean recurring oscillation loops.
    """
    if source == "synthetic":
        x, fs = synthetic_eeg()
        label = "synthetic"
    else:
        x, fs = download_eeg(url, channel)
        label = f"channel {channel}"
    if band is not None:
        x = bandpass(x, fs, *band)
    if tau is None:
        tau = estimate_tau(x)
    pts = phase_space_2d(x, tau)
    g = trajectory_graph(pts, start=start, count=count)
    return g, {"source": label, "fs": fs, "tau": tau, "band": band,
               "samples": len(x), "points": g.num_vertices}


def _main(argv: list[str] | None = None) -> int:
    import argparse

    from .io import save_json

    parser = argparse.ArgumentParser(
        description="Phase-space-reconstruct one EEG channel into a 2D trajectory graph."
    )
    parser.add_argument("--source", choices=["download", "synthetic"], default="download")
    parser.add_argument("--channel", type=int, default=0, help="EEG channel index")
    parser.add_argument("--tau", type=int, default=None, help="embedding delay (auto if omitted)")
    parser.add_argument("--count", type=int, default=600, help="number of trajectory points")
    parser.add_argument("--start", type=int, default=0, help="start sample of the window")
    parser.add_argument("--band", nargs=2, type=float, metavar=("LO", "HI"), default=None,
                        help="band-pass (Hz) before embedding, e.g. 8 13 for the alpha rhythm")
    parser.add_argument("--url", default=PHYSIONET_EDF, help="EDF url for --source download")
    parser.add_argument("-o", "--out", required=True, help="output graph JSON")
    args = parser.parse_args(argv)

    g, meta = eeg_psr_graph(source=args.source, channel=args.channel, tau=args.tau,
                            count=args.count, start=args.start,
                            band=tuple(args.band) if args.band else None, url=args.url)
    save_json(g, args.out)
    print(f"{meta['source']}: fs={meta['fs']}Hz, tau={meta['tau']}, "
          f"{meta['samples']} samples -> {g.num_vertices} points, {g.num_edges} edges")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
