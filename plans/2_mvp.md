# MVP-Plan: xls2ccu3

## Ziel
Python-Script, das Heizprofile (Raum × Wochentag × Zeit-Range → Temperatur) aus einer Tabellenquelle liest und auf BWTH-Geräten (Bad-Wandthermostat HmIP-BWTH) einer CCU3 setzt — nur bei tatsächlichen Änderungen, um unnötiges Blinken zu vermeiden.

## Technische Machbarkeit
Alles Standardtechnik — kein Blocker:
- XLS lesen via `openpyxl`
- Google Drive Public-Share via direktem Download (`uc?export=download&id=…`) mit `requests`; kein OAuth im MVP
- CCU3 via XML-RPC (HmIP-Port 2010) oder ReGaHSS-Script über HTTP (Port 8181). MVP verwendet **ReGaHSS-HTTP**, weil Wochenprogramm-Datenpunkte sich dort am einfachsten batch-lesen/schreiben lassen
- Idempotenz durch Read-before-Write und Vergleich mit Toleranz (0.5°C-Raster der BWTH)

## Input-Format (Quelle: XLS)

Eine XLSX-Datei mit **einem Sheet pro Raum** (Sheet-Name = Raum-Alias auf der CCU3, z. B. `Bad`, `Gaeste-WC`).

Jedes Sheet hat folgende Struktur:

| von   | bis   | Mo | Di | Mi | Do | Fr | Sa | So |
|-------|-------|----|----|----|----|----|----|----|
| 00:00 | 06:00 | 17 | 17 | 17 | 17 | 17 | 17 | 17 |
| 06:00 | 08:30 | 21 | 21 | 21 | 21 | 21 | 22 | 22 |
| 08:30 | 17:00 | 17 | 17 | 17 | 17 | 17 | 21 | 21 |
| 17:00 | 22:00 | 22 | 22 | 22 | 22 | 22 | 22 | 22 |
| 22:00 | 24:00 | 17 | 17 | 17 | 17 | 17 | 17 | 17 |

Regeln:
- Zeiten in 10-Minuten-Schritten (BWTH-Raster), sortiert, lückenlos, 00:00 bis 24:00
- Temperaturen in 0.5°C-Schritten, Bereich 4.5–30.5 (Off=4.5, On=30.5)
- Max. 13 Umschaltpunkte pro Tag (BWTH-Hardware-Limit)

Alternative YAML-Variante (falls XLS umständlich) bleibt optional — MVP liefert XLS.

## Parameter / CLI

```
xls2ccu3 <source> [--dry-run] [--room ROOM]

<source>  Pfad zu .xlsx ODER Google-Drive-Share-Link (öffentlich)
--dry-run Nur Diff anzeigen, nichts schreiben
--room    Nur einen Raum verarbeiten (Sheet-Name)
```

## Konfiguration (.env)

```
CCU3_HOST=192.168.x.x
CCU3_PORT=8181           # ReGaHSS-HTTP (TLS-Port 48181 optional)
CCU3_USER=Admin          # optional, falls Auth aktiv
CCU3_PASSWORD=...
```

Es wird zusätzlich eine `.env.template` committet.

## Ablauf

1. **Source laden**
   - Lokaler Pfad → direkt öffnen
   - URL mit `drive.google.com` → File-ID extrahieren → Download nach Tempdatei
2. **Parsen**: pro Sheet ein `RoomSchedule`-Objekt mit 7 Tageslisten `[(endtime_minutes, temperature), …]`, maximal 13 Einträge, letzter Endtime = 1440
3. **CCU3 lesen**: pro Raum und Tag die 13 Datenpunkte `P1_ENDTIME_<DAY>_<N>` und `P1_TEMPERATURE_<DAY>_<N>` (N=1..13) des BWTH-Channel 1
4. **Diff bilden**: Ziel- vs. Ist-Zustand. Nicht genutzte Slots mit Endtime=1440 und gleicher Temperatur auffüllen (CCU3-Konvention), damit Vergleich stabil ist
5. **Schreiben** nur falls Diff ≠ ∅: alle geänderten Datenpunkte **eines Tages** in einem ReGaHSS-Script-Batch setzen. Pro geändertem Tag **ein** Speichervorgang → Blinken minimal. Unveränderte Tage unangetastet lassen
6. **Report**: Pro Raum/Tag: `unchanged` / `updated (N datapoints)` / `dry-run diff`

## Raum-→-Gerät-Mapping

Sheet-Name wird gegen den **Raum-Namen** der CCU3 gemappt. Pro Raum wird das erste Gerät vom Typ `HmIP-BWTH` (Channel 1 = Wochenprogramm) verwendet. Das Mapping wird beim Start geloggt, damit Fehlzuordnungen sichtbar sind. Falls ein Sheet keinen passenden Raum/BWTH findet → Warnung, Script läuft mit den anderen weiter.

## Projekt-Struktur

```
xls2ccu3/
  xls2ccu3.py           # CLI-Entrypoint
  src/
    loader.py           # lokale Datei + Google-Drive-Download
    parser.py           # XLS → RoomSchedule
    ccu3.py             # ReGaHSS-Client (read/write, Script-Batch)
    diff.py             # Ist/Soll-Vergleich mit 0.5°-Toleranz
  .env.template
  requirements.txt      # openpyxl, requests, python-dotenv
  README.md
```

## Out-of-Scope (MVP)
- Private Google-Drive-Dateien (OAuth)
- Nicht-BWTH-Geräte (andere Thermostat-Typen)
- Urlaubsmodus / Boost / weitere HmIP-Features
- Unit-Tests gegen echte CCU3 — manueller Test mit `--dry-run` reicht zunächst

## Offene Fragen an den User
1. IP/Hostname der CCU3 bekannt? Authentifizierung aktiv?
2. Wie viele Räume / BWTH-Geräte? (wegen Mapping-Strategie)
3. Lieber das XLS-Format wie oben — oder doch YAML im MVP?
