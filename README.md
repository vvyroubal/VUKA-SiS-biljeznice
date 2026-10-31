# Signali i sustavi — Jupyter bilježnice

Jupyter bilježnice uz kolegij **Signali i sustavi** (Veleučilište u Karlovcu, stručni
prijediplomski studij Mehatronika) i udžbenik *Signali i sustavi*. Na predavanju nastavnik s
prezentacije prebaci na bilježnicu i pojavu pokaže uživo. Studenti iste bilježnice mogu
pokretati sami.

Autor: mr.sc. Vedran Vyroubal

## Bilježnice

| Bilježnica | Predavanje | Poglavlje udžbenika | Sadržaj |
|---|---|---|---|
| `P08_konvolucija_zvuk.ipynb` | P08 | 8. Konvolucija i impulsni odziv | konvolucija suhog zvučnog zapisa s impulsnim odzivom prostorije (snimkom pucnja); slušanje, grafovi i klizači za udio odjeka i duljinu odziva; vlastiti ulazni zapis i impulsni odziv (WAV) |

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
moj_zvuk/                    vlastite snimke i pokusi (nije u gitu)
alati/zamjenski_zvuk.py      generira vlastite zamjenske zapise u zvuk/
tests/test_biljeznice.py     provjera: bilježnice se izvode (i s vlastitim WAV-om), dopuštene datoteke, licence
requirements.txt             Python paketi
```

Zapisi u `zvuk/` su zamjenski: generira ih `python alati/zamjenski_zvuk.py`. U `zvuk/` su
samo zapisi s izvorom i licencom u `LICENSE-sadrzaj.md`; zapis bez toga ruši test licenci.

## Vlastiti zapisi (P08)

U bilježnici P08 umjesto zadanih zapisa možete upotrijebiti vlastiti ulazni zapis (govor,
glazba) i vlastiti impulsni odziv (prasak balona ili pljesak u dvorani):

1. Snimku spremite u mapu `moj_zvuk/` (nije u gitu, pa ostaje samo na vašem računalu).
2. U ćeliji *Postavke* na vrhu bilježnice upišite putanje, npr.
   `ULAZ = "moj_zvuk/govor.wav"` i `ODZIV = "moj_zvuk/pucanj_dvorana.wav"` (prazno `""` =
   zadani zapis), pa pokrenite sve ćelije (*Run → Run All Cells*). Druga mogućnost je gumb
   za prijenos datoteke u idućoj ćeliji: prenesena datoteka sprema se u `moj_zvuk/`, a
   bilježnicu zatim ponovno pokrenete.
3. Bilježnica čita samo **WAV** (mono ili stereo, 8/16/24/32 bita, bilo koja frekvencija
   uzorkovanja). Zapis iz mobitela (M4A, MP3, OGG …) pretvorite u WAV, npr. u programu
   Audacity: *File → Open*, zatim *File → Export Audio…* (starije inačice: *File → Export →
   Export as WAV*), *Signed 16-bit PCM*; ili naredbom `ffmpeg -i snimka.m4a snimka.wav`.

Bilježnica zapise pripremi sama i ispiše svaku promjenu: stereo pretvori u mono, odziv
preuzorkuje na frekvenciju uzorkovanja ulaza (najviše 48 kHz), ulazu odreže dugu tišinu na
početku i skrati ga na `MAX_ULAZ_S` (zadano 15 s), a odzivu odreže tišinu prije izravnog
zvuka i tihi rep ispod `REP_DB` (zadano −60 dB). Za datoteku koja ne postoji, nije WAV ili je
tiha javi grešku s uputom. Upute za snimanje impulsnog odziva su u bilježnici.

Vlastita snimka smije u repozitorij (u mapu sa zapisima, s izvorom i licencom u
`LICENSE-sadrzaj.md`) samo pod licencom koja dopušta objavu (CC0, CC BY 4.0 ili
CC BY-SA 4.0); inače ostaje u `moj_zvuk/`.

Za automatske testove putanje se mogu zadati i varijablama okoline `P08_ULAZ` i
`P08_ODZIV` (vrijede kad je polje u postavkama prazno).

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
`python alati/zamjenski_zvuk.py moj_zvuk --rt60 2.5` (mapa `moj_zvuk/` nije u gitu), pa u
postavkama P08 upišite `ODZIV = "moj_zvuk/odziv_pucanj.wav"`.

## Licence

- kod (`*.py` i kod u bilježnicama): MIT, datoteka `LICENSE`;
- tekst bilježnica i dokumentacije te vlastiti zvučni zapisi: CC BY 4.0, datoteka
  `LICENSE-sadrzaj.md`, gdje je i popis zvučnih zapisa s izvorom i licencom.
