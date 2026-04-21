# xls2ccu3

Liest Heizprofile aus einer XLSX-Datei und setzt sie auf HmIP-BWTH Geräten einer HomeMatic CCU3 — nur bei tatsächlichen Änderungen, um unnötiges Blinken zu vermeiden.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

```bash
cp .env.template .env
# Fill in CCU3_HOST, CCU3_USER, CCU3_PASSWORD
```

## Usage

```
python xls2ccu3.py <source> [--dry-run] [--room ROOM]

<source>    Path to .xlsx file or public Google Drive share link
--dry-run   Show diff only, write nothing
--room      Process a single room only (sheet name)
```

## XLSX-Format

Eine Datei mit **einem Sheet pro Raum** (Sheet-Name = Raum-Alias auf der CCU3).

| von   | bis   | Mo | Di | Mi | Do | Fr | Sa | So |
|-------|-------|----|----|----|----|----|----|----|
| 00:00 | 06:00 | 17 | 17 | 17 | 17 | 17 | 17 | 17 |
| 06:00 | 08:30 | 21 | 21 | 21 | 21 | 21 | 22 | 22 |
| 08:30 | 17:00 | 17 | 17 | 17 | 17 | 17 | 21 | 21 |
| 17:00 | 22:00 | 22 | 22 | 22 | 22 | 22 | 22 | 22 |
| 22:00 | 24:00 | 17 | 17 | 17 | 17 | 17 | 17 | 17 |

- Zeiten in 10-Minuten-Schritten, lückenlos von 00:00 bis 24:00
- Temperaturen in 0.5°C-Schritten (4.5 = Off, 30.5 = On)
- Max. 13 Zeilen pro Tag (Hardware-Limit des BWTH)
