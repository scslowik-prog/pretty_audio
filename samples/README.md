# Audio Samples

This directory contains instrument samples used by `pretty_audio`.

- `samples/piano_c3_soft.wav` / `samples/piano_c3_loud.wav` — small synthetic
  test samples used by `example.py`. These are tracked in Git.
- `samples/guitar/` — converted 2496 stereo guitar samples. **Not tracked in
  Git** (too large). See `samples/guitar/README.md` for details.

You can point `pretty_audio` at any folder of `.wav`/`.mp3` files using
`build_regions_from_folder()`:

```python
from pretty_audio import build_regions_from_folder

regions = build_regions_from_folder("path/to/your/samples")
```
