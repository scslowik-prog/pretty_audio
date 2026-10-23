"""Data model for pretty_audio.

Mirrors the structure of pretty-midi (PrettyMIDI -> Instrument -> Note) but
operates on real audio sample regions rather than symbolic MIDI events.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional


@dataclass
class Note:
    """A single note event, in seconds and MIDI pitch.

    Attributes
    ----------
    start : float
        Note onset time in seconds.
    end : float
        Note release/end time in seconds.
    pitch : int
        MIDI pitch (0-127). 60 = middle C.
    velocity : int
        Note velocity (0-127), mapped to sample-layer + gain.
    instrument : int
        Index into ``PrettyAudio.instruments`` that owns this note.
    """

    start: float
    end: float
    pitch: int
    velocity: int
    instrument: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.pitch <= 127:
            raise ValueError(f"pitch must be 0-127, got {self.pitch}")
        if not 0 <= self.velocity <= 127:
            raise ValueError(f"velocity must be 0-127, got {self.velocity}")
        if self.end < self.start:
            raise ValueError("note end must be >= start")


@dataclass
class SampleRegion:
    """One audio file mapped to a key/velocity range.

    When rendering a note, the engine picks the region whose
    ``note_low <= pitch <= note_high`` and
    ``velocity_low <= velocity <= velocity_high``.  If several match, the
    first one is used (consider adding round-robin later).

    Attributes
    ----------
    sample_path : str
        Path to a .wav, .mp3, or .mpeg file.
    note_low, note_high : int
        Inclusive MIDI pitch range this sample covers.
    velocity_low, velocity_high : int
        Inclusive velocity range this sample covers.
    root_pitch : int
        The MIDI pitch the sample was recorded at.  The render engine
        pitch-shifts from ``root_pitch`` to the requested note ``pitch``.
    gain : float
        Extra linear gain applied to this region (1.0 = unity).
    pan : float
        Stereo pan (-1 = left, 0 = center, 1 = right).  Reserved for future
        stereo rendering; currently applied as a simple mono gain balance.
    """

    sample_path: str
    note_low: int = 0
    note_high: int = 127
    velocity_low: int = 0
    velocity_high: int = 127
    root_pitch: int = 60
    gain: float = 1.0
    pan: float = 0.0

    def __post_init__(self) -> None:
        for name, val in (("note_low", self.note_low), ("note_high", self.note_high)):
            if not 0 <= val <= 127:
                raise ValueError(f"{name} must be 0-127, got {val}")
        for name, val in (("velocity_low", self.velocity_low),
                          ("velocity_high", self.velocity_high)):
            if not 0 <= val <= 127:
                raise ValueError(f"{name} must be 0-127, got {val}")
        if not 0 <= self.root_pitch <= 127:
            raise ValueError(f"root_pitch must be 0-127, got {self.root_pitch}")
        if self.note_high < self.note_low:
            raise ValueError("note_high must be >= note_low")
        if self.velocity_high < self.velocity_low:
            raise ValueError("velocity_high must be >= velocity_low")

    def contains(self, pitch: int, velocity: int) -> bool:
        return (self.note_low <= pitch <= self.note_high
                and self.velocity_low <= velocity <= self.velocity_high)


@dataclass
class Instrument:
    """One instrument: a name, a set of sample regions, and its note events."""

    name: str
    program: int = 0
    is_drum: bool = False
    regions: List[SampleRegion] = field(default_factory=list)
    notes: List[Note] = field(default_factory=list)

    def add_region(self, region: SampleRegion) -> None:
        self.regions.append(region)

    def add_note(self, note: Note) -> None:
        self.notes.append(note)

    def find_region(self, pitch: int, velocity: int) -> SampleRegion | None:
        for region in self.regions:
            if region.contains(pitch, velocity):
                return region
        return None


@dataclass
class PrettyAudio:
    """Top-level container, analogous to pretty-midi's ``PrettyMIDI``.

    Attributes
    ----------
    sample_rate : int
        Rendering sample rate in Hz.
    tempo : float
        Beats per minute.
    time_signature : tuple[int, int]
        (numerator, denominator).
    key_signature : int
        Number of sharps (positive) / flats (negative).
    instruments : list[Instrument]
        The instruments in this performance.
    """

    sample_rate: int = 44100
    tempo: float = 120.0
    time_signature: tuple[int, int] = (4, 4)
    key_signature: int = 0
    instruments: List[Instrument] = field(default_factory=list)

    def add_instrument(self, instrument: Instrument) -> None:
        self.instruments.append(instrument)

    def all_notes(self) -> List[Note]:
        """Return every note across all instruments, sorted by start time."""
        notes = [n for inst in self.instruments for n in inst.notes]
        return sorted(notes, key=lambda n: (n.start, n.pitch))

    def get_end_time(self) -> float:
        if not self.all_notes():
            return 0.0
        return max(n.end for n in self.all_notes())


# --------------------------------------------------------------------------- #
# Note-name helpers
# --------------------------------------------------------------------------- #
_NOTE_TO_SEMITONE = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}

_NOTE_RE = re.compile(r"([A-G]#?|[A-G]b?)(\d)")


def note_name_to_midi(name: str) -> int:
    """Convert a note name like ``'C4'`` or ``'A#3'`` to a MIDI pitch number.

    Parameters
    ----------
    name : str
        Note name with optional sharp/flat and octave (e.g. ``'C4'``,
        ``'F#3'``, ``'Bb5'``).

    Returns
    -------
    int
        MIDI pitch number (0-127).  Middle C (C4) is 60.
    """
    m = _NOTE_RE.fullmatch(name.strip())
    if not m:
        raise ValueError(f"Cannot parse note name: {name!r}")
    letter, octave = m.group(1), int(m.group(2))
    return _NOTE_TO_SEMITONE[letter] + (octave + 1) * 12


# --------------------------------------------------------------------------- #
# Default filename parser for guitar-style sample sets
# --------------------------------------------------------------------------- #
def _default_parse_filename(stem: str) -> dict:
    """Parse a filename like ``'Guitar.ff.sulA.A2B2'`` into region fields.

    Expected convention (4+ dot-separated parts)::

        <instrument>.<dynamic>.<string>.<lowNote><highNote>

    Example
    -------
    ``Guitar.ff.sulA.A2B2`` -> dynamic=``ff``, low_midi=45 (A2), high_midi=50 (B2)
    """
    parts = stem.split(".")
    if len(parts) < 4:
        raise ValueError(
            f"Cannot parse filename '{stem}': expected "
            "<instrument>.<dynamic>.<string>.<lowNote><highNote>"
        )
    dynamic = parts[1]
    pitch_part = parts[3]
    notes = _NOTE_RE.findall(pitch_part)
    if not notes:
        raise ValueError(
            f"Cannot find any note name in pitch range '{pitch_part}' "
            f"(from filename '{stem}')"
        )
    low_note, low_oct = notes[0]
    low_midi = note_name_to_midi(f"{low_note}{low_oct}")
    if len(notes) >= 2:
        high_note, high_oct = notes[1]
        high_midi = note_name_to_midi(f"{high_note}{high_oct}")
    else:
        # Single-note file: low and high are the same
        high_midi = low_midi
    return {
        "dynamic": dynamic.lower(),
        "low_midi": low_midi,
        "high_midi": high_midi,
    }


# --------------------------------------------------------------------------- #
# Convenience builder: create SampleRegion objects from a folder of samples
# --------------------------------------------------------------------------- #
def build_regions_from_folder(
    folder: str | Path,
    *,
    pattern: str = "*.wav",
    recursive: bool = False,
    dynamic_map: Optional[dict[str, tuple[int, int]]] = None,
    gain: float = 1.0,
    root_pitch: Optional[int] = None,
    parse_filename: Optional[Callable[[str], dict]] = None,
) -> List[SampleRegion]:
    """Build ``SampleRegion`` objects from audio files in a folder.

    This is a convenience helper for sample sets whose filenames encode the
    pitch range and velocity/dynamic layer.  By default it understands the
    guitar-sample convention used by the University of Iowa / 2496 guitar
    samples (``<instrument>.<dynamic>.<string>.<lowNote><highNote>.wav``,
    e.g. ``Guitar.ff.sulA.A2B2.wav``).

    Parameters
    ----------
    folder : str | Path
        Directory containing the sample files.
    pattern : str
        Glob pattern for matching files (default ``"*.wav"``).
    recursive : bool
        Whether to search subdirectories recursively.
    dynamic_map : dict[str, tuple[int, int]], optional
        Mapping from dynamic name (lowercase) to ``(velocity_low, velocity_high)``.
        Default: ``{"pp": (0, 42), "mf": (43, 84), "ff": (85, 127)}``.
    gain : float
        Linear gain applied to every region (1.0 = unity).
    root_pitch : int, optional
        Force all regions to use this ``root_pitch``.  If ``None``, the lower
        note of the parsed pitch range is used as the root pitch.
    parse_filename : callable, optional
        Custom parser ``stem -> dict`` returning keys
        ``low_midi``, ``high_midi``, ``dynamic`` (and optionally ``root_pitch``).
        Overrides the default guitar-style parser.

    Returns
    -------
    list[SampleRegion]
        One region per matching audio file.

    Example
    -------
    >>> from pretty_audio.core import build_regions_from_folder
    >>> regions = build_regions_from_folder("samples/guitar")
    >>> # regions[0] might be SampleRegion("samples/guitar/Guitar.ff.sulA.A2B2.wav",
    >>> #   note_low=45, note_high=50, velocity_low=85, velocity_high=127, root_pitch=45)
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")

    if dynamic_map is None:
        dynamic_map = {
            "pp": (0, 42),
            "mp": (43, 63),
            "mf": (64, 84),
            "f": (85, 104),
            "ff": (105, 127),
        }

    parser = parse_filename or _default_parse_filename

    globber = folder.rglob if recursive else folder.glob
    regions: List[SampleRegion] = []

    for path in sorted(globber(pattern)):
        if not path.is_file():
            continue
        try:
            info = parser(path.stem)
        except Exception as exc:
            raise ValueError(
                f"Failed to parse '{path.name}'.  Provide a custom "
                f"parse_filename callback for this naming convention."
            ) from exc

        dynamic = info.get("dynamic", "mf")
        low_midi = info["low_midi"]
        high_midi = info["high_midi"]
        region_root = info.get("root_pitch", root_pitch or low_midi)

        vel_low, vel_high = dynamic_map.get(dynamic, (0, 127))

        regions.append(
            SampleRegion(
                sample_path=str(path),
                note_low=low_midi,
                note_high=high_midi,
                velocity_low=vel_low,
                velocity_high=vel_high,
                root_pitch=region_root,
                gain=gain,
            )
        )

    if not regions:
        raise FileNotFoundError(
            f"No files matching '{pattern}' found in {folder}"
        )

    return regions

