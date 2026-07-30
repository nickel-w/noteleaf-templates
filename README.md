# NC Planner – Druckvorlagen

A5-Druckvorlagen für das NC Planner System.  
Verbinden analoge Planung mit Nextcloud: ausdrucken, ausfüllen, einscannen.

---

## Vorlagen

| Datei | Beschreibung | QR-Code |
|-------|-------------|---------|
| `01_tagesplan.pdf`    | Stunden-Raster 06:00–21:30, Aufgaben-Checkboxen, Notizbereich | `nc-planner://daily/v1` |
| `02_wochenplan.pdf`   | 7 Tagesspalten, Stunden-Raster 07:00–22:00 | `nc-planner://weekly/v1` |
| `03_checkliste.pdf`   | 3 Kategoriegruppen mit je 5–6 Checkboxen | `nc-planner://checklist/v1` |
| `04_notizseite.pdf`   | Punkt-Raster (Dot Grid), Titel- und Tag-Feld | `nc-planner://notes/v1` |
| `05_habit_tracker.pdf`| 10 Gewohnheiten × 31 Tage, Streak-Notizbereich | `nc-planner://habit/v1` |

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
│ ■ (Marker BL)  nc-planner://…/v1  [QR] ■│  ← QR-Code: Vorlagentyp
└─────────────────────────────────────────┘
```

- **4 schwarze Quadrate** in den Ecken (Ausrichtungsmarker, 5×5 mm)
- **QR-Code** rechts unten (18×18 mm) – kodiert Vorlagentyp und Version
- **Strukturierte Zonen** – jede Zone wird von der Scan-Verarbeitung in der Nextcloud-App separat ausgewertet

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

1. Funktion `make_meinevorlage()` in `scripts/generate_templates.py` ergänzen
2. QR-Payload definieren: `nc-planner://meintyp/v1`
3. Zonen-Definition in der **Nextcloud-App** (`nc_planner/lib/Service/Scan/ScanTemplateRegistry.php`) ergänzen
4. PDF generieren und in `templates/` committen

### Vorlagen-Versionen

Der QR-Code enthält die Version (`/v1`). Bei inkompatiblen Layout-Änderungen Version erhöhen (`/v2`), damit ältere ausgedruckte Bögen weiterhin korrekt erkannt werden.

---

## Verwandte Repositories

| Repository   | Beschreibung |
|--------------|-------------|
| `nc_planner` | Nextcloud-App: Tagesübersicht, Druckfunktion, Scan-Verarbeitung (löst die ausgedruckten Vorlagen über einen konfigurierbaren Scan-Ordner und einen Hintergrundjob wieder aus – keine separate Scan-App mehr nötig) |

---

## Lizenz

AGPL-3.0 – siehe [LICENSE](LICENSE)
