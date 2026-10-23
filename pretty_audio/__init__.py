"""pretty_audio — a pretty-midi-like library for realistic .wav/.mp3 samples.

Instead of symbolic MIDI notes driven through a synth, pretty_audio lets you
build performances from real recorded audio regions and render them to a
numpy audio buffer.
"""

from .core import (
    PrettyAudio,
    Instrument,
    SampleRegion,
    Note,
    build_regions_from_folder,
    note_name_to_midi,
)
from .render import synthesize

__version__ = "0.1.0"

__all__ = [
    "PrettyAudio",
    "Instrument",
    "SampleRegion",
    "Note",
    "build_regions_from_folder",
    "note_name_to_midi",
    "synthesize",
    "__version__",
]
