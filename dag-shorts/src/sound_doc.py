"""Belgesel ses tasarımı: yavaş ambiyans pad + seyrek piyano + rüzgâr dokusu + yumuşak geçişler + seslendirme (ducking).
Tamamı kod ile sentezlenir (telifsiz). Çıktı: build/audio_doc.wav"""
import json, wave, subprocess
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
TL = json.load(open('build/timeline_doc.json'))
TOTAL = TL['total'] + 0.2
N = int(TOTAL * SR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(11)
scenes = TL['scenes']

def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def place(buf, sig, t, g=1.0):
    i = int(t * SR)
    if i < 0: sig = sig[-i:]; i = 0
    if i >= len(buf): return
    j = min(len(buf), i + len(sig)); buf[i:j] += sig[:j - i] * g
def midi(n): return 440 * 2 ** ((n - 69) / 12)

# --- akor dizisi (Re minör, yavaş): Dm - Bb - F - C / Dm - Gm - Bb - A
PROG = [[50, 57, 62, 65, 69], [46, 53, 62, 65, 70], [41, 53, 60, 65, 69], [48, 55, 60, 64, 67],
        [50, 57, 62, 65, 69], [43, 55, 62, 67, 70], [46, 53, 62, 65, 70], [45, 52, 61, 64, 69]]
CH = 4.8  # her akor süresi (sn)

# 1) pad: yumuşak, yavaş açılan, detune sinüs + üçgen katmanlar
pad = np.zeros(N)
for k in range(int(TOTAL / CH) + 2):
    t0 = k * CH; notes = PROG[k % len(PROG)]; n = int((CH + 2.5) * SR); tt = np.arange(n) / SR
    s = np.zeros(n)
    for i, note in enumerate(notes):
        for det in (-.07, .06):
            f = midi(note + det)
            s += np.sin(2 * np.pi * f * tt) * (.9 if i else 1.3)
            s += .25 * (2 * np.abs(2 * ((tt * f) % 1) - 1) - 1)
    e = np.minimum(1, tt / 1.8) * np.minimum(1, np.maximum(0, (CH + 2.5 - tt) / 2.5))
    place(pad, s * e, t0)
pad = lp(pad, 1400) * (1 + .15 * np.sin(2 * np.pi * .07 * t_all))

# 2) seyrek piyano benzeri notalar (pentatonik, akora uyumlu)
piano = np.zeros(N)
def pnote(f, d=3.5):
    n = int(d * SR); tt = np.arange(n) / SR; s = np.zeros(n)
    for h, a, dc in [(1, 1, 1.6), (2, .45, 2.4), (3, .2, 3.5), (4, .1, 5)]:
        s += a * np.sin(2 * np.pi * f * h * tt * (1 + .0004 * h)) * np.exp(-tt * dc)
    s *= np.minimum(1, tt / .004); return s
first_m = scenes[1]['start']
for k in range(int(TOTAL / (CH / 4))):
    tt0 = k * CH / 4
    if tt0 < 2.5 or tt0 > TOTAL - 3: continue
    if rng.random() < .45: continue
    notes = PROG[int(tt0 / CH) % len(PROG)]
    nt = notes[rng.integers(2, 5)] + 12 * rng.integers(0, 2)
    place(piano, pnote(midi(nt)), tt0 + rng.random() * .05, .5 + .3 * rng.random())
piano = lp(piano, 5000)
# basit yankı (çoklu gecikme)
rev = np.zeros(N)
for d, g in [(.113, .35), (.197, .28), (.311, .22), (.47, .16), (.71, .1)]:
    k = int(d * SR); rev[k:] += piano[:-k] * g
piano = piano + lp(rev, 3000)

# 3) derin drone
drone = np.sin(2 * np.pi * midi(38) * t_all) * .6 + np.sin(2 * np.pi * midi(26) * t_all) * .4
drone *= .5 + .5 * np.sin(2 * np.pi * .05 * t_all) ** 2

# 4) rüzgâr dokusu (yavaş değişen bant geçiren gürültü)
nz = rng.standard_normal(N)
wind = bp(nz, 250, 1100) * (.5 + .5 * np.sin(2 * np.pi * .09 * t_all + 1) ** 2) + hp(lp(nz, 3500), 1500) * .25 * (.5 + .5 * np.sin(2 * np.pi * .13 * t_all) ** 2)

# 5) geçişler: yumuşak rüzgâr swell'i + 1 numara ve başlık için derin "boom"
sfx = np.zeros(N)
def swell(d=1.6):
    n = int(d * SR); x = rng.standard_normal(n); out = np.zeros(n); seg = 24; L = n // seg
    for k in range(seg):
        c = 300 + 2200 * np.sin(np.pi * k / seg) ** 2; s = bp(x[k * L:k * L + L + 2000], c * .6, c * 1.5)
        out[k * L:k * L + len(s)] += s * np.hanning(len(s))
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2 / (np.abs(out).max() + 1e-9)
def boom(d=4.0):
    n = int(d * SR); tt = np.arange(n) / SR
    s = np.sin(2 * np.pi * np.cumsum(32 + 40 * np.exp(-tt * 6)) / SR) * np.exp(-tt * 1.1)
    s += lp(rng.standard_normal(n), 400) * np.exp(-tt * 2.5) * .3
    return s * np.minimum(1, tt / .02) / np.abs(s).max()
for i, s in enumerate(scenes):
    if i > 0: place(sfx, swell(), s['start'] - .9, .5)
    if s['kind'] == 'intro': place(sfx, boom(), 1.6, .7)
    if s['kind'] == 'mountain' and s['m']['rank'] == 1: place(sfx, boom(5), s['start'] + .5, .9)

def norm(x): return x / (np.abs(x).max() + 1e-9)
music = norm(pad) * .55 + norm(piano) * .38 + norm(drone) * .22
# genel zarf: girişte yavaş açılış, sonda sönüş
m01 = next(s for s in scenes if s['kind'] == 'mountain' and s['m']['rank'] == 1)['start']
env = np.interp(t_all, [0, 2.5, m01 - 1, m01 + .5, TOTAL - 4, TOTAL], [0, .8, .8, 1, .9, 0])
music *= env

# seslendirme + ducking
voice = np.zeros(N)
for s in scenes:
    w = wave.open(f"build/voice_doc/{s['key']}.wav"); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    place(voice, a, s['voice'])
venv = lp(np.abs(voice), 4, 1); venv /= venv.max() + 1e-9
duck = 1 - .5 * np.clip(venv * 3, 0, 1)
music *= duck

mixL = norm(music) * .42 + norm(wind) * .07 * env + norm(sfx) * .3 + norm(voice) * .95
# hafif stereo: rüzgâr ve pad için kanal farkı
mixR = mixL.copy(); d = int(.017 * SR)
amb = norm(music) * .42 + norm(wind) * .07 * env
mixR[d:] = mixL[d:] - amb[d:] * .5 + amb[:-d] * .5
st = np.stack([mixL, mixR], 1)
st = np.tanh(st * 1.05) / np.tanh(1.05)
pcm = (np.clip(st, -1, 1) * 32767).astype(np.int16)
with wave.open('build/audio_doc_raw.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', 'build/audio_doc_raw.wav', '-af', 'loudnorm=I=-15:TP=-1.0:LRA=11', '-ar', '44100', 'build/audio_doc.wav'], check=True)
print('belgesel sesi hazır', round(TOTAL, 2), 's')
