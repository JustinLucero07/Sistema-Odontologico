"""Música original para los anuncios (sin derechos de terceros).

  python3 musica.py anuncio   -> anuncio.wav (43 s, 120 BPM)
  python3 musica.py teaser    -> teaser.wav  (20 s, 120 BPM)

Síntesis con numpy: bombo, palmas, hi-hats, bajo, acordes, arpegio, subidas
(risers), golpes (impactos) y barridos (whoosh), con reverb por convolución.
"""
import sys, wave
import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
rng = np.random.default_rng(7)

def buf(sec): return np.zeros(int(sec * SR) + SR)

def add(dst, sig, t, g=1.0):
    i = int(t * SR); n = min(len(sig), len(dst) - i)
    if n > 0: dst[i:i + n] += sig[:n] * g

def env(n, a=0.005, d=0.2, s=0.0, r=0.1, hold=None):
    t = np.arange(n) / SR
    e = np.where(t < a, t / a, 1.0)
    dec = np.exp(-(t - a) / max(d, 1e-4)) * (1 - s) + s
    e = np.where(t >= a, dec, e)
    if hold is not None:
        rel = np.clip(1 - (t - hold) / r, 0, 1)
        e = e * np.where(t > hold, rel, 1)
    return e

def lowpass(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / fc) ** 4)
    return np.fft.irfft(X, len(x))

def highpass(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (fc / np.maximum(f, 1)) ** 4)
    return np.fft.irfft(X, len(x))

def reverb(x, sec=2.2, mix=0.25):
    n = int(sec * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir = lowpass(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
    return x * (1 - mix) + y * mix * 1.6

def nota(m): return 440 * 2 ** ((m - 69) / 12)

def kick(g=1.0):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 7.5)
    click = rng.standard_normal(n) * np.exp(-t * 300) * 0.25
    return np.tanh((s + click) * 1.6) * g

def clap():
    n = int(0.35 * SR); t = np.arange(n) / SR
    no = highpass(rng.standard_normal(n), 900)
    e = sum(np.exp(-np.clip(t - d, 0, None) * 60) * (t >= d) for d in (0, 0.011, 0.022)) + np.exp(-np.clip(t - 0.03, 0, None) * 14) * (t >= 0.03)
    return no * e * 0.35

def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR); t = np.arange(n) / SR
    return highpass(rng.standard_normal(n), 7000) * np.exp(-t * (14 if open_ else 70)) * 0.15

def saw(f, n):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 14) if f * k < 16000)

def pad(ms, sec):
    n = int(sec * SR)
    s = sum(saw(nota(m), n) * (0.5 if i else 0.7) for i, m in enumerate(ms))
    s = s + sum(saw(nota(m) * 1.006, n) for m in ms) * 0.5
    s = lowpass(s, 1800) * env(n, a=0.25, d=9, s=0.85, r=0.35, hold=sec - 0.35)
    return s * 0.045

def bass(m, sec):
    n = int(sec * SR); t = np.arange(n) / SR
    f = nota(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.15 * saw(f, n) * 0.3
    return np.tanh(s * 1.4) * env(n, a=0.004, d=0.35, s=0.55, r=0.05, hold=sec - 0.05) * 0.32

def pluck(m, sec=0.32):
    n = int(sec * SR)
    s = lowpass(saw(nota(m), n), 3500) * env(n, a=0.002, d=0.12)
    return s * 0.08

def riser(sec, top=9000):
    n = int(sec * SR); t = np.arange(n) / SR
    no = rng.standard_normal(n)
    out = np.zeros(n); seg = int(0.05 * SR)
    for i in range(0, n, seg):
        fc = 300 + (top - 300) * (i / n) ** 2
        out[i:i + seg] = highpass(lowpass(no[i:i + seg], fc), fc * 0.3)
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / sec) ** 2) / SR) * 0.15
    return (out * 0.5 + tone) * (t / sec) ** 2 * 0.35

def impacto(g=1.0):
    n = int(2.4 * SR); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(35 + 70 * np.exp(-t * 6)) / SR) * np.exp(-t * 2.2)
    no = lowpass(rng.standard_normal(n), 3000) * np.exp(-t * 3.5) * 0.5
    return np.tanh((sub + no) * 1.5) * 0.7 * g

def whoosh(sec=0.6, g=1.0):
    n = int(sec * SR); t = np.arange(n) / SR
    no = rng.standard_normal(n); out = np.zeros(n); seg = int(0.02 * SR)
    for i in range(0, n, seg):
        x = i / n; fc = 600 + 6000 * np.sin(np.pi * x)
        out[i:i + seg] = lowpass(no[i:i + seg], fc)
    return out * np.sin(np.pi * t / sec) ** 2 * 0.28 * g

def tick():
    n = int(0.03 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 200) * 0.12

def golpe():  # para cada palabra que cae en el gancho
    return kick(0.9) + lowpass(rng.standard_normal(int(0.45 * SR)), 1500) * np.exp(-np.arange(int(0.45 * SR)) / SR * 18) * 0.25

# La menor – Fa – Do – Sol: cálido y con impulso.
PROG = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [67, 72, 76]), (55, [67, 71, 74])]

def groove(mix, drums, music, a, b, kick_on=True, ligero=False):
    t = a; i = 0
    while t < b - 1e-6:
        bar = int(round((t - a) / (4 * BEAT)))
        root, ch = PROG[bar % 4]
        if (i % 4) == 0:
            add(music, pad(ch, min(4 * BEAT, b - t)), t)
            for k in range(8):
                if t + k * BEAT / 2 < b and not ligero:
                    add(music, bass(root - 12 if k % 2 == 0 else root, BEAT / 2 - 0.01), t + k * BEAT / 2)
            arp = [ch[0], ch[1], ch[2], ch[1] + 12, ch[2], ch[1], ch[0] + 12, ch[2]]
            for k, m in enumerate(arp):
                if t + k * BEAT / 2 < b: add(music, pluck(m + 12), t + k * BEAT / 2, 0.9 if ligero else 0.7)
        if kick_on: add(drums, kick(), t)
        if (i % 2) == 1 and not ligero: add(drums, clap(), t)
        add(drums, hat(), t + BEAT / 2)
        if not ligero: add(drums, hat(), t + BEAT / 4, 0.5); add(drums, hat(), t + 3 * BEAT / 4, 0.5)
        if (i % 8) == 7: add(drums, hat(True), t + BEAT / 2)
        t += BEAT; i += 1

def anuncio():
    D = 43.5; drums, music, fx = buf(D), buf(D), buf(D)
    # Gancho: palabras que caen + tic-tac de reloj, tensión.
    for tt in (0.2, 0.7, 1.0, 1.4): add(fx, golpe(), tt, 0.9)
    for k in range(10): add(fx, tick(), 2.0 + k * 0.3)
    add(music, lowpass(pad([45, 52, 57], 5.0), 600) * 2.0, 0.0)
    for tt in (3.0, 3.66, 4.33): add(fx, golpe(), tt, 0.7)
    add(fx, riser(2.2), 2.8)
    add(fx, impacto(), 5.0)
    groove(drums, drums, music, 5.0, 31.5)
    for k in range(8): add(fx, whoosh(0.55), 7.5 + 3.0 * k - 0.3, 0.9)
    groove(drums, drums, music, 31.5, 35.5, kick_on=False, ligero=True)
    add(fx, riser(2.0), 35.5)
    add(fx, whoosh(0.7), 35.2)
    add(fx, impacto(1.1), 37.5)
    groove(drums, drums, music, 37.5, 41.5)
    add(music, pad([57, 64, 69, 72], 2.0) * 1.3, 41.5)
    return drums, music, fx, D

def teaser():
    D = 20.5; drums, music, fx = buf(D), buf(D), buf(D)
    add(music, lowpass(pad([45, 52, 57], 2.5), 500) * 2.2, 0.0)
    add(fx, riser(1.8), 0.4)
    add(fx, impacto(0.8), 2.0)
    groove(drums, drums, music, 2.0, 12.0)
    for k in range(10): add(fx, whoosh(0.35, 0.6), 2.0 + k * 1.0 - 0.15)
    add(fx, riser(1.5), 10.5)
    add(fx, impacto(1.0), 12.0)
    add(music, lowpass(pad([45, 52, 57, 60], 4.0), 900) * 1.6, 12.0)
    for k in range(8): add(drums, kick(0.5), 12.0 + k * BEAT)
    add(fx, riser(1.2), 14.8)
    add(fx, impacto(1.2), 16.0)
    add(music, pad([57, 64, 69, 72], 4.0) * 1.4, 16.0)
    return drums, music, fx, D

def mezclar(drums, music, fx, D, nombre):
    music = reverb(music, 2.6, 0.3)
    fx = reverb(fx, 1.8, 0.18)
    drums = reverb(drums, 0.9, 0.08)
    # El bombo «empuja» a la música (sidechain) para que respire.
    kick_env = np.abs(lowpass(drums, 120))
    kick_env = np.convolve(kick_env, np.ones(2000) / 2000, mode='same')
    duck = 1 - np.clip(kick_env * 3.5, 0, 0.45)
    mix = drums * 0.9 + music * duck + fx
    n = int(D * SR); mix = mix[:n]
    fade = int(1.2 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix * 1.3) / np.tanh(1.3)
    mix /= np.max(np.abs(mix)) / 0.89
    l = mix; r = np.roll(mix, 9) * 0.98 + mix * 0.02
    st = (np.stack([l, r], 1) * 32767).astype(np.int16)
    with wave.open(nombre, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
    print(nombre, f'{D} s')

if __name__ == '__main__':
    q = sys.argv[1]
    mezclar(*(anuncio() if q == 'anuncio' else teaser()), f'{q}.wav')
