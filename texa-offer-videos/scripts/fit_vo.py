"""Trims silence from voice clips and (if needed) speeds them up to fit a frame budget.
Usage: python3 scripts/fit_vo.py <ffmpeg> <src_dir> <out_dir> <total_frames> <max_tempo> clip1 clip2 ...
Prints the frame count per clip for offers.ts."""
import subprocess, math, wave, sys, json
import numpy as np
FF, SRC, OUT, TOTAL, MAXT = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), float(sys.argv[5])
names = sys.argv[6:]; SR = 44100; GAP = 6; TAIL = 24
def load(n):
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", f"{SRC}/{n}.mp3", "-ac", "1", "-ar", str(SR), f"{SRC}/{n}.wav"], check=True)
    w = wave.open(f"{SRC}/{n}.wav"); return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
def trim(x):
    win = int(0.02 * SR); e = np.sqrt(np.convolve(x ** 2, np.ones(win) / win, "same")); idx = np.where(e > 0.012)[0]
    return x[max(0, idx[0] - int(0.03 * SR)): min(len(x), idx[-1] + int(0.10 * SR))]
clips = {n: trim(load(n)) for n in names}
total = sum(len(v) for v in clips.values()) / SR
tempo = min(MAXT, max(1.0, total / ((TOTAL - TAIL - GAP * len(names)) / 30)))
frames = {}
for n, x in clips.items():
    w = wave.open(f"{SRC}/{n}_t.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes()); w.close()
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", f"{SRC}/{n}_t.wav", "-af", f"atempo={tempo:.4f}", "-b:a", "160k", f"{OUT}/{n}.mp3"], check=True)
    frames[n] = math.ceil(len(x) / SR / tempo * 30) + GAP
frames[names[-1]] += TAIL
print(json.dumps({"speech_seconds": round(total, 2), "tempo": round(tempo, 3), "frames": frames, "total_frames": sum(frames.values())}))
