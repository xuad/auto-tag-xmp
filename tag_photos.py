import argparse
import base64
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import timedelta
from pathlib import Path
from ollama import chat
from PIL import Image

EXIFTOOL_PATH = Path(r"X:\path-to-exiftool.exe")
RAW_FILE_EXTENSION = ".nef"
MODEL = "qwen3.5:9b"
MAX_KEYWORDS = 14
KI_TAG = "ki-tag"
SKIP_IF_KI_TAG_EXISTS = True
MAX_JSON_ATTEMPTS = 5
MAX_IMAGE_EDGE = 1024
MODEL_CONTEXT = 2048
MAX_OUTPUT_TOKENS = 256

EXIFTOOL = (
    os.environ.get("EXIFTOOL_PATH")
    or (str(EXIFTOOL_PATH) if EXIFTOOL_PATH.is_file() else None)
    or shutil.which("exiftool")
)
if not EXIFTOOL or not Path(EXIFTOOL).is_file():
    raise SystemExit(
        f"ExifTool wurde nicht unter {EXIFTOOL_PATH} gefunden. "
        "Setze EXIFTOOL_PATH oder füge ExifTool zum PATH hinzu."
    )

PROMPT = """Analysiere das Foto und erstelle deutsche Stichwörter.

Antworte ausschließlich mit gültigem JSON in diesem Format:
{
  "keywords": [],
  "caption": ""
}

Regeln:
- 10 bis 14 Stichwörter
- Deutsch, möglichst Singular, ohne Satzzeichen
- Gib nur Details an, die im Bild eindeutig oder mit hoher Sicherheit sichtbar sind
- Priorisiere wichtige sichtbare Motive:
  1. Tiere und Insekten mit erkennbarem deutschen Namen
  2. Pflanzen, Landschaftselemente und markante Orte
  3. Motiv und Aktivität
  4. Jahreszeit und Lichtstimmung nur bei hoher Sicherheit
- Bei Tieren: Verwende einen konkreten deutschen Namen, wenn das Tier eindeutig bestimmbar ist
  (z. B. "Rothirsch", "Rotfuchs", "Feldhase"). Nutze nur "Säugetier", "Vogel", "Insekt"
  oder "Schmetterling", wenn eine genauere Bestimmung unsicher ist
- Bei Insekten: Verwende "Schmetterling", "Libelle", "Biene", "Hummel", "Käfer",
  "Marienkäfer", "Heuschrecke", "Wespe" oder eine ähnliche eindeutige deutsche Artbezeichnung
- Bei Landschaften: Benenne sichtbare Landschaftsformen und Orte konkret, z. B.
  "Alpen", "Gebirge", "Tal", "Gipfel", "See", "Bach", "Fluss", "Wald", "Wiese",
  "Moor", "Düne", "Klippe", "Küste", "Hochebene", "Strand" oder "Heidelandschaft"
- Verwende einen genauen Ortsnamen nur bei sichtbaren Hinweisen wie Ortsschildern oder
  eindeutig identifizierbaren Landmarken. Nenne sonst den Landschafts- oder Regionstyp
- Klare Tags und kein Prosa
- Unterscheide zwischen Sonnenaufgang und Sonnenuntergang
- Keine erfundenen Personennamen oder Ortsnamen
- Folgende Tags sind verboten: "Foto", "Bild", "schön", "Fotografie", "Urlaub", "Urlaubsort", "Urlaubsstimmung", "Reise", "Reiseziel", "Reiseort"
- caption: ein kurzer, sachlicher deutscher Satz
"""

def get_raw_files(raw_folder: Path):
    return sorted(
        path
        for path in raw_folder.rglob("*")
        if path.is_file() and path.suffix.casefold() == RAW_FILE_EXTENSION
    )

def extract_preview(raw_file: Path, raw_folder: Path, preview_root: Path) -> Path:
    relative_parent = raw_file.parent.relative_to(raw_folder)
    preview_folder = preview_root / relative_parent
    preview_folder.mkdir(parents=True, exist_ok=True)
    preview = preview_folder / f"{raw_file.stem}.jpg"

    if not preview.exists():
        result = subprocess.run(
            [
                EXIFTOOL,
                "-b",
                "-PreviewImage",
                str(raw_file),
            ],
            input=b"\n",
            check=True,
            capture_output=True,
        )

        if not result.stdout:
            raise ValueError(f"Kein PreviewImage in {raw_file.name} gefunden")
        preview.write_bytes(result.stdout)

    return preview

def analyse_image(preview: Path) -> dict:
    with Image.open(preview) as image:
        image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        jpeg_buffer = io.BytesIO()
        image.save(jpeg_buffer, format="JPEG", quality=85, optimize=True)

    image_base64 = base64.b64encode(jpeg_buffer.getvalue()).decode("utf-8")

    for attempt in range(1, MAX_JSON_ATTEMPTS + 1):
        response = chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT + "\nDenke nicht laut. Gib nur das JSON aus.",
                    "images": [image_base64],
                }
            ],
            format="json",
            think=False,
            keep_alive="30m",
            options={
                "temperature": 0.1,
                "num_ctx": MODEL_CONTEXT,
                "num_predict": MAX_OUTPUT_TOKENS,
            },
        )

        text = response.message.content.strip()

        # JSON auch aus Markdown-Codeblöcken extrahieren
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                break
            except json.JSONDecodeError:
                pass

        if attempt < MAX_JSON_ATTEMPTS:
            print(f"  Kein gültiges JSON, neuer Versuch ({attempt + 1}/{MAX_JSON_ATTEMPTS})")
    else:
        raise ValueError(
            f"Nach {MAX_JSON_ATTEMPTS} Versuchen kein gültiges JSON erhalten; "
            f"Bild wird übersprungen. Letzte Antwort:\n{text}"
        )

    keywords = data.get("keywords", [])
    keywords = [str(k).strip() for k in keywords if str(k).strip()]
    keywords = list(dict.fromkeys(keywords))
    if not any(keyword.casefold() == KI_TAG for keyword in keywords):
        keywords = keywords[:MAX_KEYWORDS - 1] + [KI_TAG]
    else:
        keywords = keywords[:MAX_KEYWORDS]

    caption = str(data.get("caption", "")).strip()

    return {"keywords": keywords, "caption": caption}

def has_ki_tag(raw_file: Path) -> bool:
    xmp_file = raw_file.with_suffix(".xmp")
    if not xmp_file.exists():
        return False

    try:
        root = ET.parse(xmp_file).getroot()
    except ET.ParseError as error:
        raise ValueError(f"XMP-Datei ist kein gültiges XML: {xmp_file}: {error}") from error

    subject_tag = "{http://purl.org/dc/elements/1.1/}subject"
    subjects = [
        value.strip()
        for element in root.iter(subject_tag)
        for value in element.itertext()
        if value.strip()
    ]
    return any(subject.strip().casefold() == KI_TAG for subject in subjects)

def get_folder_tag(raw_file: Path) -> str:
    folder_name = raw_file.parent.name
    tag = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[-–—]\s*", "", folder_name).strip()
    return tag or folder_name

def write_xmp(raw_file: Path, result: dict) -> Path:
    xmp_file = raw_file.with_suffix(".xmp")

    args = [
        "-overwrite_original",
        "-XMP-dc:Subject=",
    ]

    for keyword in result["keywords"]:
        args += ["-XMP-dc:Subject=" + keyword]

    args.append("-XMP-dc:Description=")
    if result["caption"]:
        args += ["-XMP-dc:description=" + result["caption"]]

    args.append(str(xmp_file))

    with tempfile.TemporaryDirectory() as temp_dir:
        args_file = Path(temp_dir) / "exiftool.args"
        args_file.write_text("\n".join(args) + "\n", encoding="utf-8")
        subprocess.run(
            [
                EXIFTOOL,
                "-m",
                "-charset",
                "UTF8",
                "-charset",
                "filename=UTF8",
                "-@",
                str(args_file),
            ],
            input=b"\n",
            check=True,
        )

    return xmp_file

def main():
    parser = argparse.ArgumentParser(
        description="RAW-Dateien im angegebenen Ordner rekursiv verschlagworten."
    )
    parser.add_argument(
        "raw_folder",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Ordner mit RAW-Dateien (Standard: aktueller Ordner)",
    )
    raw_folder = parser.parse_args().raw_folder.resolve()
    if not raw_folder.is_dir():
        parser.error(f"Ordner existiert nicht: {raw_folder}")

    preview_folder = raw_folder / "_previews"
    start_time = time.perf_counter()
    raw_files = get_raw_files(raw_folder)
    print(f"Gefundene RAW-Dateien: {len(raw_files)}")
    successful = 0

    for index, raw_file in enumerate(raw_files, start=1):
        print(f"[{index}/{len(raw_files)}] {raw_file.name}")

        try:
            if SKIP_IF_KI_TAG_EXISTS and has_ki_tag(raw_file):
                print(f"  {KI_TAG} bereits in XMP, übersprungen.")
                continue

            preview = extract_preview(raw_file, raw_folder, preview_folder)
            result = analyse_image(preview)
            folder_tag = get_folder_tag(raw_file)
            if folder_tag and not any(
                keyword.casefold() == folder_tag.casefold()
                for keyword in result["keywords"]
            ):
                keywords = result["keywords"]
                reserved = [keyword for keyword in keywords if keyword.casefold() == KI_TAG]
                other_keywords = [
                    keyword for keyword in keywords if keyword.casefold() != KI_TAG
                ]
                result["keywords"] = (
                    other_keywords[:MAX_KEYWORDS - len(reserved) - 1]
                    + [folder_tag]
                    + reserved
                )
            xmp_file = write_xmp(raw_file, result)

            print(f"  Tags: {', '.join(result['keywords'])}")
            print(f"  XMP: {xmp_file.name}")
            successful += 1

        except Exception as error:
            print(f"  FEHLER: {error}")

    if preview_folder.exists():
        shutil.rmtree(preview_folder)
        print("Vorschauordner gelöscht.")

    elapsed = time.perf_counter() - start_time
    print(
        f"Fertig: {len(raw_files)} Bilder insgesamt, "
        f"{successful} erfolgreich, {len(raw_files) - successful} übersprungen."
    )
    print(f"Gesamtdauer: {timedelta(seconds=round(elapsed))}")

if __name__ == "__main__":
    main()