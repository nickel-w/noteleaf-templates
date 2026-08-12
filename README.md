# Noteleaf – Druckvorlagen

A5-Druckvorlagen für Noteleaf.
Verbinden analoge Planung mit Nextcloud: ausdrucken, ausfüllen, einscannen.

---

## Vorlagen

| Datei | Beschreibung | QR-Code |
|-------|-------------|---------|
| `01_tagesplan.pdf`        | Stunden-Raster 06:00–21:30, Aufgaben-Checkboxen, Notizbereich (Punkt-Raster, randlos) | `noteleaf://daily/v1` |
| `02_wochenplan.pdf`       | 7 Tagesspalten, Stunden-Raster 07:00–22:00 | `noteleaf://weekly/v1` |
| `03_checkliste.pdf`       | 3 Kategoriegruppen mit je 5–6 Checkboxen | `noteleaf://checklist/v1` |
| `04_notizseite.pdf`       | Punkt-Raster (Dot Grid), Titel- und Tag-Feld | `noteleaf://notes/v1` |
| `05_meeting_notizen.pdf`  | Kopf (Thema/Teilnehmer), Notizbereich, Action Items (Kästchen, Wer, Bis) | `noteleaf://meeting/v1` |
| `06_tagesplan_quer.pdf`   | A5 quer, Tag auf zwei Zeitsäulen à 11mm, Aufgaben, Notizen | `noteleaf://daily-wide/v1` |

> Ältere ausgedruckte Bögen mit dem historischen `nc-planner://…`-Schema
> (Vorgängername der App) werden von der Noteleaf-App weiterhin erkannt –
> siehe `ScanTemplateRegistry::fromQrPayload()` im `noteleaf`-Repo.

> Alle Vorlagen verwenden kreisförmige Fadenkreuz-Registrierungstargets statt
> der älteren schwarzen Eck-Quadrate (siehe `_draw_markers()` in
> `generate_templates.py`, Standard-Stil `"target"`). Der quadratische Stil
> existiert dort weiterhin als Option (`style="square"`), damit historische
> Ausdrucke mit dem alten Marker-Layout kompatibel bleiben – neu erzeugte
> Vorlagen nutzen ihn aber nicht mehr.

Alle Vorlagen: **A5 (148 × 210 mm)**, schwarz-weiß druckbar.

---

## Aufbau jeder Vorlage

Jede Vorlage enthält drei maschinenlesbare Elemente:

```
┌─────────────────────────────────────────┐
│ ■ (Marker TL)              (Marker TR) ■│  ← Ausrichtungsmarker
│                                          │     für Perspektivkorrektur
│   [Inhalt]                               │     beim Scan
│                                          │
│ ■ (Marker BL)   noteleaf://…/v1   [QR] ■│  ← QR-Code: Vorlagentyp
└─────────────────────────────────────────┘
```

- **4 kreisförmige Fadenkreuz-Marker** in den Ecken (Ausrichtungsmarker, 5×5 mm Box)
- **QR-Code** rechts unten (18×18 mm) – kodiert Vorlagentyp und Version
- **Strukturierte Zonen** – jede Zone wird von der Scan-Verarbeitung in der Nextcloud-App (`noteleaf`) separat ausgewertet

Vorlagentyp, QR-Payload und die Zonen-Grenzen jeder Vorlage sind in
[`templates/manifest.json`](templates/manifest.json) deklariert. Diese Datei
ist die gemeinsame Quelle der Wahrheit für dieses Repo und für die
Nextcloud-App `noteleaf`, die daraus sowohl ihre Scan-Zonen-Registry als
auch – für Zonen ohne Sonderfall – den PDF-Druck generisch ableitet
(siehe Abschnitt „Weiterentwicklung" unten).

Jede Zone hat einen `type` (`timeGrid`, `taskList`, `noteArea`,
`titleField`, `tagsField`) und optional ein `renderer`-Feld, falls eine
Zone dieses Typs abweichend vom Standard gerendert werden soll (z. B.
`action_items` in `meeting`: `type: taskList`, aber
`renderer: actionItems`, weil es eine Tabelle mit Wer/Bis-Spalten statt
einer einfachen Checkbox-Liste ist). Fehlt `renderer`, entspricht er dem
`type`.

---

## Vorlagen generieren

### Voraussetzungen

```bash
pip install reportlab qrcode pillow
```

### Alle Vorlagen neu erstellen

```bash
python scripts/generate_templates.py
```

Die PDFs landen im Ordner `templates/`.

### Einzelne Vorlage erzeugen

```python
from scripts.generate_templates import make_tagesplan
make_tagesplan("mein_tagesplan.pdf", date_str="Fr, 11. April 2026")
```

### Vorlage vorausfüllen (aus Nextcloud-Daten)

```python
from scripts.generate_templates import make_tagesplan

events = [
    {"time": "07:00", "title": "Standup-Meeting"},
    {"time": "10:00", "title": "Sprint Review"},
]
tasks = [
    {"title": "E-Mails bearbeiten", "completed": True},
    {"title": "Nextcloud-App fertigstellen", "completed": False},
]

make_tagesplan("tagesplan_prefilled.pdf",
               date_str="Fr, 11. April 2026",
               events=events,
               tasks=tasks)
```

---

## Drucken

- Format: **A5** direkt, oder **A4 mit 2-up** (zwei A5 auf ein Blatt)
- Skalierung: **100%** (nicht „auf Seite anpassen")
- Ränder: **keine** / minimale Druckerränder
- Farbe: Schwarz-weiß reicht vollständig aus

### 2-up auf A4 drucken (Papier sparen)

```bash
# Mit pdfnup (pdfbook2 / pdfjam)
pdfjam --nup 2x1 --a4paper templates/01_tagesplan.pdf -o tagesplan_a4.pdf
```

---

## Weiterentwicklung

### Neue Vorlage hinzufügen

1. Neuen Eintrag (Typ, `displayName`, `qrPayload`, Zonen – ggf. mit
   `renderer`, falls eine Zone abweichend von ihrem `type` gedruckt werden
   soll) in `templates/manifest.json` ergänzen
2. Funktion `make_meinevorlage()` in `scripts/generate_templates.py` ergänzen, Zeichnung visuell konsistent zu den Zonen-Grenzen aus dem Manifest halten
3. PDF generieren (`python scripts/generate_templates.py`) und zusammen mit dem Manifest in `templates/` committen
4. **Ab hier automatisch:** `.github/workflows/template-sync.yml` im
   **`noteleaf`**-Repo übernimmt den Submodule-Bump und den
   Registry-Codegen von selbst (täglich, per PR). Falls die neue Vorlage
   nur bereits unterstützte Zonen-`renderer` verwendet (`noteArea`,
   `titleField`, `tagsField`, `taskList`, `actionItems`), funktioniert dort
   auch der PDF-Druck ohne weitere Code-Änderung. Nur bei wirklich neuem
   Layout (z. B. einem neuen Zeitraster-Typ) braucht `PdfService.php` im
   `noteleaf`-Repo noch eine eigene Ergänzung – siehe README dort.

### Vorlagen-Versionen

Der QR-Code enthält die Version (`/v1`, Feld `qrPayload` im Manifest). Bei inkompatiblen Layout-Änderungen Version erhöhen (`/v2`), damit ältere ausgedruckte Bögen weiterhin korrekt erkannt werden.

---

## Verwandte Repositories

| Repository   | Beschreibung |
|--------------|-------------|
| `noteleaf`   | Nextcloud-App: Tagesübersicht, Druckfunktion, Scan-Verarbeitung (löst die ausgedruckten Vorlagen über einen konfigurierbaren Scan-Ordner und einen Hintergrundjob wieder aus). Bindet dieses Repository als Git-Submodule ein und generiert daraus `lib/Service/Scan/ScanTemplateRegistry.php` per `composer run generate-registry`. |

---

## Lizenz

AGPL-3.0 – siehe [LICENSE](LICENSE)
