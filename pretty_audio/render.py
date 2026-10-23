"""Render engine: turn PrettyAudio + sample regions into real audio.

The synthesizer walks every note, finds its SampleRegion, loads/pitch-shifts
the audio, applies velocity gain + an ADSR envelope, and mixes it into the
output buffer at the note's start time.
"""

from __future__ import annotations

import numpy as np

from .core import PrettyAudio
from .io import load_sample


# --------------------------------------------------------------------------- #
# Envelopes
# --------------------------------------------------------------------------- #
def adsr_envelope(
    n_samples: int,
    sample_rate: int,
    attack: float = 0.01,
    decay: float = 0.1,
    sustain: float = 0.7,
    release: float = 0.2,
) -> np.ndarray:
    """Simple linear ADSR envelope (length ``n_samples``)."""
    env = np.ones(n_samples, dtype=np.float32)
    n_a = int(attack * sample_rate)
    n_d = int(decay * sample_rate)
    n_r = int(release * sample_rate)
    n_s = max(0, n_samples - n_a - n_d - n_r)

    if n_a > 0:
        env[:n_a] = np.linspace(0.0, 1.0, n_a, dtype=np.float32)
    if n_d > 0:
        env[n_a : n_a + n_d] = np.linspace(1.0, sustain, n_d, dtype=np.float32)
    if n_s > 0:
        env[n_a + n_d : n_a + n_d + n_s] = sustain
    if n_r > 0 and n_a + n_d + n_s < n_samples:
        env[n_a + n_d + n_s :] = np.linspace(sustain, 0.0, n_r, dtype=np.float32)
    return env


# --------------------------------------------------------------------------- #
# Sample cache (avoid reloading the same file many times)
# --------------------------------------------------------------------------- #
class _SampleCache:
    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self._cache: dict[str, tuple[np.ndarray, int]] = {}

    def get(self, path: str):
        if path not in self._cache:
            self._cache[path] = load_sample(path, sample_rate=self.sample_rate)
        return self._cache[path]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _pitch_shift_semitones(y: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """Pitch-shift ``y`` by ``semitones`` using librosa (phase vocoder)."""
    import librosa

    if semitones == 0:
        return y
    y_shifted = librosa.effects.pitch_shift(y.astype(np.float32), sr=sr,
                                            n_steps=semitones)
    return y_shifted.astype(np.float32)


def _velocity_gain(velocity: int) -> float:
    """Map MIDI velocity (0-127) to a linear gain."""
    return (velocity / 127.0) ** 0.5  # gentle curve; tweak to taste


def _mix_into(buffer: np.ndarray, audio: np.ndarray, start_sample: int) -> None:
    """Add ``audio`` into ``buffer`` starting at ``start_sample``."""
    end = min(start_sample + len(audio), len(buffer))
    if end <= start_sample:
        return
    n = end - start_sample
    buffer[start_sample:end] += audio[:n]


# --------------------------------------------------------------------------- #
# Main render
# --------------------------------------------------------------------------- #
def synthesize(
    pretty_audio: PrettyAudio,
    duration: float | None = None,
    attack: float = 0.005,
    decay: float = 0.05,
    sustain: float = 0.6,
    release: float = 0.15,
) -> np.ndarray:
    """Render a ``PrettyAudio`` performance to a mono float32 numpy array.

    Parameters
    ----------
    pretty_audio : PrettyAudio
        The performance to render.
    duration : float, optional
        Output length in seconds.  Defaults to the end of the last note plus
        a short release tail.
    attack, decay, sustain, release : float
        ADSR envelope parameters applied to every triggered sample.

    Returns
    -------
    audio : np.ndarray, shape (n_samples,), float32
        The rendered mix, normalized to peak <= 1.0.
    """
    sr = pretty_audio.sample_rate
    if duration is None:
        duration = pretty_audio.get_end_time() + release + 0.5
    n_total = int(duration * sr)
    buffer = np.zeros(n_total, dtype=np.float32)

    cache = _SampleCache(sr)

    for inst in pretty_audio.instruments:
        for note in inst.notes:
            region = inst.find_region(note.pitch, note.velocity)
            if region is None:
                continue  # no sample for this pitch/velocity -> silence

            y, _ = cache.get(region.sample_path)

            # Pitch-shift from the sample's recorded root pitch to the note.
            semitones = note.pitch - region.root_pitch
            y = _pitch_shift_semitones(y, sr, semitones)

            # Velocity -> gain, times the region's own gain.
            gain = _velocity_gain(note.velocity) * region.gain
            y = y * gain

            # Apply ADSR envelope sized to the (shifted) sample length.
            env = adsr_envelope(len(y), sr, attack, decay, sustain, release)
            y = y * env

            # Place at the note's start time.
            start_sample = int(note.start * sr)
            _mix_into(buffer, y, start_sample)

    # Normalize to avoid clipping, but preserve quiet dynamics.
    peak = np.max(np.abs(buffer))
    if peak > 1.0:
        buffer = buffer / peak
    elif peak > 0:
        buffer = buffer / peak  # normalize to full scale (optional; remove if
                                # you want to preserve absolute loudness)

    return buffer.astype(np.float32)
