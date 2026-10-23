"""Audio file I/O for pretty_audio.

Loads .wav, .mp3, and .mpeg files into mono float32 numpy arrays at a target
sample rate, using librosa (which handles MP3 via audioread/ffmpeg).
"""

from __future__ import annotations

import numpy as np


def load_sample(path: str, sample_rate: int = 44100, mono: bool = True):
    """Load an audio file as mono float32 at ``sample_rate``.

    Parameters
    ----------
    path : str
        Path to a .wav, .mp3, or .mpeg file.
    sample_rate : int
        Target sample rate; the file is resampled if needed.
    mono : bool
        Whether to mix down to mono.

    Returns
    -------
    y : np.ndarray, shape (n_samples,) [, n_channels]
        Audio data as float32 in [-1, 1].
    sr : int
        The actual sample rate (== ``sample_rate`` when resampling).
    """
    import librosa

    y, sr = librosa.load(path, sr=sample_rate, mono=mono)
    if y.dtype != np.float32:
        y = y.astype(np.float32)
    return y, sr


def save_wav(path: str, audio: np.ndarray, sample_rate: int = 44100) -> None:
    """Save a float32 numpy array as a 16-bit PCM WAV file."""
    import soundfile as sf

    audio = np.asarray(audio, dtype=np.float32)
    # Clamp to avoid clipping on write
    audio = np.clip(audio, -1.0, 1.0)
    sf.write(path, audio, sample_rate, subtype="PCM_16")
