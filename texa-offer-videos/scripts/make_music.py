"""Synthesises a simple upbeat backing track (120 BPM, A major) as a WAV file.
Usage: python3 scripts/make_music.py <seconds> <out.wav>"""
import sys, wave
import numpy as np

SR = 44100
BEAT = 0.5  # 120 BPM
rng = np.random.default_rng(7)

def env(n, decay):
    return np.exp(-np.arange(n) / (decay * SR))

def note(freq, dur, decay, harm=(1, 0.5, 0.25, 0.12)):
    n = int(dur * SR); t = np.arange(n) / SR
    w = sum(a * np.sin(2 * np.pi * freq * (i + 1) * t) for i, a in enumerate(harm))
    att = np.minimum(1, np.arange(n) / (0.004 * SR))
    return w * env(n, decay) * att

def kick():
    n = int(0.3 * SR); t = np.arange(n) / SR
    f = 45 + 95 * np.exp(-t / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.11)

def noise(dur, decay, hp):
    n = int(dur * SR); x = rng.standard_normal(n)
    x = np.diff(x, prepend=0) if hp else x          # crude high-pass
    if hp > 1: x = np.diff(x, prepend=0)
    return x * env(n, decay)

def clap():
    c = noise(0.18, 0.045, 1)
    for d in (0.008, 0.017):                       # layered bursts
        k = int(d * SR); c[k:] += 0.6 * noise(0.18, 0.03, 1)[: len(c) - k]
    return c

def add(buf, x, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= buf.shape[0]: return
    x = x[: buf.shape[0] - i]
    buf[i:i + len(x), 0] += x * gain * (1 - max(0, pan))
    buf[i:i + len(x), 1] += x * gain * (1 + min(0, pan))

def hz(semitones_from_a2): return 110.0 * 2 ** (semitones_from_a2 / 12)

# A – E – F#m – D, one bar each; chord tones as semitones above A2
CHORDS = [(0, [12, 16, 19, 24]), (7, [11, 16, 19, 23]), (9, [9, 13, 16, 21]), (5, [14, 17, 21, 26])]
ARP = [0, 2, 1, 3, 2, 1, 3, 2, 0, 2, 1, 3, 2, 3, 1, 2]

def build(seconds):
    n = int(seconds * SR); buf = np.zeros((n, 2)); duck = np.ones(n)
    K, C, H = kick(), clap(), noise(0.05, 0.012, 2)
    bars = int(seconds / (4 * BEAT)) + 1
    for bar in range(bars):
        t0 = bar * 4 * BEAT
        root, tones = CHORDS[bar % 4]
        intro = bar < 2
        fill = (bar % 8 == 7)                      # breathing bar before each new phrase
        for b in range(4):
            tb = t0 + b * BEAT
            if not intro and not (fill and b >= 2):
                add(buf, K, tb, 0.95)
                i = int(tb * SR); m = min(n - i, int(0.22 * SR))
                if m > 0: duck[i:i + m] = np.minimum(duck[i:i + m], 0.45 + 0.55 * np.linspace(0, 1, m))
            if not intro and b in (1, 3): add(buf, C, tb, 0.20)
            add(buf, H, tb + BEAT / 2, 0.10 if intro else 0.14, pan=0.3)
            if not intro: add(buf, H, tb + BEAT / 4, 0.05, pan=-0.3)
        if fill:                                   # snare-ish roll into the next phrase
            for k in range(8): add(buf, C, t0 + 3 * BEAT + k * BEAT / 8, 0.06 + 0.02 * k)
        tonal = np.zeros((int(4 * BEAT * SR) + SR, 2))
        if not intro:
            for e in range(8):                     # bass on 8ths, octave jump on the off-beat
                f = hz(root - 12 + (12 if e % 2 else 0))
                add(tonal, note(f, 0.24, 0.12, (1, 0.6, 0.3, 0.15, 0.08)), e * BEAT / 2, 0.32)
        for s, idx in enumerate(ARP):              # plucked 16ths
            f = hz(tones[idx])
            add(tonal, note(f, 0.3, 0.09), s * BEAT / 4, 0.16, pan=0.5 if s % 2 else -0.5)
        for st in tones[:3]:                       # soft pad
            p = note(hz(st), 4 * BEAT, 3.0, (1, 0.2))
            p *= np.minimum(1, np.arange(len(p)) / (0.3 * SR))
            add(tonal, p, 0, 0.035)
        i = int(t0 * SR); m = min(n - i, tonal.shape[0])
        if m > 0: buf[i:i + m] += tonal[:m] * duck[i:i + m, None]
    d = int(0.375 * SR)                            # dotted-8th echo for width
    buf[d:, 0] += 0.22 * buf[:-d, 1]; buf[d:, 1] += 0.22 * buf[:-d, 0]
    fade = int(2.5 * SR); buf[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    buf = np.tanh(buf * 1.4)
    return buf / np.abs(buf).max() * 0.89

if __name__ == "__main__":
    out = build(float(sys.argv[1]))
    with wave.open(sys.argv[2], "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out * 32767).astype("<i2").tobytes())
