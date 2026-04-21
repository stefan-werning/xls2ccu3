es soll ein Script erstellt werden, z.b. Python (Version 3).

als Parameter soll ein Pfad zu einer xls Datei auf der Festplatte, ein share Link zu einer xls Datei auf Google Drive oder anderes sinnvolles mitgegeben werden.

in der Excel ist strukturiert Temperaturen je Raum, Wochentag und uhrzeit-range erfasst. welche Struktur sich am besten eignet kannst du vorgeben. alternativ, wenn Excel schwierig umzusetzen ist, kannst du auch ein anderes Format festlegen. z.b. yaml.

neben dem Script liegt ein .env File wo die Zugangsdaten zu meiner ccu3 hinterlegt werden. erstelle eine .env.template

das Script liest die Daten ein und setzt sie bei den bwth geräten auf der ccu3. nur wenn sich tatsächlich werte geändert haben sollen die Werte gesetzt und gespeichert werden. hintergrund ist, die bwth geräte blinken bei jedem speichern und das soll nur wenn sich was geändert hat.