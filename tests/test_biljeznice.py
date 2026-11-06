"""Testovi javnog repozitorija bilježnica (pokretanje: ``.venv/bin/pytest -q`` u korijenu).

- svaka bilježnica izvodi se od vrha prema dnu bez greške, bez zvučne kartice i bez
  interneta (nbclient, kao na predavanju);
- repozitorij sadrži samo dopuštene vrste datoteka i nikakav nastavnički sadržaj;
- svaki zvučni zapis u ``zvuk/`` ima u ``LICENSE-sadrzaj.md`` naveden izvor i licencu.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

KORIJEN = Path(__file__).resolve().parent.parent
BILJEZNICE = sorted(KORIJEN.glob("*.ipynb"))
ZVUK = KORIJEN / "zvuk"
LICENCA_SADRZAJA = KORIJEN / "LICENSE-sadrzaj.md"

TIMEOUT_CELIJE = 120          # s; na predavanju ćelija traje manje od 10 s
DOPUSTENI_NASTAVCI = {".ipynb", ".py", ".md", ".txt", ".wav"}
DOPUSTENA_IMENA = {".gitignore"}
# Nastavnički sadržaj (rješenja vježbi, kviz s očekivanim vrijednostima, recenzentske
# inačice) ne smije u javni repozitorij ni kao dopuštena vrsta datoteke (npr. .py).
NASTAVNICKA_IMENA = re.compile(r"rjesenj|rješenj|nastavni|recenz|kviz|kostur", re.I)
# Bilježnice sa zvukom: njihova funkcija klizača mora ponuditi zvuk (<audio>). Ostale (npr.
# P05_odziv_zeta) zvuka nemaju i rade bez zvučnika. Nova bilježnica sa zvukom dodaje se ovdje.
ZVUCNE = {"P08_konvolucija_zvuk", "P09_harmonici_zvuk", "P12_aliasing_zvuk", "P13_spektar_snimke",
          "P15_digitalni_filtar_zvuk"}
MREZA = re.compile(r"https?://|urllib|requests|urlretrieve|wget|curl|socket", re.I)


def test_postoji_barem_jedna_biljeznica():
    assert BILJEZNICE, "u korijenu repozitorija nema nijedne .ipynb"
    # popis zvučnih bilježnica ne zastarijeva: svaka postoji
    assert ZVUCNE <= {p.stem for p in BILJEZNICE}, ZVUCNE


def _klijent(nb):
    """NotebookClient bez nbclientove obrade Output widgeta (``widget_registry`` prazan).

    nbclient sinkronizira stanje Output widgeta (``interactive``/``interact``) slanjem na
    shell kanal dok čeka odgovor jezgre na istom kanalu; s pyzmq asyncio to katkad „proguta”
    buđenje, pa ćelija čeka do isteka timeouta (izmjereno: 8–120 s, jednom 325 s) iako je
    jezgra odgovorila odmah. Zato se bilježnice izvode ovim testom, a ne s
    ``jupyter nbconvert --execute``. Bez obrade widgeta izlazi funkcije klizača (slika, zvuk,
    eventualna greška) postaju obični izlazi ćelije, pa ih test vidi."""
    from nbclient import NotebookClient

    klijent = NotebookClient(nb, timeout=TIMEOUT_CELIJE, kernel_name="python3",
                             resources={"metadata": {"path": str(KORIJEN)}})
    # nbclient puni widget_registry u __init__ (ne u execute); ako se to promijeni, test pada
    assert "@jupyter-widgets/output" in getattr(klijent, "widget_registry", {}), \
        "nbclient više nema widget_registry: provjeriti zaobilaznicu"
    klijent.widget_registry = {}
    return klijent


@pytest.mark.parametrize("put", BILJEZNICE, ids=lambda p: p.name)
def test_sve_se_izvode(put):
    """Izvođenje od vrha prema dnu (nbclient) bez greške; IPython.display.Audio ne treba
    zvučnu karticu (zvuk se ugrađuje u izlaz), a klizači (ipywidgets) rade i bez preglednika.
    Greška u funkciji klizača ne ruši ćeliju (ipywidgets je ispiše), pa se traže i izlazi
    vrste ``error``. Funkcija klizača mora nacrtati sliku, a u bilježnicama sa zvukom
    (``ZVUCNE``) i ponuditi zvuk; bilježnica bez zvuka radi i bez zvučnika."""
    import nbformat

    nb = nbformat.read(put, as_version=4)
    _klijent(nb).execute()
    for celija in nb.cells:
        if celija.cell_type == "code":
            izlazi = celija.get("outputs", [])
            greske = [o for o in izlazi if o.get("output_type") == "error"]
            assert not greske, (celija.source[:200], greske)
            if "widgets.interact" in celija.source:
                # funkcija klizača se izvela: nacrtala sliku (i ponudila zvuk, ako je zvučna)
                podaci = [o.get("data", {}) for o in izlazi]
                assert any("image/png" in d for d in podaci), celija.source[:200]
                if put.stem in ZVUCNE:
                    assert any("<audio" in d.get("text/html", "") for d in podaci), \
                        celija.source[:200]


@pytest.mark.parametrize("put", BILJEZNICE, ids=lambda p: p.name)
def test_bez_interneta(put):
    """Kod bilježnice ne dohvaća ništa s mreže (na predavanju možda nema interneta)."""
    nb = json.loads(put.read_text(encoding="utf-8"))
    for celija in nb["cells"]:
        if celija["cell_type"] == "code":
            izvor = "".join(celija["source"])
            assert not MREZA.search(izvor), izvor


@pytest.mark.parametrize("put", BILJEZNICE, ids=lambda p: p.name)
def test_spremljena_bez_izlaza(put):
    """Bilježnica je u gitu bez izlaza (ugrađen zvuk i slike bi napuhali repozitorij)."""
    nb = json.loads(put.read_text(encoding="utf-8"))
    for celija in nb["cells"]:
        if celija["cell_type"] == "code":
            assert celija["outputs"] == [] and celija["execution_count"] is None


def _git_datoteke() -> list[str]:
    if not (KORIJEN / ".git").exists() or not shutil.which("git"):
        pytest.skip("nije git repozitorij")
    r = subprocess.run(["git", "ls-files", "-z"], cwd=KORIJEN, capture_output=True,
                       text=True, check=True)
    return [d for d in r.stdout.split("\0") if d]


def test_samo_dopustene_datoteke():
    datoteke = _git_datoteke()
    assert datoteke
    for d in datoteke:
        ime = Path(d).name
        assert (Path(d).suffix in DOPUSTENI_NASTAVCI or ime in DOPUSTENA_IMENA
                or ime.startswith("LICENSE")), f"nedopuštena vrsta datoteke: {d}"
        assert not NASTAVNICKA_IMENA.search(d), f"nastavnički sadržaj: {d}"


def _redci_licence() -> list[list[str]]:
    """Redci tablice zapisa u LICENSE-sadrzaj.md: ``| zvuk/ime.wav | izvor | licenca |``."""
    redci = []
    for redak in LICENCA_SADRZAJA.read_text(encoding="utf-8").splitlines():
        celije = [c.strip() for c in redak.strip().strip("|").split("|")]
        if redak.strip().startswith("|") and len(celije) >= 3 and celije[0].strip("`").startswith("zvuk/"):
            redci.append(celije)
    return redci


# Licence koje dopuštaju objavu u javnom repozitoriju i u udžbeniku (ne NC ni ND)
DOPUSTENE_LICENCE = {"CC0", "CC0 1.0", "CC BY 4.0", "CC BY-SA 4.0"}


def test_svaki_zapis_ima_licencu():
    zapisi = sorted(p.relative_to(KORIJEN).as_posix() for p in ZVUK.glob("*.wav"))
    assert zapisi, "zvuk/ nema nijednog zapisa"
    navedeni = {c[0].strip("`"): c for c in _redci_licence()}
    for z in zapisi:
        assert z in navedeni, f"{z} nije naveden u LICENSE-sadrzaj.md"
        _, izvor, licenca, *_ = navedeni[z]
        assert izvor, f"{z}: nedostaje izvor"
        licenca = " ".join(licenca.strip("`* ").split())
        assert licenca in DOPUSTENE_LICENCE, (
            f"{z}: licenca „{licenca}” nije među dopuštenima {sorted(DOPUSTENE_LICENCE)}")


def test_zamjenski_zvuk_je_svjez(tmp_path):
    """Zapisi u zvuk/ su upravo oni koje generira alati/zamjenski_zvuk.py (vlastiti zvuk)."""
    subprocess.run([sys.executable, str(KORIJEN / "alati" / "zamjenski_zvuk.py"), str(tmp_path)],
                   check=True)
    from scipy.io import wavfile

    novi = sorted(p.name for p in tmp_path.glob("*.wav"))
    assert novi
    for ime in novi:
        fs_novi, novi_uzorci = wavfile.read(tmp_path / ime)
        fs_zvuk, uzorci = wavfile.read(ZVUK / ime)
        assert (fs_novi, novi_uzorci.dtype, novi_uzorci.shape) == (fs_zvuk, uzorci.dtype, uzorci.shape), ime
        # zaokruživanje na int16 smije se razlikovati za 1 na drugom OS-u ili inačici numpyja
        razlika = np.max(np.abs(novi_uzorci.astype(np.int32) - uzorci.astype(np.int32)))
        assert razlika <= 1, (ime, razlika)


# Bilježnice koje učitavaju vlastiti WAV istom funkcijom ``ucitaj`` (P13 i P15 su je preuzele
# iz P08)
VLASTITI_WAV = ("P08_konvolucija_zvuk", "P13_spektar_snimke", "P15_digitalni_filtar_zvuk")


def _ucitaj_iz_biljeznice(monkeypatch, ime="P08_konvolucija_zvuk"):
    """Funkcija ``ucitaj`` iz bilježnice (ćelija s importima i ćelija s ``def ucitaj``)."""
    monkeypatch.setenv("MPLBACKEND", "Agg")
    monkeypatch.chdir(KORIJEN)
    nb = json.loads((KORIJEN / f"{ime}.ipynb").read_text(encoding="utf-8"))
    kod = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    prostor: dict = {"display": lambda *a, **k: None}
    exec(kod[0], prostor)
    exec(next(k for k in kod if "def ucitaj" in k), prostor)
    return prostor["ucitaj"]


@pytest.mark.parametrize("ime", VLASTITI_WAV)
def test_ucitaj_8bit_stereo_i_48khz(tmp_path, monkeypatch, ime):
    """Snimka s mobitela: 8-bitni WAV i 48 kHz stereo pretvaraju se u mono −1 … 1 na 44,1 kHz."""
    from scipy.io import wavfile

    ucitaj = _ucitaj_iz_biljeznice(monkeypatch, ime)
    wavfile.write(tmp_path / "osam.wav", 44100, np.array([128, 255, 0, 128], dtype=np.uint8))
    fs, s = ucitaj("osam.wav", fs=44100, mapa=tmp_path)
    assert fs == 44100
    assert np.allclose(s, [0, 127 / 128, -1, 0])
    t = np.arange(48000) / 48000
    ton = (0.5 * 32767 * np.sin(2 * np.pi * 1000 * t)).astype(np.int16)
    wavfile.write(tmp_path / "mobitel.wav", 48000, np.column_stack([ton, ton]))
    fs, s = ucitaj("mobitel.wav", fs=44100, mapa=tmp_path)
    assert fs == 44100 and s.ndim == 1 and len(s) == 44100
    assert abs(np.max(np.abs(s[1000:-1000])) - 0.5) < 0.01


@pytest.mark.parametrize("ime", VLASTITI_WAV)
def test_vlastite_snimke_u_moj_zvuk(ime):
    """Upute za vlastite snimke vode u mapu moj_zvuk/ (nije u gitu), ne u zvuk/: zapis u zvuk/
    bez izvora i licence u LICENSE-sadrzaj.md ruši test licenci."""
    assert "moj_zvuk/" in (KORIJEN / ".gitignore").read_text(encoding="utf-8").split()
    nb = json.loads((KORIJEN / f"{ime}.ipynb").read_text(encoding="utf-8"))
    tekstovi = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown"]
    tekstovi.append((KORIJEN / "README.md").read_text(encoding="utf-8"))
    for tekst in tekstovi:
        # „stavite/spremite … u (mapu) `zvuk/`“ unutar jedne rečenice
        assert not re.search(r"(stavite|spremite)[^.]*?\bu\s+(mapu\s+)?`zvuk/`", tekst), tekst
    assert any("moj_zvuk" in t and "snim" in t.lower() for t in tekstovi[:-1])


def _izlazi(nb) -> tuple[str, str]:
    """(sav ispisani tekst, sav HTML) iz izlaza izvedene bilježnice."""
    tekst, html = [], []
    for celija in nb.cells:
        for o in celija.get("outputs", []):
            if o.get("output_type") == "stream":
                tekst.append(o.get("text", ""))
            html.append(o.get("data", {}).get("text/html", ""))
    return "".join(tekst), "".join(html)


def test_p08_vlastiti_ulaz_i_odziv(tmp_path, monkeypatch):
    """Vlastite snimke preko P08_ULAZ i P08_ODZIV (kao da ih je nastavnik upisao u postavke):
    ulaz 48 kHz stereo 16 bita, 20 s s tišinom na početku; odziv 8 bita, 22,05 kHz, s 0,3 s
    tišine prije praska. Bilježnica se izvodi do kraja, skraćuje ulaz, reže tišinu i rep
    odziva, preuzorkuje odziv na 48 kHz i nudi zvuk."""
    import nbformat
    from scipy.io import wavfile

    rng = np.random.default_rng(1)
    fs_x = 48000
    t = np.arange(int(18.5 * fs_x)) / fs_x
    govor = (0.3 * np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 3 * t) > 0)
             + 0.01 * rng.standard_normal(len(t)))
    x = np.concatenate([np.zeros(int(1.5 * fs_x)), govor])           # 20 s
    lijevo = np.round(32767 * x).astype(np.int16)
    wavfile.write(tmp_path / "govor.wav", fs_x, np.column_stack([lijevo, lijevo // 2]))

    fs_h = 22050
    n = int(2.0 * fs_h)
    rep = rng.standard_normal(n) * np.exp(-np.log(1000) * np.arange(n) / fs_h / 0.5)
    rep[0] = 4.0                                                    # izravni zvuk
    h = np.concatenate([np.zeros(int(0.3 * fs_h)), rep / 4.0])
    wavfile.write(tmp_path / "pucanj_dvorana.wav", fs_h,
                  np.clip(np.round(128 + 127 * h), 0, 255).astype(np.uint8))

    monkeypatch.setenv("P08_ULAZ", str(tmp_path / "govor.wav"))
    monkeypatch.setenv("P08_ODZIV", str(tmp_path / "pucanj_dvorana.wav"))
    put = KORIJEN / "P08_konvolucija_zvuk.ipynb"
    nb = nbformat.read(put, as_version=4)
    _klijent(nb).execute()
    for celija in nb.cells:
        greske = [o for o in celija.get("outputs", []) if o.get("output_type") == "error"]
        assert not greske, (celija.source[:200], greske)
    tekst, html = _izlazi(nb)
    assert "ulaz: odrezano 1,30 s tišine na početku" in tekst, tekst
    assert "uzeto prvih 15,00 s" in tekst, tekst
    assert "pucanj_dvorana.wav: preuzorkovano s 22050 Hz na 48000 Hz" in tekst, tekst
    assert "odziv: odrezano 0,30 s tišine prije izravnog zvuka" in tekst, tekst
    assert "odziv: rep ispod" in tekst, tekst
    assert "f_s = 48000 Hz" in tekst and f"N_x = {15 * fs_x} uzoraka" in tekst, tekst
    assert "<audio" in html


def test_p08_greske_i_prijenos(tmp_path, monkeypatch):
    """Jasne greške za nepostojeću, ne-WAV i tihu datoteku; prijenos gumbom sprema u mapu."""
    from scipy.io import wavfile

    ucitaj = _ucitaj_iz_biljeznice(monkeypatch)
    with pytest.raises(FileNotFoundError, match="Nema datoteke"):
        ucitaj("nema.wav", mapa=tmp_path)
    (tmp_path / "pjesma.mp3").write_bytes(b"ID3\x03\x00")
    with pytest.raises(ValueError, match="samo WAV"):
        ucitaj(str(tmp_path / "pjesma.mp3"))
    (tmp_path / "krivo.wav").write_bytes(b"ID3\x03\x00" + bytes(100))
    with pytest.raises(ValueError, match="ne mogu pročitati kao WAV"):
        ucitaj(str(tmp_path / "krivo.wav"))
    wavfile.write(tmp_path / "tisina.wav", 44100, np.zeros(4410, dtype=np.int16))
    with pytest.raises(ValueError, match="tih"):
        ucitaj(str(tmp_path / "tisina.wav"))

    nb = json.loads((KORIJEN / "P08_konvolucija_zvuk.ipynb").read_text(encoding="utf-8"))
    kod = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    prostor: dict = {"display": lambda *a, **k: None}
    monkeypatch.delenv("P08_ULAZ", raising=False)
    monkeypatch.delenv("P08_ODZIV", raising=False)
    exec(kod[0], prostor)
    exec(next(k for k in kod if "ODZIV = ODZIV or" in k), prostor)       # postavke
    exec(next(k for k in kod if "def spremi_prijenos" in k), prostor)
    assert (prostor["ULAZ"], prostor["ODZIV"]) == ("", "")
    assert prostor["spremi_prijenos"]((), tmp_path) == ""
    put = prostor["spremi_prijenos"](({"name": "../snimka.wav", "content": memoryview(b"RIFF")},),
                                     tmp_path / "moj")
    assert Path(put) == tmp_path / "moj" / "snimka.wav"
    assert (tmp_path / "moj" / "snimka.wav").read_bytes() == b"RIFF"


def test_p13_vlastita_snimka(tmp_path, monkeypatch):
    """Vlastita snimka preko P13_SNIMKA (kao da ju je student upisao u postavke): stereo,
    16 bita, 44,1 kHz, 0,6 s tišine pa 2 s tona od 330 Hz s harmonikom. Bilježnica se izvodi
    do kraja, preuzorkuje snimku na 16 kHz, reže tišinu, nudi samo N koji stanu u snimku i
    zvuk, a najviši vrh je na tonu snimke."""
    import nbformat
    from scipy.io import wavfile

    fs = 44100
    t = np.arange(2 * fs) / fs
    rng = np.random.default_rng(2)
    ton = 0.4 * np.sin(2 * np.pi * 330 * t) + 0.1 * np.sin(2 * np.pi * 660 * t)
    x = np.concatenate([0.001 * rng.standard_normal(int(0.6 * fs)), ton])
    lijevo = np.round(32767 * x).astype(np.int16)
    wavfile.write(tmp_path / "ton.wav", fs, np.column_stack([lijevo, lijevo // 2]))
    monkeypatch.setenv("P13_SNIMKA", str(tmp_path / "ton.wav"))
    nb = nbformat.read(KORIJEN / "P13_spektar_snimke.ipynb", as_version=4)
    _klijent(nb).execute()
    for celija in nb.cells:
        greske = [o for o in celija.get("outputs", []) if o.get("output_type") == "error"]
        assert not greske, (celija.source[:200], greske)
    tekst, html = _izlazi(nb)
    assert "ton.wav: preuzorkovano s 44100 Hz na 16000 Hz" in tekst, tekst
    assert re.search(r"snimka: odrezano 0,6\d s tišine na početku", tekst), tekst
    assert "snimka: vrh normiran na 0,9" in tekst, tekst
    assert "ton.wav: izvorno f_s = 44100 Hz, analiza uz f_s = 16000 Hz" in tekst, tekst
    assert "klizač N od 256 do 16384" in tekst, tekst
    assert "za N = 32768 snimka bi trebala trajati barem" in tekst, tekst
    f_vrh = float(re.search(r"najviši vrh do \d+ Hz: f = ([\d,]+) Hz", tekst).group(1)
                  .replace(",", "."))
    assert abs(f_vrh - 330) < 16000 / 2048, f_vrh
    assert "<audio" in html


def _p13_funkcije(monkeypatch) -> dict:
    """Prostor imena bilježnice P13 nakon ćelije s importima, postavki i ćelija s funkcijama
    (``def opis`` i ``def ucitaj``), bez okoline P13_SNIMKA."""
    monkeypatch.setenv("MPLBACKEND", "Agg")
    monkeypatch.chdir(KORIJEN)
    monkeypatch.delenv("P13_SNIMKA", raising=False)
    nb = json.loads((KORIJEN / "P13_spektar_snimke.ipynb").read_text(encoding="utf-8"))
    kod = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    prostor: dict = {"display": lambda *a, **k: None}
    exec(kod[0], prostor)
    for oznaka in ("N_POCETNI =", "def opis", "def ucitaj"):
        exec(next(k for k in kod if oznaka in k), prostor)
    return prostor


def test_p13_greske(tmp_path, monkeypatch):
    """Jasne greške za nepostojeću, ne-WAV, tihu i prekratku snimku; bez vlastite snimke
    postavke ostaju na zadanoj sintetičkoj."""
    from scipy.io import wavfile

    p = _p13_funkcije(monkeypatch)
    assert p["SNIMKA"] == ""
    with pytest.raises(FileNotFoundError, match="Nema datoteke"):
        p["ucitaj"]("nema.wav", mapa=tmp_path)
    (tmp_path / "pjesma.mp3").write_bytes(b"ID3\x03\x00")
    with pytest.raises(ValueError, match="samo WAV"):
        p["ucitaj"](str(tmp_path / "pjesma.mp3"))
    wavfile.write(tmp_path / "tisina.wav", 44100, np.zeros(4410, dtype=np.int16))
    with pytest.raises(ValueError, match="tih"):
        p["ucitaj"](str(tmp_path / "tisina.wav"))
    kratka = np.ones(100)
    pocetak = p["pocetak_odsjecka"](len(kratka))
    with pytest.raises(ValueError, match="prekratka"):
        p["opis_snimke"](kratka, "kratka.wav", pocetak, p["moguci_n"](len(kratka), pocetak))


def _vrhovi_zica(p: dict, snimka, N: int, prozor: str) -> int:
    """Broj vrhova jednostranog spektra (nadopuna ×16) oko osnovnih tonova dviju žica zadane
    snimke P13 viših od pola amplitude osnovnog tona prve žice."""
    pocetak = p["pocetak_odsjecka"](len(snimka))
    f, A = p["spektar"](snimka[pocetak:pocetak + N], prozor, 16)
    sredina = p["F0"] + p["RASTIMANOST"] / 2
    m = np.abs(f - sredina) <= 3 * p["RASTIMANOST"]
    a = A[m]
    prag = 0.5 * p["HARMONICI"][0]
    return int(sum(1 for i in range(1, len(a) - 1)
                   if a[i] > a[i - 1] and a[i] >= a[i + 1] and a[i] > prag))


def test_p13_razlucivanje_zadane_snimke(monkeypatch):
    """Prikaz razlučivanja u odjeljcima 4 i 5 bilježnice P13 ovisi o zadanoj snimci (SJEME,
    F0, RASTIMANOST, HARMONICI): osnovni tonovi dviju žica uz pravokutni prozor daju jedan vrh
    uz zadani N = 2048, a dva od N = 4096; uz Hannov prozor jedan vrh i uz N = 4096, a dva od
    N = 8192. Promjena snimke koja to pokvari ruši ovaj test."""
    p = _p13_funkcije(monkeypatch)
    snimka = p["sinteza"]()
    ocekivano = {("pravokutni", 2048): 1, ("pravokutni", 4096): 2, ("pravokutni", 8192): 2,
                 ("pravokutni", 16384): 2, ("Hannov", 2048): 1, ("Hannov", 4096): 1,
                 ("Hannov", 8192): 2, ("Hannov", 16384): 2}
    dobiveno = {k: _vrhovi_zica(p, snimka, N, k[0]) for k in ocekivano for N in [k[1]]}
    assert dobiveno == ocekivano, dobiveno
    assert p["N_POCETNI"] == 2048


def test_p15_vlastita_snimka(tmp_path, monkeypatch):
    """Vlastiti zapis preko P15_SNIMKA (kao da ga je student upisao u postavke): stereo,
    16 bita, 44,1 kHz, 0,5 s tišine pa 2 s tona od 300 Hz uz šum i pisak od 3 kHz. Bilježnica
    se izvodi do kraja, preuzorkuje zapis na 16 kHz, reže tišinu, normira vrh i nudi zvuk prije
    i poslije filtra; izlaz pomičnog prosjeka s nulom na 3 kHz nema piska."""
    import nbformat
    from scipy.io import wavfile

    fs = 44100
    t = np.arange(2 * fs) / fs
    rng = np.random.default_rng(3)
    x = (0.4 * np.sin(2 * np.pi * 300 * t) + 0.05 * np.sin(2 * np.pi * 3000 * t)
         + 0.03 * rng.standard_normal(len(t)))
    x = np.concatenate([0.001 * rng.standard_normal(int(0.5 * fs)), x])
    lijevo = np.round(32767 * x).astype(np.int16)
    wavfile.write(tmp_path / "govor.wav", fs, np.column_stack([lijevo, lijevo // 2]))
    monkeypatch.setenv("P15_SNIMKA", str(tmp_path / "govor.wav"))
    nb = nbformat.read(KORIJEN / "P15_digitalni_filtar_zvuk.ipynb", as_version=4)
    # pomični prosjek s M = 16 ima nulu na 3 kHz (3 · 16000/16): pisak u izlazu nestane
    nb.cells.append(nbformat.v4.new_code_cell(
        "izlaz = filtriraj(zapis, *model('pomični prosjek', 1000, 16))\n"
        "f, S_iz = spektar_db(izlaz)\n"
        "i = int(np.argmin(np.abs(f - 3000)))\n"
        "print('PISAK', round(S_ulaz[i] - S_iz[i]))"))
    _klijent(nb).execute()
    for celija in nb.cells:
        greske = [o for o in celija.get("outputs", []) if o.get("output_type") == "error"]
        assert not greske, (celija.source[:200], greske)
    tekst, html = _izlazi(nb)
    assert "govor.wav: preuzorkovano s 44100 Hz na 16000 Hz" in tekst, tekst
    assert re.search(r"snimka: odrezano 0,5\d s tišine na početku", tekst), tekst
    assert "snimka: vrh normiran na 0,9" in tekst, tekst
    assert "govor.wav: izvorno f_s = 44100 Hz, filtrira se uz f_s = 16000 Hz" in tekst, tekst
    assert int(re.search(r"PISAK (-?\d+)", tekst).group(1)) > 40, tekst
    assert html.count("<audio") >= 3, html.count("<audio")


def _p15_funkcije(monkeypatch) -> dict:
    """Prostor imena bilježnice P15 nakon ćelije s importima, postavki i ćelija s funkcijama
    (``def opis`` i ``def ucitaj``), bez okoline P15_SNIMKA."""
    monkeypatch.setenv("MPLBACKEND", "Agg")
    monkeypatch.chdir(KORIJEN)
    monkeypatch.delenv("P15_SNIMKA", raising=False)
    nb = json.loads((KORIJEN / "P15_digitalni_filtar_zvuk.ipynb").read_text(encoding="utf-8"))
    kod = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    prostor: dict = {"display": lambda *a, **k: None}
    exec(kod[0], prostor)
    for oznaka in ("F_C_POCETNA =", "def opis", "def ucitaj"):
        exec(next(k for k in kod if oznaka in k), prostor)
    return prostor


def test_p15_greske(tmp_path, monkeypatch):
    """Jasne greške za nepostojeći, ne-WAV, tihi i prekratki zapis i nepoznat filtar; bez
    vlastitog zapisa postavke ostaju na zadanom sintetičkom."""
    from scipy.io import wavfile

    p = _p15_funkcije(monkeypatch)
    assert p["SNIMKA"] == ""
    with pytest.raises(FileNotFoundError, match="Nema datoteke"):
        p["ucitaj"]("nema.wav", mapa=tmp_path)
    (tmp_path / "pjesma.mp3").write_bytes(b"ID3\x03\x00")
    with pytest.raises(ValueError, match="samo WAV"):
        p["ucitaj"](str(tmp_path / "pjesma.mp3"))
    wavfile.write(tmp_path / "tisina.wav", 44100, np.zeros(4410, dtype=np.int16))
    with pytest.raises(ValueError, match="tih"):
        p["ucitaj"](str(tmp_path / "tisina.wav"))
    with pytest.raises(ValueError, match="prekratak"):
        p["opis_snimke"](np.ones(1000), "kratak.wav")
    with pytest.raises(ValueError, match="nepoznat filtar"):
        p["model"]("Butterworth", 1000, 4)


def test_p15_pisak_i_nule(monkeypatch):
    """Zadani zapis P15: pisak leži na nuli pomičnog prosjeka za M = f_s/F_PISAK i njegove
    višekratnike s klizača, a ne za zadani M; uz zadani M i f_c svi filtri pisak samo
    oslabe. Promjena zapisa ili klizača koja to pokvari ruši ovaj test."""
    p = _p15_funkcije(monkeypatch)
    nule = [M for M in range(1, p["M_NAJVECI"] + 1)
            if abs(p["odziv"](*p["fir"](M), p["F_PISAK"])) < 1e-9]
    assert nule == [8, 16, 24], nule
    assert p["M_POCETNI"] not in nule
    for filtar in p["FILTRI"]:
        H = abs(p["odziv"](*p["model"](filtar, p["F_C_POCETNA"], p["M_POCETNI"]), p["F_PISAK"]))
        assert 0.3 < H < 0.8, (filtar, H)
