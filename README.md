# pretty_audio

A **pretty-midi-like** Python library, but for *realistic recorded audio* (`.wav`, `.mp3`/`.mpeg`) instead of symbolic MIDI.

## The idea

[pretty-midi](https://github.com/craffel/pretty-midi) parses MIDI into tidy objects (`PrettyMIDI` → `Instrument` → `Note`, `ControlChange`, …) and renders them to audio through a synthesizer such as FluidSynth.

`pretty_audio` does the same thing, except the "notes" are triggered from **real recorded instrument samples**. Instead of MIDI program numbers driving a synth, you map sample regions (key range × velocity range × root pitch) to MIDI pitches and render a mixdown of real audio.

```
pretty-midi:   MIDI file  →  symbolic Note objects  →  FluidSynth  →  audio
pretty_audio:  sample set →  SampleRegion objects   →  render engine →  audio
```

## Core concepts

| pretty-midi | pretty_audio | Purpose |
|-------------|--------------|---------|
| `PrettyMIDI` | `PrettyAudio` | Top-level container (tempo, time signature, instruments) |
| `Instrument` | `Instrument` | One instrument with sample regions + its note events |
| `Note` | `Note` | `start`, `end`, `pitch`, `velocity` (seconds & MIDI pitch) |
| — | `SampleRegion` | One audio file mapped to a note range + velocity range (+ root pitch) |
| `pretty_midi.synthesize` | `render.synthesize` | Trigger samples, pitch-shift, envelope, mix → numpy audio |

## Installation

```bash
git clone <repo>
cd pretty_audio
pip install -e .
```

Dependencies: `numpy`, `librosa` (loads `.wav` and `.mp3`/`.mpeg` via audioread), `soundfile` (WAV writing).

## Quick example

```python
from pretty_audio import PrettyAudio, Instrument, SampleRegion, Note
from pretty_audio.render import synthesize
from pretty_audio.io import save_wav

pa = PrettyAudio(sample_rate=44100, tempo=120)

piano = Instrument(name="Grand Piano")
piano.regions = [
    SampleRegion("samples/piano_c3_soft.wav",
                 note_low=48, note_high=55,
                 velocity_low=0, velocity_high=63, root_pitch=48),
    SampleRegion("samples/piano_c3_loud.wav",
                 note_low=48, note_high=55,
                 velocity_low=64, velocity_high=127, root_pitch=48),
    SampleRegion("samples/piano_c4_soft.wav",
                 note_low=56, note_high=63,
                 velocity_low=0, velocity_high=63, root_pitch=60),
    SampleRegion("samples/piano_c4_loud.wav",
                 note_low=56, note_high=63,
                 velocity_low=64, velocity_high=127, root_pitch=60),
]
pa.add_instrument(piano)

piano.notes = [
    Note(start=0.0, end=1.0, pitch=60, velocity=80),  # C4
    Note(start=0.25, end=1.25, pitch=64, velocity=70),  # E4
    Note(start=0.5, end=1.5, pitch=67, velocity=60),    # G4
]

audio = synthesize(pa, duration=2.5)
save_wav("output.wav", audio, sample_rate=pa.sample_rate)
```

## How it works

1. You build a `PrettyAudio` and add `Instrument`s.
2. Each `Instrument` owns `SampleRegion`s — real `.wav`/`.mp3` files mapped to inclusive MIDI pitch and velocity ranges, with a `root_pitch` (the pitch the file was recorded at).
3. You add `Note`s (`start`, `end`, `pitch`, `velocity` in seconds/MIDI) to instruments.
4. `synthesize()` walks every note, finds the matching region, loads the audio, pitch-shifts it from `root_pitch` to the note pitch, applies a velocity gain + ADSR envelope, and mixes it into a numpy buffer at the note's start time.
5. The output is a float32 numpy array you can save as WAV with `io.save_wav`.

## Adding your own instrument samples

`pretty_audio` does not ship with instrument samples — you bring your own
`.wav`/`.mp3`/`.mpeg` files and map them to MIDI pitches with `SampleRegion`.

### 1. Where to find samples

A great free source is the **University of Iowa Musical Instrument Samples**:

https://theremin.music.uiowa.edu/mis.html

It contains public-domain, single-note recordings of orchestral and band
instruments (trumpet, flute, violin, guitar, etc.), often in multiple dynamic
layers (soft / medium / loud). Files are typically `.au` or `.aif`.

Other options:
- Record your own instrument (one file per note × dynamic layer)
- Free sample packs (search "free piano samples wav", etc.)
- SoundFonts (`.sf2`) — extract individual WAVs from them

### 2. Convert files to `.wav`

Iowa MIS files are often `.au` or `.aif`. `pretty_audio` loads `.wav`
natively (and `.mp3`/`.mpeg` via librosa), so convert first:

```bash
# Using ffmpeg (batch)
for f in samples/iowa/*.au; do ffmpeg -i "$f" "${f%.au}.wav"; done
```

Or with Python:

```python
from pathlib import Path
import soundfile as sf

for au in Path("samples/iowa").glob("*.au"):
    y, sr = sf.read(au)
    sf.write(au.with_suffix(".wav"), y, sr, subtype="PCM_16")
```

### 3. Name files for automatic region building

`build_regions_from_folder()` can auto-generate `SampleRegion` objects from
filenames. The expected convention is:

```
<instrument>.<dynamic>.<string>.<lowNote><highNote>.wav
```

Example (guitar samples):

```
Guitar.ff.sulA.A2B2.wav   # fortissimo, A string, A2–B2 (MIDI 45–47)
Guitar.mf.sulA.C3B3.wav   # mezzo-forte, A string, C3–B3 (MIDI 48–59)
Guitar.pp.sulB.B3.wav     # pianissimo, B string, B3 only (MIDI 59)
```

- **Dynamic layer** maps to velocity: `pp` (0–42), `mp` (43–63), `mf` (64–84),
  `f` (85–104), `ff` (105–127). You can customize this with `dynamic_map`.
- **Pitch range** (`A2B2`) sets `note_low`/`note_high`. Single-note files
  (`B3`) set both to the same pitch.
- **Root pitch** defaults to the lower note of the range.

### 4. Build regions and render

```python
from pretty_audio import PrettyAudio, Instrument, Note, build_regions_from_folder
from pretty_audio.render import synthesize
from pretty_audio.io import save_wav

# Auto-build regions from a folder of converted .wav files
regions = build_regions_from_folder("samples/trumpet")

trumpet = Instrument(name="Trumpet")
trumpet.regions = regions
trumpet.notes = [
    Note(start=0.0, end=1.0, pitch=60, velocity=100),  # C4, loud layer
    Note(start=1.0, end=2.0, pitch=64, velocity=50),   # E4, soft layer
]

pa = PrettyAudio(sample_rate=44100)
pa.add_instrument(trumpet)
audio = synthesize(pa, duration=3.0)
save_wav("trumpet_output.wav", audio, sample_rate=pa.sample_rate)
```

If your files use a different naming convention, pass a custom
`parse_filename` callback to `build_regions_from_folder()`.

### 5. Licensing

Iowa MIS samples are public domain, but most other sample libraries are
copyrighted. Only bundle samples you have rights to distribute, or point users
to download them separately.

## Roadmap / open questions

- **Stereo & pan:** currently mono. Add per-region stereo files and pan law.
- **Round-robin:** multiple samples per region to avoid the "machine-gun" effect on repeated notes.
- **Release samples / key noise:** trigger a separate release sample on note `end` for realism (piano key release, fret noise, breath).
- **Time-stretch:** match sample length to note duration (`librosa.effects.time_stretch`) instead of relying on ADSR alone.
- **Effects chain:** reverb, EQ, compression on the final mix.
- **Sample format:** `.wav` is native; `.mp3`/`.mpeg` works via librosa/audioread but introduces a small decode delay — fine for rendering, not for low-latency playback.
- **Sample licensing:** remember that realistic instrument samples are usually copyrighted; bundle only samples you have rights to, or point users to free sample packs.

## License

MIT
