"""Example usage of pretty_audio.

Requires some real .wav/.mp3 instrument samples under ./samples/.
"""

from pretty_audio import PrettyAudio, Instrument, SampleRegion, Note
from pretty_audio.render import synthesize
from pretty_audio.io import save_wav

# 1. Container -----------------------------------------------------------
pa = PrettyAudio(sample_rate=44100, tempo=120)

# 2. Instrument with real samples mapped to key/velocity ranges ---------
piano = Instrument(name="Grand Piano", program=0)
piano.regions = [
    # Soft layer, low register
    SampleRegion("samples/piano_c3_soft.wav",
                 note_low=48, note_high=55,
                 velocity_low=0, velocity_high=63,
                 root_pitch=48, gain=0.9),
    # Loud layer, low register
    SampleRegion("samples/piano_c3_loud.wav",
                 note_low=48, note_high=55,
                 velocity_low=64, velocity_high=127,
                 root_pitch=48, gain=1.1),
    # Soft layer, middle register
    SampleRegion("samples/piano_c4_soft.wav",
                 note_low=56, note_high=63,
                 velocity_low=0, velocity_high=63,
                 root_pitch=60, gain=0.9),
    # Loud layer, middle register
    SampleRegion("samples/piano_c4_loud.wav",
                 note_low=56, note_high=63,
                 velocity_low=64, velocity_high=127,
                 root_pitch=60, gain=1.1),
]
pa.add_instrument(piano)

# 3. Notes (a simple C major arpeggio, in seconds & MIDI pitch) ---------
piano.notes = [
    Note(start=0.0, end=1.0, pitch=60, velocity=80, instrument=0),  # C4
    Note(start=0.25, end=1.25, pitch=64, velocity=70, instrument=0), # E4
    Note(start=0.5, end=1.5, pitch=67, velocity=60, instrument=0),   # G4
    Note(start=0.75, end=1.75, pitch=72, velocity=90, instrument=0), # C5
]

# 4. Render --------------------------------------------------------------
audio = synthesize(pa, duration=2.5)

# 5. Save ----------------------------------------------------------------
save_wav("output.wav", audio, sample_rate=pa.sample_rate)
print("Wrote output.wav,", len(audio) / pa.sample_rate, "seconds")
