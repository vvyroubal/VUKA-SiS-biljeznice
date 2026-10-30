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
    """NotebookClient bez nbclientove obrade Output widgeta.

    nbclient sinkronizira stanje Output widgeta (``interact``) slanjem na shell kanal dok
    čeka odgovor jezgre na istom kanalu; s pyzmq asyncio to katkad „proguta” buđenje, pa
    ćelija čeka do isteka timeouta (izmjereno: 120 s, jednom i 325 s) iako je jezgra
    odgovorila odmah. Bez obrade widgeta izlazi funkcije klizača (slika, zvuk, eventualna
    greška) postaju obični izlazi ćelije, pa ih test i dalje vidi."""
    from nbclient import NotebookClient

    class Klijent(NotebookClient):
        def reset_execution_trackers(self):
            super().reset_execution_trackers()
            self.widget_registry = {}

    return Klijent(nb, timeout=TIMEOUT_CELIJE, kernel_name="python3",
                   resources={"metadata": {"path": str(KORIJEN)}})


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
            greske = [o for o in celija.get("outputs", []) if o.get("output_type") == "error"]
            assert not greske, (celija.source[:200], greske)


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


def test_svaki_zapis_ima_licencu():
    zapisi = sorted(p.relative_to(KORIJEN).as_posix() for p in ZVUK.glob("*.wav"))
    assert zapisi, "zvuk/ nema nijednog zapisa"
    navedeni = {c[0].strip("`"): c for c in _redci_licence()}
    for z in zapisi:
        assert z in navedeni, f"{z} nije naveden u LICENSE-sadrzaj.md"
        _, izvor, licenca, *_ = navedeni[z]
        assert izvor and licenca, f"{z}: nedostaje izvor ili licenca"


def test_zamjenski_zvuk_je_svjez(tmp_path):
    """Zapisi u zvuk/ su upravo oni koje generira alati/zamjenski_zvuk.py (vlastiti zvuk)."""
    subprocess.run([sys.executable, str(KORIJEN / "alati" / "zamjenski_zvuk.py"), str(tmp_path)],
                   check=True)
    novi = sorted(p.name for p in tmp_path.glob("*.wav"))
    assert novi
    for ime in novi:
        assert (tmp_path / ime).read_bytes() == (ZVUK / ime).read_bytes(), ime
