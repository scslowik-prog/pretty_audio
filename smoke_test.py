"""End-to-end smoke test for pretty_audio.

Creates a synthetic .wav sample, builds a PrettyAudio performance, renders it,
and saves a WAV.  Monkeypatches librosa's pitch_shift to identity so the test
runs even without librosa installed (validates engine logic).
"""

import numpy as np
import soundfile as sf

import pretty_audio
from pretty_audio import PrettyAudio, Instrument, SampleRegion, Note
from pretty_audio.render import synthesize, _pitch_shift_semitones
import pretty_audio.io as io

SR = 44100

# --- 1. Create a synthetic "sample": sine wave at MIDI 60 (middle C) -------
def make_sample(path, duration=1.0, freq=261.63, root_pitch=60):
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)
    y = 0.5 * np.sin(2 * np.pi * freq * t).astype(np.float32)
    sf.write(path, y, SR, subtype="PCM_16")

make_sample("samples/piano_c3_soft.wav")
make_sample("samples/piano_c3_loud.wav", freq=261.63)

# --- 2. Monkeypatch librosa bits so we don't need them installed -----------
import pretty_audio.render as render

def identity_shift(y, sr, semitones):
    return y

render._pitch_shift_semitones = identity_shift

def fake_load(path, sample_rate=SR, mono=True):
    y, sr = sf.read(path, always_2d=False)
    if y.dtype != np.float32:
        y = y.astype(np.float32)
    if y.ndim > 1:
        y = y.mean(axis=1)
    return y, sr

io.load_sample = fake_load
render.load_sample = fake_load

# --- 3. Build the performance -----------------------------------------------
pa = PrettyAudio(sample_rate=SR, tempo=120)
piano = Instrument(name="Test Piano")
# Pitch 52 = E3, which lies inside note range [48, 55] (C3-G3)
piano.regions = [
    SampleRegion("samples/piano_c3_soft.wav",
                 note_low=48, note_high=55,
                 velocity_low=0, velocity_high=63, root_pitch=52, gain=1.0),
    SampleRegion("samples/piano_c3_loud.wav",
                 note_low=48, note_high=55,
                 velocity_low=64, velocity_high=127, root_pitch=52, gain=1.0),
]
pa.add_instrument(piano)

piano.notes = [
    Note(start=0.0, end=0.6, pitch=52, velocity=80, instrument=0),  # loud layer (E3)
    Note(start=0.3, end=0.9, pitch=52, velocity=40, instrument=0),  # soft layer (overlap -> polyphony)
]

# --- 4. Render --------------------------------------------------------------
audio = synthesize(pa, duration=1.5)
print("rendered length:", len(audio), "samples =", len(audio) / SR, "seconds")
print("peak amplitude :", float(np.max(np.abs(audio))))

# --- 5. Save ----------------------------------------------------------------
from pretty_audio.io import save_wav
save_wav("smoke_output.wav", audio, sample_rate=SR)
print("wrote smoke_output.wav")

# --- 6. Sanity assertions ---------------------------------------------------
assert len(audio) == int(1.5 * SR), "wrong output length"
assert np.max(np.abs(audio)) <= 1.0 + 1e-6, "clipped output"
assert np.max(np.abs(audio)) > 0.01, "output is silent - nothing mixed"
print("ALL SMOKE TEST ASSERTIONS PASSED")
