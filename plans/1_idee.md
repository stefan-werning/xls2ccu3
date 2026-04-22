Es soll ein Skript erstellt werden, z. B. in Python (Version 3).

Als Parameter soll ein Pfad zu einer XLS-Datei auf der Festplatte, ein Share-Link zu einer XLS-Datei auf Google Drive oder etwas anderes Sinnvolles übergeben werden können.

In der Excel-Datei sind die Temperaturen je Raum, Wochentag und Uhrzeit-Range strukturiert erfasst. Welche Struktur sich am besten eignet, kannst du vorgeben. Falls eine Umsetzung mit Excel schwierig ist, kannst du alternativ auch ein anderes Format festlegen, z. B. YAML.

Neben dem Skript liegt eine `.env`-Datei, in der die Zugangsdaten zu meiner CCU3 hinterlegt werden. Erstelle dazu eine `.env.template`.

Das Skript liest die Daten ein und setzt sie bei den BWTH-Geräten auf der CCU3. Die Werte sollen nur gesetzt und gespeichert werden, wenn sich tatsächlich etwas geändert hat. Hintergrund ist, dass die BWTH-Geräte bei jedem Speichern blinken – das soll nur passieren, wenn sich tatsächlich etwas geändert hat.
