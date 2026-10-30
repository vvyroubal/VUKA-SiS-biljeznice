# Signali i sustavi — Jupyter bilježnice

Jupyter bilježnice uz kolegij **Signali i sustavi** (Veleučilište u Karlovcu, stručni
prijediplomski studij Mehatronika) i udžbenik *Signali i sustavi*. Na predavanju nastavnik s
prezentacije prebaci na bilježnicu i pojavu pokaže uživo. Studenti iste bilježnice mogu
pokretati sami.

Autor: mr.sc. Vedran Vyroubal

## Bilježnice

| Bilježnica | Predavanje | Poglavlje udžbenika | Sadržaj |
|---|---|---|---|
| `P08_konvolucija_zvuk.ipynb` | P08 | 8. Konvolucija i impulsni odziv | konvolucija suhog zvučnog zapisa s impulsnim odzivom prostorije (snimkom pucnja); slušanje, grafovi i klizači za udio odjeka i duljinu odziva |

Bilježnice rade bez interneta. Za zvuk trebaju zvučnici ili slušalice.

## Instalacija

Treba **Python 3.12 ili noviji** (<https://www.python.org/downloads/>). U mapi repozitorija:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter lab
```

JupyterLab se otvori u pregledniku. Otvorite bilježnicu i pokrenite ćelije redom
(Shift + Enter) ili izbornikom *Run → Run All Cells*.

Repozitorij možete preuzeti s `git clone` ili kao ZIP (gumb *Code → Download ZIP* na GitHubu).

## Struktura

```
P08_konvolucija_zvuk.ipynb   bilježnica uz predavanje P08
zvuk/                        zvučni zapisi (izvor i licenca: LICENSE-sadrzaj.md)
alati/zamjenski_zvuk.py      generira vlastite zamjenske zapise u zvuk/
tests/test_biljeznice.py     provjera: bilježnice se izvode, dopuštene datoteke, licence
requirements.txt             Python paketi
```

Zapisi u `zvuk/` su zamjenski: generira ih `python alati/zamjenski_zvuk.py`. Vlastite snimke
(WAV, mono ili stereo, 8/16/32 bita, bilo koja frekvencija uzorkovanja) stavite u `zvuk/` i u
bilježnici promijenite ime datoteke.

## Provjera

```bash
.venv/bin/pytest -q
```

Test izvodi svaku bilježnicu od vrha do dna (bez zvučne kartice i bez interneta), provjerava
da su u repozitoriju samo dopuštene vrste datoteka i da svaki zvučni zapis ima naveden izvor
i dopuštenu licencu (CC0, CC BY 4.0 ili CC BY-SA 4.0). Bilježnice se spremaju bez izlaza
(*Edit → Clear Outputs of All Cells*).

Bilježnice bez preglednika izvodite ovim testom, a ne s `jupyter nbconvert --execute`. S
klizačima (ipywidgets) nbconvert katkad čeka do isteka timeouta (opis u
`tests/test_biljeznice.py`, funkcija `_klijent`). U JupyterLabu toga nema.

Odziv s drugim vremenom odjeka napravite u zasebnoj mapi, da `zvuk/` ostane nepromijenjen:
`python alati/zamjenski_zvuk.py moj_zvuk --rt60 2.5` (mapa `moj_zvuk/` nije u gitu).

## Licence

- kod (`*.py` i kod u bilježnicama): MIT, datoteka `LICENSE`;
- tekst bilježnica i dokumentacije te vlastiti zvučni zapisi: CC BY 4.0, datoteka
  `LICENSE-sadrzaj.md`, gdje je i popis zvučnih zapisa s izvorom i licencom.
