# Automatic RAW Photo Tagging with Ollama and XMP

Windows setup and usage guide for `tag_photos.py` and `auto_tag.bat`, using Python, Ollama, Qwen 3.5, and ExifTool.

## Overview

This workflow uses an AI model served locally through Ollama to generate descriptive photo keywords and write them to XMP sidecar files. Adobe Lightroom Classic can then import those keywords into its catalog.

The RAW file is not modified. The Python script only extracts the embedded preview image from the RAW file and uses that preview for image analysis. Generated tags are written exclusively to the corresponding XMP files.

```text
RAW file → extract embedded preview → AI image analysis
         → generate keywords → update XMP sidecar
         → read metadata into Lightroom Classic
```

| Component | Purpose |
|---|---|
| `auto_tag.bat` | Launches the workflow on Windows. |
| `tag_photos.py` | Coordinates preview extraction, model requests, and tag writing. |
| Python 3.10+ | Runs the Python script. |
| Ollama | Serves the local AI model. |
| `qwen3.5:9b` | Analyzes the extracted preview and generates keywords. |
| ExifTool | Extracts image/metadata content and writes XMP metadata as implemented by the script. |
| Lightroom Classic | Reads externally written keywords into the catalog. |

Preview extraction and XMP-only writing describe the intended script behavior. The actual scripts are not included with this guide. Supported formats, recursive scanning, Python dependencies, and handling of existing keywords must match the implementation.

## 1. Requirements and backups

- Windows and compatible Python and Ollama versions.
- Python 3.10 or newer; preferably a currently supported version compatible with the dependencies.
- Ollama with the downloaded `qwen3.5:9b` model.
- ExifTool for Windows.
- The project files `tag_photos.py` and `auto_tag.bat`.
- Adobe Lightroom Classic for the catalog/XMP workflow described here.
- Disk space for software, model files, and backups; internet access for downloads.

Processing speed depends on CPU, GPU, available RAM/VRAM, and image count.

> Start with a small backup copy of your RAW photos and their sidecars. Back up your Lightroom catalog too. Although this workflow leaves RAW files unchanged, it updates XMP files, which may contain development settings and other metadata in addition to keywords.

## 2. Install Python

Download: <https://www.python.org/downloads/windows/>

Windows documentation: <https://docs.python.org/3/using/windows.html>

1. Download Python from the official website. Use the Python Install Manager or a traditional Windows installer, depending on the installation options provided.
2. Install a Python runtime version 3.10 or newer.
3. With a traditional installer, enable `Add python.exe to PATH` or `Add Python to PATH` when offered.
4. Open a new Command Prompt after installation.
5. Verify the version:

```bat
python --version
```

Alternatively, if the Python launcher is available:

```bat
py --version
```

Find the full interpreter path for the batch configuration:

```bat
python -c "import sys; print(sys.executable)"
```

If only `py` works, use `py -c "import sys; print(sys.executable)"` instead.

### Python dependencies

Additional packages depend on the imports in `tag_photos.py`. If the project supplies `requirements.txt`, install it using the same interpreter the batch file will launch:

```bat
"C:\Path\To\Python\python.exe" -m pip install -r "X:\path-to-auto-tag-xmp\requirements.txt"
```

Without the dependency list, a complete verified package installation command cannot be supplied. Installing the Ollama application does not automatically install Python packages required by the script.

## 3. Install Ollama on Windows

Download: <https://ollama.com/download/windows>

Windows documentation: <https://docs.ollama.com/windows>

1. Download `OllamaSetup.exe`.
2. Run the installer and follow the instructions.
3. Start Ollama if it is not already running.
4. Open a new Command Prompt and check:

```bat
ollama --version
```

Ollama must remain reachable during tagging.

### Download the model

```bat
ollama pull qwen3.5:9b
ollama list
```

Optional startup test:

```bat
ollama run qwen3.5:9b
```

Exit the interactive session with `/bye`. This tests model startup, not the complete preview-extraction and XMP pipeline.

Model page: <https://ollama.com/library/qwen3.5:9b>

If the script has a model-name setting, it must also specify `qwen3.5:9b`. Downloading the model does not update the script configuration.

## 4. Install ExifTool

Download: <https://exiftool.org/>

Installation instructions: <https://www.exiftool.org/install.html>

1. Download the appropriate Windows executable ZIP archive.
2. Extract the complete archive, for example to `C:\Tools\ExifTool`.
3. Rename `exiftool(-k).exe` to `exiftool.exe`.
4. Keep the `exiftool_files` directory next to the EXE; do not move the executable alone.
5. Verify the installation:

```bat
"C:\Tools\ExifTool\exiftool.exe" -ver
```

Example layout:

```text
C:\Tools\ExifTool\
├── exiftool.exe
└── exiftool_files\
```

Enable file name extensions in Explorer to avoid accidentally creating `exiftool.exe.exe`.

### Avoid unwanted ENTER prompts

The `-k` option makes ExifTool wait for keyboard input before exiting. This is undesirable for automated processing. If `-- press ENTER --` appears repeatedly, check the executable name and whether the script explicitly passes `-k`.

A Windows PATH entry is optional when the script uses the full ExifTool path.

## 5. Configure `tag_photos.py`

Open the file in a text editor and update the existing settings. Example values:

```python
EXIFTOOL_PATH = r"C:\Tools\ExifTool\exiftool.exe"
RAW_FILE_EXTENSION = ".NEF"
MAX_KEYWORDS = 20
KI_TAG = "ki-tag"
SKIP_IF_KI_TAG_EXISTS = True
```

These examples do not replace the complete script.

### `EXIFTOOL_PATH`

The full path to the renamed `exiftool.exe`. The Python string's `r` prefix makes Windows backslashes convenient to use.

### `RAW_FILE_EXTENSION`

The file extension of your RAW photos. Set this value to match the files you want to process.

Example for Nikon NEF files:

```python
RAW_FILE_EXTENSION = ".NEF"
```

Other possible extensions include `.CR2`, `.CR3`, and `.ARW`. Selecting an extension does not guarantee that the preview-extraction implementation supports that format.

Follow the syntax expected by the existing script, particularly the leading dot and letter case. This example includes a leading dot. Multiple extensions can only be specified together if the code supports that feature; a comma-separated string does not automatically enable it.

If no images are found, check this setting as well as the actual input directory.

### `MAX_KEYWORDS`

The desired maximum number of generated descriptive keywords, for example `20`. Lower values keep the result compact; higher values allow more detail.

Check whether the code enforces the limit after receiving the response or only requests it in the prompt. Whether the marker and existing keywords count toward the limit is also implementation-dependent.

### `KI_TAG`

An additional keyword identifying processed images, such as `ki-tag`. It is a processing marker rather than a description of the subject.

Choose a distinctive value. Changing it later may prevent the skip logic from recognizing older markers.

### `SKIP_IF_KI_TAG_EXISTS`

| Value | Meaning and use |
|---|---|
| `True` | Skip images containing the configured AI marker. Useful for repeated runs and resuming interrupted work without unnecessary model requests. |
| `False` | Do not skip images merely because the marker exists. Useful for deliberate re-tagging after changing the prompt, model, or keyword limit. |

`False` does not automatically delete old keywords. Appending, replacing, and deduplicating depend on the writing code. Test this before reprocessing an entire library.

Likewise, `True` is not a quality check: the presence of a marker does not prove that the keywords are correct.

### `PROMPT`

Adapt the existing prompt to your subjects and preferred language. Example content instructions:

```text
Analyze the image and generate precise English keywords.
Prioritize clearly visible subjects, objects, architecture, landscape, and lighting.
Avoid duplicate terms and unsupported guesses.
Name specific places, buildings, or people only when identification is reliable.
Respect the maximum keyword count configured by the script.
```

Preserve the output format expected by the script, such as JSON or a comma-separated list. Keep existing placeholders and formatting unless you also update the parser or code.

## 6. Configure `auto_tag.bat`

```bat
set "SCRIPT_DIR=X:\path-to-auto-tag-xmp"
set "PYTHON=C:\Path\To\Python\python.exe"
set "SCRIPT=%SCRIPT_DIR%\tag_photos.py"
```

| Variable | Purpose |
|---|---|
| `SCRIPT_DIR` | Fixed project directory containing `tag_photos.py`. |
| `PYTHON` | Full path to the installed Python interpreter with the required packages. |
| `SCRIPT` | Path to the Python script assembled from `SCRIPT_DIR`. |

These paths must match your system. Python is not normally installed in the project directory.

The `set "NAME=value"` syntax prevents accidental trailing spaces. Paths must also be quoted correctly when invoking the program.

### Correct the Python path line

Incorrect:

```bat
set "PYTHON=%SCRIPT_DIR%=python.exe"
```

This places an equals sign between the directory and filename instead of a backslash. Only if a complete Python installation actually exists in the project directory would this be appropriate:

```bat
set "PYTHON=%SCRIPT_DIR%\python.exe"
```

For a normal installation, use the full interpreter path obtained earlier. Do not simply copy `python.exe` into the project.

### Distinguish the project directory from the photo directory

Keep the project in its fixed location and copy the configured batch file into the parent directory containing your photos:

```text
X:\path-to-auto-tag-xmp\
└── tag_photos.py

D:\Photo-Test\
├── auto_tag.bat
└── Dresden\
    ├── Z81_9233.NEF
    └── Z81_9233.xmp
```

Copying the batch file does not, by itself, determine the Python script's input directory. The existing batch file must use its own location as the photo root or pass it to the script correctly. Subfolders are processed only if recursive scanning is implemented. Exact argument names cannot be documented reliably without the source code.

## 7. Prepare Lightroom Classic

These instructions apply to Lightroom Classic, not the cloud-based Lightroom application.

1. Back up your RAW files, sidecars, and Lightroom catalog.
2. Open `Edit > Catalog Settings`.
3. Select the `Metadata` tab.
4. Enable `Automatically Write Changes Into XMP`.
5. Select the test images and explicitly run `Metadata > Save Metadata To File` to save their current state.
6. Wait for writing to finish and verify the matching XMP files.

```text
Z81_9233.NEF
Z81_9233.xmp
```

Lightroom initially stores changes in its catalog. Check that the current state has actually reached the disk. For DNG and some other formats, Lightroom may write XMP inside the image file; this guide describes a sidecar workflow in which tagging leaves RAW files unchanged.

Preferably close Lightroom before tagging once all writes have finished. This avoids competing metadata changes.

## 8. Start tagging

1. Create a small test directory with copies of several RAW files and their XMP sidecars.
2. Copy the configured `auto_tag.bat` into the parent photo directory.
3. Check the project, Python, and ExifTool paths, plus `RAW_FILE_EXTENSION`.
4. Confirm that Ollama is running and `qwen3.5:9b` is available.
5. Review the prompt, keyword limit, marker, and skip setting.
6. Double-click `auto_tag.bat`.
7. Monitor the output and allow processing to finish.

The script extracts the preview, analyzes it, and writes the tags to the XMP file. The RAW file itself remains unchanged. A small trial run helps confirm that keyword language, detail level, and writing behavior match your needs.

### Example output and screenshot

The documentation's example screenshot, `tagging-example.jpg`, shows a running job with a progress counter, NEF filenames, generated keywords, and XMP filenames. Abbreviated example:

```text
[6328/30216] Z81_9234.NEF
    1 image files updated
Tags: Dresden, Frauenkirche, Kuppel, Turm, Glockenturm,
      Barockarchitektur, ... , ki-tag
XMP: Z81_9234.xmp
```

In this workflow, ExifTool's generic `1 image files updated` message does not mean the RAW file is modified: the tags are written to the XMP sidecar.

The screenshot also contains `-- press ENTER --` prompts. For unattended operation, investigate the `-k` behavior explained in the ExifTool section.

## 9. Load the tags into Lightroom Classic

1. Open Lightroom Classic after tagging has finished.
2. Select the processed photos in the Library module.
3. Choose `Metadata > Read Metadata From File`.
4. Review and confirm any prompts.
5. Check the keywords and marker on several images.

Warning: Reading metadata from disk can import more than keywords, including other metadata and development settings. Catalog changes not previously written to XMP can be lost. Save and back up first.

Do not accidentally choose `Save Metadata To File` after tagging: that direction writes catalog data to disk and may overwrite the externally added keywords.

## 10. Repeat and review quality

- Use `SKIP_IF_KI_TAG_EXISTS = True` for normal subsequent runs.
- Use `False` for deliberate re-tagging, starting with a few copies.
- Switch back to `True` afterward if appropriate.
- Spot-check AI keywords; specific buildings and locations may be misidentified.
- Verify that existing keywords and development settings are preserved.
- Remember that the AI analyzes the embedded preview, not the full RAW sensor data directly.

## 11. Troubleshooting

| Problem | Checks / solution |
|---|---|
| Python is not found | Check installation and set `PYTHON` to the full interpreter path. |
| `ModuleNotFoundError` | Install the missing dependency into the interpreter actually being launched. |
| Ollama is unreachable | Start the application; use `ollama serve` for intentional manual operation only if no server is already running. |
| Model is missing | Run `ollama pull qwen3.5:9b` and check the script's model name. |
| ExifTool does not start | Check the path, EXE filename, and adjacent `exiftool_files` directory. |
| ENTER required after every file | Check for `(-k)` in the filename and explicit `-k` arguments. |
| No photos are found | Check `RAW_FILE_EXTENSION`, photo root, letter case, and recursive scanning. |
| Preview extraction fails | Check format support, the embedded preview, and the extraction code. |
| Many images are skipped | Check `KI_TAG` and `SKIP_IF_KI_TAG_EXISTS`. |
| Tags are missing in Lightroom | Select the correct photos, check sidecars, and use `Read Metadata From File`. |
| New tags are overwritten | Check concurrent Lightroom writes and synchronization direction. |

## Checklist before a full-library run

- [ ] RAW files, sidecars, and catalog backed up.
- [ ] Python 3.10+ and the actual script dependencies installed.
- [ ] Ollama running; `qwen3.5:9b` available.
- [ ] ExifTool working without unwanted input pauses.
- [ ] `RAW_FILE_EXTENSION` matches the files to process.
- [ ] Python and batch settings checked.
- [ ] Current Lightroom metadata written to disk beforehand.
- [ ] Test run and Lightroom metadata import successful.
- [ ] Existing keywords and development settings checked.
