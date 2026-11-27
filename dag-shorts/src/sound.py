"""Ses tasarımı: sentezlenmiş epik müzik + geçiş whoosh'ları + darbe/tik/ding efektleri + seslendirme (ducking ile).
Tamamı kod ile üretilir, telifsizdir. Çıktı: build/audio_mix.wav"""
import json, wave, subprocess
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
TL = json.load(open('build/timeline.json'))
TOTAL = TL['total'] + 0.3
N = int(TOTAL * SR)
rng = np.random.default_rng(7)
t_all = np.arange(N) / SR

def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def env_ad(n, a, d):
    e = np.ones(n); na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (d * SR)); return e
def place(buf, sig, t, g=1.0):
    i = int(t * SR)
    if i < 0: sig = sig[-i:]; i = 0
    if i >= len(buf): return
    j = min(len(buf), i + len(sig)); buf[i:j] += sig[:j - i] * g
def midi(n): return 440 * 2 ** ((n - 69) / 12)

# ---------------- efektler ----------------
def whoosh(dur=.55, up=True):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n)
    seg = 32; L = n // seg
    for k in range(seg):  # süpüren bant geçiren gürültü
        fr = k / seg if up else 1 - k / seg
        c = 300 + 5200 * fr ** 2
        s = bp(x[k * L:(k + 1) * L + 2000][:L + 2000], c * .6, min(c * 1.6, 18000))
        out[k * L:k * L + len(s)] += s * np.hanning(len(s))
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return out * e / (np.abs(out).max() + 1e-9)

def impact(big=False):
    d = 2.2 if big else 1.2; n = int(d * SR); tt = np.arange(n) / SR
    f = 30 + (110 if big else 80) * np.exp(-tt * 14)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * (1.6 if big else 3.2))
    nz = lp(rng.standard_normal(n), 2500) * np.exp(-tt * 18) * .6
    crack = hp(rng.standard_normal(n), 3000) * np.exp(-tt * 60) * .35
    s = sub + nz + crack
    if big:  # reverb kuyruğu
        tail = lp(rng.standard_normal(n), 1800) * np.exp(-tt * 2.2) * .15; s += tail
    return s / np.abs(s).max()

def tick():
    n = int(.03 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2400 * tt) * .6 + hp(rng.standard_normal(n), 4000) * .5) * np.exp(-tt * 260)

def ding():
    n = int(1.4 * SR); tt = np.arange(n) / SR; s = np.zeros(n)
    for f, a, dcy in [(1318.5, 1, 3.5), (1975.5, .5, 5), (2637, .3, 7), (3951, .15, 9)]: s += a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * dcy)
    return s * env_ad(n, .002, 10) / 2

def riser(dur):
    n = int(dur * SR); tt = np.arange(n) / SR; p = tt / dur
    nz = rng.standard_normal(n); out = np.zeros(n); seg = 40; L = n // seg
    for k in range(seg):
        c = 400 + 7000 * (k / seg) ** 2; s = bp(nz[k * L:k * L + L + 1500], c * .7, min(c * 1.4, 18000))
        out[k * L:k * L + len(s)] += s * np.hanning(len(s))
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * p ** 2) / SR) * .25
    s = (out / (np.abs(out).max() + 1e-9) + tone) * p ** 2
    return s

def pop():
    n = int(.25 * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(500 + 900 * np.exp(-tt * 30)) / SR) * np.exp(-tt * 22)

sfx = np.zeros(N)
scenes = TL['scenes']
for i, s in enumerate(scenes):
    st = s['start']
    if i > 0: place(sfx, whoosh(.6), st - .3, .55)
    if s['kind'] == 'intro':
        place(sfx, riser(1.0), 0.0, .35)
        place(sfx, impact(), .15 + 2 * .32 + .12, .8)          # "10" yere iniyor
        place(sfx, pop(), .15 + 4 * .32 + .1, .35)
    elif s['kind'] == 'mountain':
        big = s['m']['rank'] == 1
        place(sfx, impact(big), st + .2, 1.0 if big else .75)
        K = 18
        for k in range(1, K + 1):                              # sayaç tikleri (easeOut ile senkron)
            x = 1 - (1 - k / K) ** (1 / 3); place(sfx, tick(), st + .65 + 1.2 * x, .22)
        place(sfx, ding(), st + 1.85, .32)
        place(sfx, pop(), st + 1.95, .18)                      # bilgi rozeti
        if s['m']['rank'] == 2: place(sfx, riser(2.2), st + s['dur'] - 2.2, .55)  # 1 numara öncesi gerilim
    else:
        for k in range(10): place(sfx, tick() * 1.5, st + .3 + (9 - k) * .09, .2)
        place(sfx, impact(), st + 1.95, .5); place(sfx, ding(), st + 2.0, .3)

# ---------------- müzik (100 BPM, Re minör) ----------------
BPM = 100; beat = 60 / BPM; bar = beat * 4
music = np.zeros(N)
m01 = next(s for s in scenes if s['kind'] == 'mountain' and s['m']['rank'] == 1)['start']
outro = scenes[-1]['start']
first_m = scenes[1]['start']
prog = [(50, [62, 65, 69]), (46, [62, 65, 70]), (53, [60, 65, 69]), (48, [60, 64, 67])]  # Dm Bb F C
# pad: detune saw akorlar
pad = np.zeros(N)
for b in range(int(TOTAL / bar) + 2):
    t0 = b * bar; root, ch = prog[(b // 1) % 4]; n = int(bar * SR) + int(.5 * SR); tt = np.arange(n) / SR
    s = np.zeros(n)
    for note in ch + [ch[0] + 12]:
        for det in (-.12, 0, .11):
            f = midi(note + det); s += 2 * ((tt * f) % 1) - 1
    e = np.minimum(1, tt / .35) * np.minimum(1, np.maximum(0, (bar + .5 - tt) / .5))
    place(pad, s * e / 12, t0)
    # bas
    sub = np.sin(2 * np.pi * midi(root - 12) * tt) * .8 + (2 * ((tt * midi(root - 12)) % 1) - 1) * .2
    place(music, lp(sub, 400) * e * .5, t0)
pad = lp(pad, 1800)
music += pad * .55
# ostinato arpej (16'lık), 1. sahneden sonra
arp = np.zeros(N)
for k in range(int(TOTAL / (beat / 2))):
    t0 = k * beat / 2
    if t0 < first_m - .1 or t0 > outro + 2.5: continue
    b = int(t0 / bar); root, ch = prog[b % 4]; note = (ch + [ch[0] + 12])[k % 4] + 12
    n = int(.22 * SR); tt = np.arange(n) / SR
    arp_s = (2 * ((tt * midi(note)) % 1) - 1) * np.exp(-tt * 14)
    place(arp, arp_s, t0, .18)
music += lp(arp, 3500)
# davullar
def kick():
    n = int(.4 * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(45 + 120 * np.exp(-tt * 30)) / SR) * np.exp(-tt * 7)
def clap():
    n = int(.3 * SR); tt = np.arange(n) / SR
    return bp(rng.standard_normal(n), 900, 5000) * np.exp(-tt * 18)
def hat():
    n = int(.06 * SR); tt = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-tt * 70)
drums = np.zeros(N)
KS, CS, HS = kick(), clap(), hat()
m05 = next(s for s in scenes if s['kind'] == 'mountain' and s['m']['rank'] == 5)['start']
for k in range(int(TOTAL / beat) + 1):
    t0 = k * beat
    if t0 < first_m - .05 or t0 > outro + 2.0: continue
    if m01 - 2.3 < t0 < m01 - .05: continue                      # 1 numara öncesi drop: davul sus
    place(drums, KS, t0, .9)
    if t0 >= m05 and k % 2 == 1: place(drums, CS, t0, .35)
    place(drums, HS, t0 + beat / 2, .18);
    if t0 >= m01: place(drums, HS, t0, .12)
music += drums
# genel müzik zarfı: intro'da yumuşak, 1 numarada tam, kapanışta söner
g = np.interp(t_all, [0, first_m, m01 - 2.3, m01 - .1, m01, outro + 2, TOTAL],
                     [.55, .8, .8, .45, 1.0, .9, 0])
music *= g

# ---------------- seslendirme + ducking ----------------
voice = np.zeros(N)
keys = {s['key']: s['voice'] for s in scenes}
for key, vt in keys.items():
    w = wave.open(f'build/voice/{key}.wav'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    place(voice, a, vt)
venv = lp(np.abs(voice), 6, 1); venv = venv / (venv.max() + 1e-9)
duck = 1 - .6 * np.clip(venv * 3, 0, 1)
music *= duck

def norm(x, peak): return x / (np.abs(x).max() + 1e-9) * peak
mix = norm(music, .5) + norm(sfx, .55) + norm(voice, .95)
# hafif oda yankısı (sadece müzik+efekt için basit çoklu gecikme)
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
stereo = np.stack([mix, mix], 1)
# hafif stereo genişlik: pad için küçük gecikme
d = int(.012 * SR); stereo[d:, 1] = mix[d:] * .7 + mix[:-d] * .3
pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
with wave.open('build/audio_raw.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', 'build/audio_raw.wav', '-af', 'loudnorm=I=-14:TP=-1.0:LRA=9', '-ar', '44100', 'build/audio_mix.wav'], check=True)
print('ses hazır', round(TOTAL, 2), 's')
