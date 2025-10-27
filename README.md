# dcm2niix4ct

A simple wrapper for dcm2niix that adds BIDS-compliant CT metadata to JSON sidecars.

## Installation

```bash
pip install git+https://github.com/ChristianHinge/dcm2niix4ct.git
```

Or clone and install:

```bash
git clone https://github.com/ChristianHinge/dcm2niix4ct.git
cd dcm2niix4ct
pip install -e .
```

## Usage

```bash
dcm2niix4ct /path/to/dicom/folder
```

Works exactly like dcm2niix, but automatically extracts CT metadata (tube voltage, dose, exposure, etc.) and adds it to the JSON sidecar.
