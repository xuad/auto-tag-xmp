# Automatisches RAW-Tagging mit Ollama und XMP

Windows-Anleitung für `tag_photos.py` und `auto_tag.bat` mit Python, Ollama, Qwen 3.5 und ExifTool.

## Überblick

Dieser Workflow erzeugt mithilfe eines lokal über Ollama bereitgestellten KI-Modells Stichwörter für deine Fotos und schreibt sie in XMP-Sidecar-Dateien. Anschließend kannst du die Stichwörter in Adobe Lightroom Classic übernehmen.

Die RAW-Datei wird dabei nicht verändert. Das Python-Skript extrahiert lediglich das eingebettete Vorschaubild aus der RAW-Datei und verwendet dieses für die Bildanalyse. Die erzeugten Tags werden ausschließlich in die zugehörigen XMP-Dateien geschrieben.

Der Ablauf:

```text
RAW-Datei → eingebettetes Vorschaubild extrahieren → KI-Bildanalyse
         → Stichwörter erzeugen → XMP-Datei aktualisieren
         → Metadaten in Lightroom Classic einlesen
```

| Bestandteil | Aufgabe |
|---|---|
| `auto_tag.bat` | Startet den Workflow unter Windows. |
| `tag_photos.py` | Steuert Vorschau-Extraktion, Modellanfrage und Schreiben der Tags. |
| Python 3.10+ | Führt das Python-Skript aus. |
| Ollama | Stellt das KI-Modell lokal bereit. |
| `qwen3.5:9b` | Analysiert das extrahierte Vorschaubild und erzeugt Stichwörter. |
| ExifTool | Extrahiert Bild-/Metadaten bzw. schreibt die XMP-Metadaten entsprechend dem Skript. |
| Lightroom Classic | Übernimmt die extern geschriebenen Stichwörter in den Katalog. |

Die Vorschau-Extraktion und das ausschließliche Schreiben in XMP beschreiben das vorgesehene Skriptverhalten. Die Skripte selbst sind dieser Anleitung nicht beigefügt. Details wie unterstützte Formate, rekursive Suche, Python-Abhängigkeiten und Behandlung vorhandener Keywords müssen zur tatsächlichen Implementierung passen.

## 1. Voraussetzungen und Sicherung

- Windows sowie eine dazu passende Python- und Ollama-Version.
- Python 3.10 oder neuer; vorzugsweise eine aktuell unterstützte Version, die mit den Skript-Abhängigkeiten kompatibel ist.
- Ollama mit dem heruntergeladenen Modell `qwen3.5:9b`.
- ExifTool für Windows.
- Die Projektdateien `tag_photos.py` und `auto_tag.bat`.
- Adobe Lightroom Classic für den beschriebenen Katalog-/XMP-Workflow.
- Speicherplatz für Software, Modell und Sicherungen; Internetzugang für die Downloads.

Die Geschwindigkeit hängt unter anderem von CPU, GPU, RAM/VRAM und Bildanzahl ab.

> Teste zuerst mit einer kleinen Kopie deiner RAW-Dateien und der zugehörigen Sidecars. Sichere auch den Lightroom-Katalog. Die RAW-Dateien bleiben bei diesem Workflow unverändert, XMP-Dateien werden jedoch aktualisiert und können neben Tags weitere Metadaten und Entwicklungseinstellungen enthalten.

## 2. Python installieren

Download: <https://www.python.org/downloads/windows/>

Windows-Dokumentation: <https://docs.python.org/3/using/windows.html>

1. Lade Python über die offizielle Website herunter. Verwende je nach angebotenem Installationsweg den Python Install Manager oder einen klassischen Windows-Installer.
2. Installiere eine Python-Laufzeit mit Version 3.10 oder neuer.
3. Aktiviere beim klassischen Installer, falls angeboten, `Add python.exe to PATH` bzw. `Add Python to PATH`.
4. Öffne nach der Installation eine neue Eingabeaufforderung.
5. Prüfe die Version:

```bat
python --version
```

Alternativ, wenn der Python-Launcher verfügbar ist:

```bat
py --version
```

Ermittle den vollständigen Interpreterpfad für die spätere Batch-Konfiguration:

```bat
python -c "import sys; print(sys.executable)"
```

Falls nur `py` funktioniert, verwende `py -c "import sys; print(sys.executable)"`.

### Python-Abhängigkeiten

Zusätzliche Pakete hängen von den Imports in `tag_photos.py` ab. Wenn das Projekt eine `requirements.txt` enthält, installiere diese mit demselben Interpreter, den später die Batch-Datei verwendet:

```bat
"C:\Pfad\zu\Python\python.exe" -m pip install -r "X:\path-to-auto-tag-xmp\requirements.txt"
```

Ohne Paketliste lässt sich keine vollständige, verifizierte Installationszeile angeben. Die Ollama-Anwendung installiert nicht automatisch die Python-Pakete des Skripts.

## 3. Ollama unter Windows installieren

Download: <https://ollama.com/download/windows>

Windows-Anleitung: <https://docs.ollama.com/windows>

1. Lade `OllamaSetup.exe` herunter.
2. Starte die Installation und folge den Anweisungen.
3. Starte Ollama, falls es noch nicht läuft.
4. Öffne eine neue Eingabeaufforderung und prüfe:

```bat
ollama --version
```

Ollama muss während des Taggings erreichbar bleiben.

### Modell installieren

```bat
ollama pull qwen3.5:9b
ollama list
```

Optionaler Starttest:

```bat
ollama run qwen3.5:9b
```

Mit `/bye` verlässt du die interaktive Sitzung. Dieser Test prüft den Modellstart, nicht die komplette Vorschau- und XMP-Verarbeitung.

Modellseite: <https://ollama.com/library/qwen3.5:9b>

Falls das Skript einen Modellnamen konfiguriert, muss dieser ebenfalls `qwen3.5:9b` lauten. Der Download allein ändert die Skriptkonfiguration nicht.

## 4. ExifTool installieren

Download: <https://exiftool.org/>

Installationsanleitung: <https://www.exiftool.org/install.html>

1. Lade das passende Windows-Executable-ZIP herunter.
2. Entpacke das vollständige Archiv, beispielsweise nach `C:\Tools\ExifTool`.
3. Benenne `exiftool(-k).exe` in `exiftool.exe` um.
4. Belasse den Ordner `exiftool_files` direkt neben der EXE; verschiebe nicht nur die EXE allein.
5. Prüfe die Installation:

```bat
"C:\Tools\ExifTool\exiftool.exe" -ver
```

Beispielstruktur:

```text
C:\Tools\ExifTool\
├── exiftool.exe
└── exiftool_files\
```

Blende Dateinamenerweiterungen im Explorer ein, damit nicht versehentlich `exiftool.exe.exe` entsteht.

### Unerwünschte ENTER-Pausen vermeiden

Die Option `-k` lässt ExifTool vor dem Beenden auf eine Eingabe warten. Für einen automatischen Durchlauf ist das unerwünscht. Wenn wiederholt `-- press ENTER --` erscheint, prüfe den EXE-Dateinamen und ob das Skript ausdrücklich `-k` übergibt.

Ein PATH-Eintrag ist nicht erforderlich, wenn das Skript den vollständigen ExifTool-Pfad verwendet.

## 5. `tag_photos.py` konfigurieren

Öffne die Datei in einem Texteditor und passe die vorhandenen Einstellungen an. Beispielwerte:

```python
EXIFTOOL_PATH = r"C:\Tools\ExifTool\exiftool.exe"
RAW_FILE_EXTENSION = ".NEF"
MAX_KEYWORDS = 20
KI_TAG = "ki-tag"
SKIP_IF_KI_TAG_EXISTS = True
```

Die Beispiele ersetzen nicht das vollständige Skript.

### `EXIFTOOL_PATH`

Vollständiger Pfad zur umbenannten `exiftool.exe`. Das `r` vor dem Python-String erleichtert die Verwendung von Windows-Backslashes.

### `RAW_FILE_EXTENSION`

Dateiendung deiner RAW-Dateien. Passe diesen Wert an die Dateien an, die du verarbeiten möchtest.

Beispiel für Nikon-NEF-Dateien:

```python
RAW_FILE_EXTENSION = ".NEF"
```

Weitere mögliche Dateiendungen sind beispielsweise `.CR2`, `.CR3` oder `.ARW`. Die Endung auszuwählen ist jedoch keine Garantie dafür, dass die verwendete Vorschau-Extraktion das jeweilige Format unterstützt.

Übernimm die vom vorhandenen Skript erwartete Schreibweise, insbesondere bezüglich führendem Punkt und Groß-/Kleinschreibung. Das Beispiel verwendet einen führenden Punkt. Mehrere Endungen lassen sich nur dann gemeinsam angeben, wenn der Code dies unterstützt; eine kommaseparierte Zeichenkette funktioniert nicht automatisch.

Wenn keine Bilder gefunden werden, prüfe diese Einstellung zusammen mit dem tatsächlich verarbeiteten Ordner.

### `MAX_KEYWORDS`

Gewünschte maximale Zahl erzeugter inhaltlicher Stichwörter, beispielsweise `20`. Kleinere Werte halten die Verschlagwortung kompakt, größere erlauben mehr Details.

Prüfe im Code, ob die Grenze nach der Modellantwort durchgesetzt oder nur im Prompt angefordert wird. Ob Marker und vorhandene Keywords mitzählen, hängt ebenfalls von der Implementierung ab.

### `KI_TAG`

Zusätzliches Kennzeichen für bereits bearbeitete Bilder, beispielsweise `ki-tag`. Es dient als Verarbeitungsmarkierung, nicht als Motivbeschreibung.

Wähle einen möglichst eindeutigen Wert. Änderst du ihn später, erkennt die Skip-Logik alte Markierungen möglicherweise nicht mehr.

### `SKIP_IF_KI_TAG_EXISTS`

| Wert | Bedeutung und Einsatz |
|---|---|
| `True` | Überspringt Bilder mit dem konfigurierten KI-Marker. Sinnvoll für wiederholte Läufe und das Fortsetzen unterbrochener Durchgänge. Vermeidet unnötige Modellanfragen. |
| `False` | Der KI-Marker verhindert die Verarbeitung nicht. Sinnvoll zum erneuten Taggen nach Änderungen an Prompt, Modell oder Keyword-Limit. |

`False` bedeutet nicht automatisch, dass alte Keywords gelöscht werden. Ob neue Tags ergänzt, ersetzt oder dedupliziert werden, legt der Schreibcode fest. Teste das vor einem erneuten Gesamtdurchlauf.

`True` ist außerdem keine Qualitätsprüfung: Das Vorhandensein des Markers beweist nicht, dass alle Stichwörter korrekt sind.

### `PROMPT`

Passe den bestehenden Prompt an deine Motive und die gewünschte Sprache an. Inhaltliches Beispiel:

```text
Analysiere das Bild und erzeuge präzise deutsche Stichwörter.
Bevorzuge klar sichtbare Motive, Objekte, Architektur, Landschaft und Lichtstimmung.
Vermeide doppelte Begriffe und unbelegte Vermutungen.
Nenne konkrete Orte, Gebäude oder Personen nur bei sicherer Erkennung.
Halte die im Skript vorgegebene maximale Stichwortanzahl ein.
```

Bewahre das vom Skript erwartete Ausgabeformat, zum Beispiel JSON oder eine kommaseparierte Liste. Behalte vorhandene Platzhalter und deren Formatierung bei, sofern du nicht auch den Parser bzw. Code anpasst.

## 6. `auto_tag.bat` konfigurieren

```bat
set "SCRIPT_DIR=X:\path-to-auto-tag-xmp"
set "PYTHON=C:\Pfad\zu\Python\python.exe"
set "SCRIPT=%SCRIPT_DIR%\tag_photos.py"
```

| Variable | Bedeutung |
|---|---|
| `SCRIPT_DIR` | Fester Projektordner mit `tag_photos.py`. |
| `PYTHON` | Vollständiger Pfad zum installierten Python-Interpreter mit den benötigten Paketen. |
| `SCRIPT` | Aus `SCRIPT_DIR` zusammengesetzter Pfad zur Python-Datei. |

Diese Pfade müssen zu deinem System passen. Python ist normalerweise nicht im Projektordner installiert.

Die Schreibweise `set "NAME=Wert"` verhindert versehentliche Leerzeichen am Wertende. Beim eigentlichen Programmaufruf müssen Pfade ebenfalls korrekt in Anführungszeichen stehen.

### Fehlerhafte Python-Zeile korrigieren

Falsch:

```bat
set "PYTHON=%SCRIPT_DIR%=python.exe"
```

Hier steht zwischen Ordner und Dateiname ein Gleichheitszeichen statt eines Backslashs. Nur wenn eine vollständige Python-Installation tatsächlich im Projektordner liegt, wäre Folgendes passend:

```bat
set "PYTHON=%SCRIPT_DIR%\python.exe"
```

Bei einer normalen Installation verwende den zuvor ermittelten vollständigen Interpreterpfad. Kopiere nicht einfach nur `python.exe` in das Projekt.

### Projekt- und Bilderordner unterscheiden

Lass das Projekt an seinem festen Ort und kopiere die konfigurierte Batch-Datei in den übergeordneten Ordner deiner Bilder:

```text
X:\path-to-auto-tag-xmp\
└── tag_photos.py

D:\Fotos-Test\
├── auto_tag.bat
└── Dresden\
    ├── Z81_9233.NEF
    └── Z81_9233.xmp
```

Das Kopieren der Batch-Datei allein legt noch nicht den Eingabeordner des Python-Skripts fest. Die bestehende Batch-Datei muss ihren eigenen Ablageort als Bildwurzel verwenden oder ihn korrekt an das Skript übergeben. Unterordner werden nur bei implementierter rekursiver Suche verarbeitet. Ohne Quellcode lassen sich keine zuverlässigen Argumentnamen angeben.

## 7. Lightroom Classic vorbereiten

Diese Anleitung bezieht sich auf Lightroom Classic, nicht auf die cloudbasierte Lightroom-Anwendung.

1. Sichere RAW-Dateien, Sidecars und Lightroom-Katalog.
2. Öffne `Bearbeiten > Katalogeinstellungen`.
3. Wechsle zum Reiter `Metadaten`.
4. Aktiviere `Änderungen automatisch in XMP speichern` (`Automatically Write Changes Into XMP`; Bezeichnung je nach Version).
5. Wähle die Testbilder aus und speichere den aktuellen Stand ausdrücklich mit `Metadaten > Metadaten in Datei speichern`.
6. Warte auf den Abschluss und prüfe, ob passende XMP-Dateien vorhanden sind.

```text
Z81_9233.NEF
Z81_9233.xmp
```

Lightroom speichert Änderungen zunächst im Katalog. Kontrolliere deshalb, dass der aktuelle Stand tatsächlich auf dem Datenträger angekommen ist. Bei DNG und anderen Formaten kann Lightroom XMP direkt in die Bilddatei schreiben; diese Anleitung beschreibt einen Sidecar-Workflow mit unveränderten RAW-Dateien beim Tagging.

Schließe Lightroom vor dem Tagging möglichst, nachdem alle Schreibvorgänge beendet sind. Das vermeidet konkurrierende Metadatenänderungen.

## 8. Jetzt taggen

1. Erstelle einen kleinen Testordner mit Kopien einiger RAW-Dateien und ihrer XMP-Sidecars.
2. Kopiere die konfigurierte `auto_tag.bat` in den übergeordneten Bilderordner.
3. Prüfe Projekt-, Python- und ExifTool-Pfade sowie `RAW_FILE_EXTENSION`.
4. Stelle sicher, dass Ollama läuft und `qwen3.5:9b` vorhanden ist.
5. Kontrolliere Prompt, Keyword-Limit, Marker und Skip-Einstellung.
6. Doppelklicke auf `auto_tag.bat`.
7. Beobachte die Ausgabe und lasse den Durchlauf vollständig abschließen.

Das Skript extrahiert das Vorschaubild, lässt es analysieren und schreibt die Tags in die XMP-Datei. Die RAW-Datei selbst bleibt unverändert. Ein kleiner Probelauf zeigt, ob Sprache, Detailgrad und Schreibverhalten zu deinen Anforderungen passen.

### Beispielausgabe und Screenshot

Der zur Dokumentation gehörende Screenshot `tagging-example.jpg` zeigt einen laufenden Durchgang mit Fortschrittszähler, NEF-Dateinamen, erzeugten Stichwörtern und XMP-Dateinamen. Gekürztes Beispiel:

```text
[6328/30216] Z81_9234.NEF
    1 image files updated
Tags: Dresden, Frauenkirche, Kuppel, Turm, Glockenturm,
      Barockarchitektur, ... , ki-tag
XMP: Z81_9234.xmp
```

Die generische ExifTool-Meldung `1 image files updated` bedeutet in diesem Workflow nicht, dass die RAW-Datei geändert wird: Die Tags werden in das XMP-Sidecar geschrieben.

Im Screenshot erscheinen außerdem `-- press ENTER --`-Aufforderungen. Für einen unbeaufsichtigten Ablauf solltest du die unter ExifTool beschriebene `-k`-Ursache prüfen.

## 9. Tags in Lightroom Classic laden

1. Öffne Lightroom Classic nach Abschluss des Taggings.
2. Wähle im Bibliotheksmodul die bearbeiteten Bilder aus.
3. Wähle `Metadaten > Metadaten aus Datei lesen` (`Metadata > Read Metadata From File`).
4. Prüfe und bestätige gegebenenfalls Rückfragen.
5. Kontrolliere die Stichwörter und den Marker an mehreren Bildern.

Achtung: Dieser Vorgang kann mehr als Keywords einlesen, einschließlich anderer Metadaten und Entwicklungsinformationen. Nicht zuvor nach XMP geschriebene Katalogänderungen können verloren gehen. Deshalb vorher speichern und sichern.

Wähle nach dem Tagging nicht versehentlich „Metadaten in Datei speichern“: Diese Richtung schreibt den Katalogstand auf den Datenträger und kann die extern hinzugefügten Tags überschreiben.

## 10. Wiederholen und Qualität prüfen

- Für normale Folgeläufe `SKIP_IF_KI_TAG_EXISTS = True` verwenden.
- Für bewusstes Neu-Taggen `False` setzen und zuerst wenige Kopien testen.
- Danach bei Bedarf wieder auf `True` wechseln.
- KI-Stichwörter stichprobenartig kontrollieren; konkrete Orte und Gebäude können falsch erkannt werden.
- Prüfen, ob bestehende Keywords und Entwicklungsdaten erhalten bleiben.
- Beachten, dass die KI die eingebettete Vorschau analysiert, nicht unmittelbar die vollständigen RAW-Sensordaten.

## 11. Häufige Probleme

| Problem | Prüfen / Lösung |
|---|---|
| Python wird nicht gefunden | Installation prüfen und vollständigen Interpreterpfad in `PYTHON` eintragen. |
| `ModuleNotFoundError` | Fehlendes Paket im tatsächlich gestarteten Interpreter installieren. |
| Ollama nicht erreichbar | Anwendung starten; bei bewusst manuellem Serverbetrieb `ollama serve` nur verwenden, wenn noch kein Server läuft. |
| Modell fehlt | `ollama pull qwen3.5:9b` ausführen und Skript-Modellnamen prüfen. |
| ExifTool startet nicht | Pfad, EXE-Dateiname und benachbarten Ordner `exiftool_files` kontrollieren. |
| Nach jeder Datei ENTER nötig | `(-k)` im Dateinamen und explizite `-k`-Argumente prüfen. |
| Keine Bilder gefunden | `RAW_FILE_EXTENSION`, Bildwurzel, Groß-/Kleinschreibung und rekursive Suche prüfen. |
| Vorschau kann nicht extrahiert werden | Formatunterstützung, vorhandene eingebettete Vorschau und Extraktionscode prüfen. |
| Viele Bilder werden übersprungen | `KI_TAG` und `SKIP_IF_KI_TAG_EXISTS` kontrollieren. |
| Tags fehlen in Lightroom | Richtige Bilder wählen, Sidecars prüfen und „Metadaten aus Datei lesen“ verwenden. |
| Neue Tags werden überschrieben | Paralleles Schreiben durch Lightroom und Synchronisationsrichtung prüfen. |

## Checkliste vor dem großen Durchlauf

- [ ] RAW-Dateien, Sidecars und Katalog gesichert.
- [ ] Python 3.10+ und tatsächliche Skript-Abhängigkeiten installiert.
- [ ] Ollama läuft; `qwen3.5:9b` ist vorhanden.
- [ ] ExifTool funktioniert ohne unerwünschte Eingabepausen.
- [ ] `RAW_FILE_EXTENSION` entspricht den zu verarbeitenden Dateien.
- [ ] Python- und Batch-Konfiguration geprüft.
- [ ] Aktuelle Lightroom-Metadaten vorab auf den Datenträger geschrieben.
- [ ] Testlauf und Einlesen in Lightroom erfolgreich.
- [ ] Vorhandene Keywords und Entwicklungsdaten kontrolliert.
