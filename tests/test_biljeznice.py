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
MREZA = re.compile(r"https?://|urllib|requests|urlretrieve|wget|curl|socket", re.I)


def test_postoji_barem_jedna_biljeznica():
    assert BILJEZNICE, "u korijenu repozitorija nema nijedne .ipynb"


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
    vrste ``error``."""
    import nbformat

    nb = nbformat.read(put, as_version=4)
    _klijent(nb).execute()
    for celija in nb.cells:
        if celija.cell_type == "code":
            izlazi = celija.get("outputs", [])
            greske = [o for o in izlazi if o.get("output_type") == "error"]
            assert not greske, (celija.source[:200], greske)
            if "widgets.interact" in celija.source:
                # funkcija klizača se izvela: nacrtala sliku i ponudila zvuk
                podaci = [o.get("data", {}) for o in izlazi]
                assert any("image/png" in d for d in podaci), celija.source[:200]
                assert any("<audio" in d.get("text/html", "") for d in podaci), celija.source[:200]


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


def _ucitaj_iz_biljeznice(monkeypatch):
    """Funkcija ``ucitaj`` iz bilježnice P08 (ćelija s importima i ćelija s ``def ucitaj``)."""
    monkeypatch.setenv("MPLBACKEND", "Agg")
    monkeypatch.chdir(KORIJEN)
    nb = json.loads((KORIJEN / "P08_konvolucija_zvuk.ipynb").read_text(encoding="utf-8"))
    kod = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    prostor: dict = {"display": lambda *a, **k: None}
    exec(kod[0], prostor)
    exec(next(k for k in kod if "def ucitaj" in k), prostor)
    return prostor["ucitaj"]


def test_ucitaj_8bit_stereo_i_48khz(tmp_path, monkeypatch):
    """Snimka s mobitela: 8-bitni WAV i 48 kHz stereo pretvaraju se u mono −1 … 1 na 44,1 kHz."""
    from scipy.io import wavfile

    ucitaj = _ucitaj_iz_biljeznice(monkeypatch)
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


def test_vlastite_snimke_u_moj_zvuk():
    """Upute za vlastite snimke vode u mapu moj_zvuk/ (nije u gitu), ne u zvuk/: zapis u zvuk/
    bez izvora i licence u LICENSE-sadrzaj.md ruši test licenci."""
    assert "moj_zvuk/" in (KORIJEN / ".gitignore").read_text(encoding="utf-8").split()
    nb = json.loads((KORIJEN / "P08_konvolucija_zvuk.ipynb").read_text(encoding="utf-8"))
    tekstovi = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown"]
    tekstovi.append((KORIJEN / "README.md").read_text(encoding="utf-8"))
    for tekst in tekstovi:
        # „stavite/spremite … u (mapu) `zvuk/`“ unutar jedne rečenice
        assert not re.search(r"(stavite|spremite)[^.]*?\bu\s+(mapu\s+)?`zvuk/`", tekst), tekst
    assert any("moj_zvuk" in t and "snim" in t.lower() for t in tekstovi[:-1])
