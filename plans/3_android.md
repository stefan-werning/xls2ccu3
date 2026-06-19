# Plan: Flutter Android App — xls2ccu3

## Ziel

Flutter-App für Android, die denselben Sync-Ablauf wie `xls2ccu3.py` ausführt:
Google-Drive-Tabelle herunterladen → parsen → mit CCU3-Istzustand vergleichen → nur geänderte Tage schreiben.

Der User startet den Sync direkt vom Handy, ohne PC.

---

## Voraussetzungen / Einschränkungen

- Handy muss im **gleichen WLAN** wie die CCU3 sein (CCU3 ist nicht über Internet erreichbar)
- Google Drive Tabelle muss **öffentlich freigegeben** sein (kein OAuth im MVP)
- CCU3 spricht unverschlüsseltes HTTP → AndroidManifest braucht `usesCleartextTraffic`

---

## Flutter-Packages

| Package | Zweck |
|---|---|
| `excel: ^4.0.6` | .xlsx lesen (reines Dart, kein native code) |
| `http: ^1.2.0` | Google-Drive-Download + CCU3 ReGaHSS HTTP |
| `xml: ^6.5.0` | XML-RPC Response parsen |
| `shared_preferences: ^2.3.0` | CCU3-Host, Port, User, Drive-URL speichern |
| `flutter_secure_storage: ^9.0.0` | CCU3-Passwort sicher im Android Keystore |

---

## Projektstruktur

```
flutter_app/
├── pubspec.yaml
├── android/app/src/main/
│   └── AndroidManifest.xml        ← usesCleartextTraffic="true"
└── lib/
    ├── main.dart
    ├── models/
    │   └── room_schedule.dart     ← RoomSchedule, DaySchedule, TimeSlot
    ├── services/
    │   ├── loader.dart            ← Port von loader.py
    │   ├── xlsx_parser.dart       ← Port von parser.py
    │   ├── ccu3_client.dart       ← Port von ccu3.py (eigener XML-RPC)
    │   ├── diff.dart              ← Port von diff.py
    │   └── sync_service.dart      ← Pipeline-Orchestrierung
    └── screens/
        ├── sync_screen.dart       ← Hauptbildschirm: Sync-Button + Log
        └── settings_screen.dart   ← CCU3-Zugangsdaten + Drive-URL
```

---

## Screens

### SyncScreen (Hauptbildschirm)
- Großer **„Sync starten"**-Button
- Toggle-Switch **„Dry Run"** (Default: aus) — wenn aktiv, wird nichts geschrieben, nur der Diff geloggt
- ScrollView mit Live-Log (wird während des Syncs Zeile für Zeile befüllt)
- Kleines Zahnrad-Icon oben rechts → Settings
- Statusanzeige: Erfolg / Fehler am Ende

### SettingsScreen
- CCU3 Host (IP oder Hostname)
- CCU3 Port (Default: 8181)
- CCU3 User (optional)
- CCU3 Passwort (SecureStorage, wird als `***` angezeigt)
- Google Drive Share-Link
- Speichern-Button

---

## Implementierung der Services

### loader.dart
Port von `loader.py`:
- Google-Drive-URL → File-ID extrahieren (Regex, identisch zu Python)
- Spreadsheet-URL: Export als XLSX via `https://docs.google.com/spreadsheets/d/{id}/export?format=xlsx`
- HTTP GET → Bytes → temporäre Datei (oder direkt als `List<int>` an Parser übergeben)

### xlsx_parser.dart
Port von `parser.py` mit dem `excel`-Package:
```dart
final Excel workbook = Excel.decodeBytes(bytes);
for (final sheetName in workbook.tables.keys) {
    final sheet = workbook.tables[sheetName]!;
    // Zeilen iterieren, Gruppen-Labels erkennen (Mo-Fr, Sa+So, etc.)
    // Gleiche Logik wie _parse_sheet() und _parse_group_label() in Python
}
```
Besonderheit: Das xlsx-Format verwendet **Gruppen-Label-Blöcke**:
```
Mo-Fr         ← Gruppen-Label
von | bis | Temp
00:00 | 06:00 | 17
...
Sa+So         ← nächster Block
von | bis | Temp
...
```
Die Gruppen-Label-Erkennung und Bereichsexpansion (`Mo-Fr` → `[Mo,Di,Mi,Do,Fr]`) muss exakt wie in `_parse_group_label()` portiert werden.

### ccu3_client.dart
Port von `ccu3.py`. Kein XML-RPC-Package nötig — selbst implementiert:

**ReGaHSS (HTTP POST zu `/tclrega.exe`):** identisch zu Python `_rega()`

**XML-RPC** (Port 2010) wird manuell gebaut:
```dart
String buildXmlRpcCall(String method, List<dynamic> params) {
  // <?xml version="1.0"?><methodCall>...
}

Map<String, dynamic> parseXmlRpcResponse(String xml) {
  // <methodResponse><params><param><value><struct>...
  // via xml-Package
}
```
Methoden:
- `findBwthDevices()` → `Map<String, String>` (Raum → Channel-Adresse)
- `readSchedule(channelAddr)` → `Map<String, List<TimeSlot>>`
- `writeDay(channelAddr, day, slots)` → void

### diff.dart
1:1-Port von `diff.py` — reine Dart-Logik, keine Abhängigkeiten:
- `normalize()` — auf 13 Slots auffüllen
- `effectiveSlots()` — aktive Slots bis Endzeit 1440
- `diffDay()` — Soll/Ist-Vergleich mit 0.25°C-Toleranz
- `computeDiffs()` — alle 7 Tage vergleichen

### sync_service.dart
Orchestriert die Pipeline und gibt Fortschritt über einen `Stream<String>` aus (für Live-Log im UI):
```dart
Stream<String> runSync(SyncConfig config, {bool dryRun = false}) async* {
    yield "Lade Tabelle von Google Drive...";
    final bytes = await loader.download(config.driveUrl);
    yield "Parse XLSX...";
    final rooms = xlsxParser.parse(bytes);
    yield "Verbinde mit CCU3 ${config.host}...";
    final deviceMap = await ccu3.findBwthDevices();
    // pro Raum: lesen → diff → schreiben (oder bei dryRun: nur loggen)
    if (dryRun) yield "  [dry-run] würde N Slots schreiben";
    yield "Fertig.";
}
```

---

## AndroidManifest.xml (wichtige Änderungen)

```xml
<uses-permission android:name="android.permission.INTERNET"/>

<application
    android:usesCleartextTraffic="true"
    ...>
```

---

## Ablauf (identisch zu xls2ccu3.py)

1. XLSX von Google Drive herunterladen
2. Alle Sheets parsen → `List<RoomSchedule>`
3. CCU3 verbinden → `Map<String, String>` Raum→Channel
4. Pro Raum:
   - Aktuellen Zeitplan lesen (`getParamset`)
   - Diff berechnen
   - Nur geänderte Tage schreiben (`putParamset`) — ein Write pro Tag
5. Log im UI anzeigen

---

## Out of Scope (MVP)

- Einzelner Raum (–room Filter)
- iOS (funktioniert technisch, ungetestet)
- Hintergrund-Sync / Scheduler
- OAuth für private Google-Drive-Dateien
- Andere Thermostat-Typen (nicht BWTH)

---

## Offene Fragen

1. Soll die App auch funktionieren wenn das Handy **nicht im Heimnetz** ist (VPN)? → kein Einfluss auf die App selbst, aber Voraussetzung für den User
2. Google-Drive-Link — öffentlich freigegeben oder privat? → bei privat: OAuth nötig (deutlich mehr Aufwand)
3. Soll der Google-Drive-Link fest in Settings gespeichert sein, oder auch über QR-Code / Teilen-Dialog übergeben werden können?
