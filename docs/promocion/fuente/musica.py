"""Música original para los anuncios (sin derechos de terceros).

  python3 musica.py anuncio   -> anuncio.wav (40 s)
  python3 musica.py teaser    -> teaser.wav  (20 s)

Estilo house pop de redes: 120 BPM, bombo en negras con «bombeo»
(sidechain), bajo a contratiempo, palmas, acordes Do–Sol–Lam–Fa y un
gancho melódico pegajoso en ritmo de tresillo. Gancho seco al inicio,
caída (drop) con el logo, pausa con subida antes del cierre y segundo drop.
"""
import sys, wave
import numpy as np

SR = 44100
BPM = 120
B = 60 / BPM          # una negra
S = B / 4             # una semicorchea
rng = np.random.default_rng(11)

def buf(sec): return np.zeros(int(sec * SR) + SR)
def add(dst, sig, t, g=1.0):
    i = int(round(t * SR)); n = min(len(sig), len(dst) - i)
    if n > 0 and i >= 0: dst[i:i + n] += sig[:n] * g

def lowpass(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 4), len(x))
def highpass(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (fc / np.maximum(f, 1)) ** 4), len(x))
def reverb(x, sec=1.8, mix=0.2):
    n = int(sec * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.6)
    ir = lowpass(ir, 6000); ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
    return x * (1 - mix) + y * mix * 1.5

def hz(m): return 440 * 2 ** ((m - 69) / 12)
def env(n, a=0.003, d=0.2, s=0.0, hold=None, r=0.05):
    t = np.arange(n) / SR
    e = np.minimum(t / a, 1.0) * (np.exp(-np.maximum(t - a, 0) / d) * (1 - s) + s)
    if hold is not None: e *= np.clip(1 - (t - hold) / r, 0, 1)
    return e
def saw(f, n, det=0.0):
    t = np.arange(n) / SR
    ph = (f * (1 + det) * t + rng.random()) % 1.0
    return 2 * ph - 1

# ---------- instrumentos ----------
def kick(g=1.0):
    n = int(0.42 * SR); t = np.arange(n) / SR
    f = 50 + 140 * np.exp(-t * 38)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    click = highpass(rng.standard_normal(n), 3000) * np.exp(-t * 400) * 0.3
    return np.tanh((s + click) * 2.2) * 0.95 * g
def clap(g=1.0):
    n = int(0.3 * SR); t = np.arange(n) / SR
    no = lowpass(highpass(rng.standard_normal(n), 1000), 9000)
    e = sum(np.exp(-np.clip(t - d, 0, None) * 70) * (t >= d) for d in (0, 0.009, 0.018)) + 0.7 * np.exp(-np.clip(t - 0.027, 0, None) * 16) * (t >= 0.027)
    return no * e * 0.42 * g
def hat(abierto=False, g=1.0):
    n = int((0.22 if abierto else 0.05) * SR); t = np.arange(n) / SR
    return highpass(rng.standard_normal(n), 8000) * np.exp(-t * (16 if abierto else 85)) * 0.13 * g
def shaker(g=1.0):
    n = int(0.07 * SR); t = np.arange(n) / SR
    return highpass(rng.standard_normal(n), 6000) * np.sin(np.pi * t / 0.07) ** 2 * 0.05 * g
def bajo(m, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) + 0.25 * lowpass(saw(f, n), 900)
    return np.tanh(s * 1.6) * env(n, 0.004, 0.18, 0.4, hold=dur - 0.03, r=0.03) * 0.34
def acorde(ms, dur, brillo=2600, g=1.0):
    n = int(dur * SR)
    s = sum(saw(hz(m), n, d) for m in ms for d in (-0.006, 0.0, 0.007))
    return lowpass(s, brillo) * env(n, 0.005, 0.16, 0.25, hold=dur - 0.04, r=0.04) * 0.035 * g
def colchon(ms, dur, brillo=1500, g=1.0):
    n = int(dur * SR)
    s = sum(saw(hz(m), n, d) for m in ms for d in (-0.008, 0.008))
    return lowpass(s, brillo) * env(n, 0.3, 30, 1.0, hold=dur - 0.4, r=0.4) * 0.03 * g
def pluck(m, dur=0.28, g=1.0):
    n = int(dur * SR)
    s = sum(saw(hz(m), n, d) for d in (-0.005, 0.0, 0.006)) + 0.6 * np.sin(2 * np.pi * hz(m + 12) * np.arange(n) / SR)
    return lowpass(s, 4200) * env(n, 0.002, 0.11) * 0.11 * g
def campana(m, dur=0.9, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t + 1.8 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t * 6))
    return s * np.exp(-t * 4) * 0.12 * g
def subida(dur, top=10000):
    n = int(dur * SR); t = np.arange(n) / SR
    no = rng.standard_normal(n); out = np.zeros(n); seg = int(0.04 * SR)
    for i in range(0, n, seg):
        fc = 400 + (top - 400) * (i / n) ** 2
        out[i:i + seg] = highpass(lowpass(no[i:i + seg], fc), fc * 0.35)
    return out * (t / dur) ** 2 * 0.3
def redoble(dur):  # caja que se acelera hacia el drop
    out = np.zeros(int(dur * SR) + SR); t = 0.0; k = 0
    while t < dur:
        paso = B / 2 if t < dur * 0.5 else (B / 4 if t < dur * 0.8 else B / 8)
        add(out, clap(0.35 + 0.65 * t / dur), t); t += paso; k += 1
    return out
def impacto(g=1.0):
    n = int(2.0 * SR); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(32 + 80 * np.exp(-t * 7)) / SR) * np.exp(-t * 2.5)
    no = lowpass(rng.standard_normal(n), 2500) * np.exp(-t * 4) * 0.45
    return np.tanh((sub + no) * 1.6) * 0.65 * g
def golpe(g=1.0):  # para cada palabra del gancho
    k = kick(0.9 * g); c = clap(0.6 * g); k[:len(c)] += c
    return k
def barrido(dur=0.4, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    no = rng.standard_normal(n); out = np.zeros(n); seg = int(0.02 * SR)
    for i in range(0, n, seg):
        out[i:i + seg] = lowpass(no[i:i + seg], 800 + 7000 * np.sin(np.pi * i / n))
    return out * np.sin(np.pi * t / dur) ** 2 * 0.2 * g

# Do – Sol – Lam – Fa (I–V–vi–IV): brillante y pegajoso.
PROG = [(48, [60, 64, 67]), (43, [59, 62, 67]), (45, [60, 64, 69]), (41, [60, 65, 69])]
# Gancho melódico: posiciones en semicorcheas (ritmo de tresillo) y notas por compás.
RITMO = [0, 3, 6, 8, 10, 12, 14]
MELODIA = [
    [76, 79, 84, 79, 76, 74, 72],
    [74, 79, 83, 79, 74, 72, 71],
    [72, 76, 81, 76, 72, 71, 69],
    [69, 72, 77, 76, 74, 72, 67],
]

def seccion(pist, a, b, bombo=True, palmas=True, bajo_on=True, melodia=True, acordes=True, filtro=None):
    drums, music = pist
    t = a; compas = 0
    while t < b - 1e-6:
        raiz, ch = PROG[compas % 4]
        for k in range(4):
            tb = t + k * B
            if tb >= b: break
            if bombo: add(drums, kick(), tb)
            if palmas and k % 2 == 1: add(drums, clap(), tb)
            add(drums, hat(True, 0.9 if bombo else 0.5), tb + B / 2)
            for q in (1, 3): add(drums, shaker(), tb + q * S)
            if bajo_on:
                add(music, bajo(raiz, B / 2 - 0.02), tb + B / 2)
                if k == 3: add(music, bajo(raiz + 12, S), tb + 3 * S)
        if acordes:
            for q in (2, 5, 10, 13):  # acordes cortos sincopados
                if t + q * S < b: add(music, acorde(ch, S * 1.6, 2400 if filtro is None else filtro), t + q * S)
        if melodia:
            for pos, m in zip(RITMO, MELODIA[compas % 4]):
                if t + pos * S < b: add(music, pluck(m), t + pos * S)
        t += 4 * B; compas += 1

def anuncio():
    D = 40.6; drums, music, fx = buf(D), buf(D), buf(D)
    P = (drums, music)
    # Gancho (0–4 s): golpes secos en cada palabra, sobre un colchón tenso.
    for k, tt in enumerate([0.0, 0.5, 1.0, 1.5, 2.0, 2.5]):
        add(fx, golpe(), tt); add(music, acorde(PROG[k // 2 % 4][1], 0.22, 3000), tt, 1.6)
    add(music, colchon([57, 60, 64], 4.0, 900), 0.0, 1.2)
    add(fx, subida(1.5), 2.5); add(drums, redoble(1.0), 3.0)
    # Drop con el logo.
    add(fx, impacto(), 4.0)
    seccion(P, 4.0, 30.0)
    for k in range(8): add(fx, barrido(0.4), 6.0 + 3 * k - 0.25)
    # Pausa: sin bombo, campanas con la melodía, y subida.
    seccion(P, 30.0, 34.0, bombo=False, palmas=False, bajo_on=False, melodia=False, filtro=1200)
    for c in range(2):
        for pos, m in zip(RITMO, MELODIA[c]):
            add(music, campana(m + 12), 30.0 + c * 4 * B + pos * S)
    add(music, colchon([60, 64, 67, 72], 4.0), 30.0, 1.4)
    add(fx, subida(2.0), 32.0); add(drums, redoble(2.0), 32.0)
    # Segundo drop: el llamado a la acción.
    add(fx, impacto(1.1), 34.0)
    seccion(P, 34.0, 38.0)
    add(music, colchon([48, 60, 64, 67, 72], 2.6, 2200), 38.0, 1.8)
    add(fx, impacto(0.7), 38.0)
    return drums, music, fx, D

def teaser():
    D = 20.6; drums, music, fx = buf(D), buf(D), buf(D)
    P = (drums, music)
    add(music, colchon([57, 60, 64], 2.0, 800), 0.0, 1.4)
    add(fx, subida(1.5), 0.5); add(drums, redoble(1.0), 1.0)
    add(fx, impacto(), 2.0)
    seccion(P, 2.0, 12.0)
    for k in range(10): add(fx, barrido(0.3, 0.7), 2.0 + k - 0.15)
    add(fx, impacto(0.9), 12.0)
    seccion(P, 12.0, 16.0, bombo=False, palmas=False, bajo_on=False, melodia=False, filtro=1000)
    for c in range(2):
        for pos, m in zip(RITMO, MELODIA[c]):
            add(music, campana(m + 12), 12.0 + c * 4 * B + pos * S)
    add(fx, subida(1.6), 14.4); add(drums, redoble(1.6), 14.4)
    add(fx, impacto(1.1), 16.0)
    seccion(P, 16.0, 18.0)
    add(music, colchon([48, 60, 64, 67, 72], 2.6, 2200), 18.0, 1.8)
    return drums, music, fx, D

def mezclar(drums, music, fx, D, nombre):
    # Bombeo: la música baja con cada bombo (estilo house).
    pulso = np.zeros(len(music)); n = int(B * SR)
    curva = 1 - 0.55 * np.exp(-np.arange(n) / SR * 9)
    eng = np.abs(lowpass(drums, 150)); eng = np.convolve(eng, np.ones(400) / 400, 'same')
    duck = np.ones(len(music))
    i = 0
    while i < len(music):
        if eng[i] > 0.15:
            m = min(n, len(music) - i); duck[i:i + m] = np.minimum(duck[i:i + m], curva[:m]); i += int(B * SR * 0.8)
        else:
            i += 200
    music = reverb(music * duck, 2.0, 0.22)
    fx = reverb(fx, 1.4, 0.15)
    drums = reverb(drums, 0.6, 0.06)
    mix = drums * 0.85 + music + fx * 0.9
    n = int(D * SR); mix = mix[:n]
    f = int(1.0 * SR); mix[-f:] *= np.linspace(1, 0, f)
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    mix /= np.max(np.abs(mix)) / 0.9
    # Estéreo: las partes agudas se abren un poco.
    ancho = highpass(mix, 2500) * 0.18
    st = (np.stack([mix + ancho, mix - ancho], 1) / 1.1 * 32767).astype(np.int16)
    with wave.open(nombre, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
    print(nombre, f'{D} s')

if __name__ == '__main__':
    q = sys.argv[1]
    mezclar(*(anuncio() if q == 'anuncio' else teaser()), f'{q}.wav')
