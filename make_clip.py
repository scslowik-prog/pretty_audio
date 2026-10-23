"""Create a short guitar music clip using pretty_audio + real samples.

Renders an arpeggiated chord progression using the converted Iowa/2496
guitar samples (samples/guitar/*.wav).
"""

from pathlib import Path
from pretty_audio import PrettyAudio, Instrument, Note, build_regions_from_folder
from pretty_audio.render import synthesize
from pretty_audio.io import save_wav

SAMPLE_DIR = Path("samples/guitar")
OUT_PATH = Path("guitar_clip.wav")

# ---------------------------------------------------------------------------
# 1. Build regions from the converted guitar samples
# ---------------------------------------------------------------------------
regions = build_regions_from_folder(SAMPLE_DIR)
print(f"Loaded {len(regions)} sample regions")

guitar = Instrument(name="Guitar 2496 (Iowa MIS)", program=25)  # acoustic guitar (nylon)
guitar.regions = regions

# ---------------------------------------------------------------------------
# 2. Compose an arpeggiated progression: Am -> F -> C -> G -> Am
#    Velocity selects the dynamic layer (pp/mf/ff).
# ---------------------------------------------------------------------------
notes = []

def arp(start, pitches, velocity, dur=0.5, spacing=0.12):
    """Add an arpeggio: one note per pitch, staggered by ``spacing`` seconds."""
    for i, p in enumerate(pitches):
        notes.append(Note(
            start=start + i * spacing,
            end=start + i * spacing + dur,
            pitch=p,
            velocity=velocity,
            instrument=0,
        ))

# Am (A C E) — ff layer, bright
arp(0.0,  [45, 48, 52, 57],  110)   # A2 C3 E3 A3
# F (F A C) — mf layer
arp(1.6,  [53, 57, 60],      80)    # F3 A3 C4
# C (C E G) — mf layer
arp(3.2,  [48, 52, 55],      85)    # C3 E3 G3
# G (B D G) — ff layer
arp(4.8,  [47, 50, 55],      105)   # B2 D3 G3
# Am resolve — soft pp layer, let ring
arp(6.4,  [45, 48, 52, 57],  50)    # A2 C3 E3 A3, soft

# Let the final chord ring out
notes.append(Note(start=7.6, end=9.0, pitch=45, velocity=45, instrument=0))
notes.append(Note(start=7.6, end=9.0, pitch=48, velocity=45, instrument=0))
notes.append(Note(start=7.6, end=9.0, pitch=52, velocity=45, instrument=0))

guitar.notes = notes

# ---------------------------------------------------------------------------
# 3. Render
# ---------------------------------------------------------------------------
pa = PrettyAudio(sample_rate=44100, tempo=90)
pa.add_instrument(guitar)

print("Rendering... (this may take several minutes on 96 kHz source samples)")
audio = synthesize(pa, duration=9.5)
print(f"Rendered {len(audio) / pa.sample_rate:.2f} seconds, peak={abs(audio).max():.3f}")

# ---------------------------------------------------------------------------
# 4. Save
# ---------------------------------------------------------------------------
save_wav(OUT_PATH, audio, sample_rate=pa.sample_rate)
print(f"Saved {OUT_PATH}")
