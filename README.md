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
