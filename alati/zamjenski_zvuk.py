"""Zamjenski zvučni zapisi za bilježnicu P08 (vlastiti, generirani; smiju se objaviti).

- ``suhi_zvuk.wav`` (3 s): „suhi” zapis bez odjeka: dva kratka „klika” (prasak šuma od
  20 ms), četiri tona (akord C-dur rastavljen, svaki 0,2 s) i završni akord koji traje
  gotovo do kraja zapisa. Klikovi su glasni prema tonovima, pa se u izlazu jasno čuje i
  vidi odjek jednog kratkog zvuka (klik ≈ δ, pa je δ * h = h). Tonovi pokazuju kako odjek
  razmazuje melodiju, a završni akord kako izlaz traje dulje od ulaza.
- ``odziv_pucanj.wav``: impulsni odziv prostorije, kakav bi dala snimka pucnja:
  izravni zvuk (impuls u t = 0), nekoliko ranih refleksija (od zidova, 7–41 ms) i
  eksponencijalno prigušen šum (kasni odjek) s vremenom odjeka RT60 (zadano 1 s). Šum
  odjeka prolazi kroz blagi niskopropusni filtar prvog reda, pa je odjek „tamniji” od
  izravnog zvuka (manje visokih frekvencija); sve frekvencije ipak trnu jednako brzo.
  Omjer izravnog i odjeknutog zvuka (DRR) je oko −12 dB. Odziv traje 1,5·RT60, ali
  najmanje 1,5 s, pa je odjek odrezan tek oko 90 dB ispod početka.

Zapisi su mono, 44,1 kHz, 16 bita. Generator slučajnih brojeva ima zadano sjeme, pa
skripta daje iste zapise (tests/test_biljeznice.py ih uspoređuje sa zvuk/).

Upotreba:  python alati/zamjenski_zvuk.py [mapa] [--rt60 SEKUNDE]   (zadano: zvuk/, 1 s)
Za pokuse: python alati/zamjenski_zvuk.py moj_zvuk --rt60 2.5  (zvuk/ ostaje nepromijenjen)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import lfilter

FS = 44100                      # Hz
SJEME = 2026
RT60 = 1.0                      # s, vrijeme za koje odjek padne za 60 dB (zadano)
# (kašnjenje u s, amplituda): rane refleksije od zidova, poda i stropa
RANE_REFLEKSIJE = [(0.007, 0.62), (0.011, -0.48), (0.017, 0.40), (0.023, -0.33),
                   (0.031, 0.27), (0.041, -0.21)]
POJACANJE_ODJEKA = 0.09         # efektivna vrijednost šuma odjeka na početku (izravni = 1)
TONOVI = [523.25, 659.25, 783.99, 1046.50]     # Hz: C5, E5, G5, C6
AMPLITUDA_TONA = 0.25           # vrh tonova i akorda (vrh klika = 1)
TRAJANJE_KLIKA = 0.02           # s
KLIKOVI = (0.1, 0.6)            # s, trenuci klikova


def trajanje_odziva(rt60: float) -> float:
    """1,5·RT60, najmanje 1,5 s: odjek se odreže tek oko 90 dB ispod početka."""
    return max(1.5, 1.5 * rt60)


def _anvelopa(n: int, rub: int) -> np.ndarray:
    """1 u sredini, kosinusni porast i pad duljine ``rub`` uzoraka na krajevima."""
    a = np.ones(n)
    r = 0.5 - 0.5 * np.cos(np.pi * np.arange(rub) / rub)
    a[:rub] = r
    a[n - rub:] = r[::-1]
    return a


def _ton(frekvencije, trajanje: float) -> np.ndarray:
    """Zbroj tonova (s prvim višim harmonikom), vrh AMPLITUDA_TONA, s mekim rubovima."""
    n = int(trajanje * FS)
    t = np.arange(n) / FS
    s = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) for f in frekvencije)
    return AMPLITUDA_TONA * s / np.max(np.abs(s)) * _anvelopa(n, int(0.01 * FS))


def suhi_zvuk(rng: np.random.Generator) -> np.ndarray:
    """Klikovi (20 ms) u 0,1 s i 0,6 s; tonovi od 1,0 s (0,2 s, razmak 0,05 s); akord od 2,0 do 2,95 s."""
    x = np.zeros(int(3.0 * FS))
    n_klik = int(TRAJANJE_KLIKA * FS)
    for t0 in KLIKOVI:
        klik = rng.standard_normal(n_klik) * np.exp(-np.arange(n_klik) / (0.005 * FS))
        i0 = int(t0 * FS)
        x[i0:i0 + n_klik] = klik / np.max(np.abs(klik))
    for k, f in enumerate(TONOVI):
        ton = _ton([f], 0.2)
        i0 = int((1.0 + 0.25 * k) * FS)
        x[i0:i0 + len(ton)] = ton
    akord = _ton(TONOVI[:3], 0.95)
    i0 = int(2.0 * FS)
    x[i0:i0 + len(akord)] = akord
    return x


def odziv_pucanj(rng: np.random.Generator, rt60: float = RT60) -> np.ndarray:
    """Izravni zvuk + rane refleksije + šum s eksponencijalnom anvelopom e^(−6,91 t / RT60)."""
    n = int(trajanje_odziva(rt60) * FS)
    t = np.arange(n) / FS
    h = np.zeros(n)
    h[0] = 1.0
    for kasnjenje, a in RANE_REFLEKSIJE:
        h[int(round(kasnjenje * FS))] += a
    # kasni odjek: počinje oko 15 ms, raste do 50 ms, zatim trne 60 dB u RT60 sekundi
    sumovi = rng.standard_normal(n)
    sumovi = lfilter([0.35], [1, -0.65], sumovi)        # blagi niskopropusni filtar
    porast = np.clip((t - 0.015) / 0.035, 0, 1)
    rep = POJACANJE_ODJEKA * sumovi / np.std(sumovi) * porast * np.exp(-np.log(1000) * t / rt60)
    return h + rep


def u_int16(x: np.ndarray) -> np.ndarray:
    """Normira na vršnu vrijednost 0,9 i pretvara u 16-bitne cijele brojeve."""
    return np.round(0.9 * 32767 * x / np.max(np.abs(x))).astype(np.int16)


def napravi(mapa: Path, rt60: float = RT60) -> list[Path]:
    rng = np.random.default_rng(SJEME)
    mapa.mkdir(parents=True, exist_ok=True)
    zapisi = {"suhi_zvuk.wav": suhi_zvuk(rng), "odziv_pucanj.wav": odziv_pucanj(rng, rt60)}
    puti = []
    for ime, x in zapisi.items():
        put = mapa / ime
        wavfile.write(put, FS, u_int16(x))
        puti.append(put)
    return puti


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Zamjenski zvučni zapisi za bilježnicu P08.")
    p.add_argument("mapa", nargs="?", type=Path,
                   default=Path(__file__).resolve().parent.parent / "zvuk",
                   help="izlazna mapa (zadano: zvuk/)")
    p.add_argument("--rt60", type=float, default=RT60, help="vrijeme odjeka u s (zadano 1)")
    a = p.parse_args()
    for put in napravi(a.mapa, a.rt60):
        print(put)
