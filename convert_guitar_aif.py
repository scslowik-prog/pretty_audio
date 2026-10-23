"""Convert Iowa/Guitar .aif samples to .wav for use with pretty_audio.

Source: C:/Users/qdgac/Downloads/Guitar.stereo.2496/2496stereo
Destination: F:/OpenCode/pretty_audio/samples/guitar/
"""
from pathlib import Path
import soundfile as sf

src_dir = Path(r"C:\Users\qdgac\Downloads\Guitar.stereo.2496\2496stereo")
dst_dir = Path(r"F:\OpenCode\pretty_audio\samples\guitar")
dst_dir.mkdir(parents=True, exist_ok=True)

aif_files = sorted(src_dir.glob("*.aif"))
print(f"Found {len(aif_files)} .aif files")
print(f"Destination: {dst_dir}\n")

converted = 0
failed = []
for aif_path in aif_files:
    wav_path = dst_dir / (aif_path.stem + ".wav")
    if wav_path.exists():
        print(f"skip: {wav_path.name}")
        continue
    try:
        y, sr = sf.read(aif_path)
        sf.write(wav_path, y, sr, subtype="PCM_16")
        converted += 1
        print(f"[{converted}/{len(aif_files)}] {aif_path.name} -> {wav_path.name}  ({sr} Hz, {y.shape})")
    except Exception as e:
        failed.append((aif_path.name, str(e)))
        print(f"FAILED: {aif_path.name}: {e}")

print(f"\nDone. {converted} converted, {len(failed)} failed.")
print(f"WAV files in: {dst_dir}")
if failed:
    print("\nFailures:")
    for name, err in failed:
        print(f"  {name}: {err}")
