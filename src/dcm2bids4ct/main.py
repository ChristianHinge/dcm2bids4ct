"""
DICOM CT metadata extraction and BIDS JSON modification utilities.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from collections import defaultdict


def find_dicom_files(directory: str) -> List[str]:
    """
    Find all DICOM files in a directory (non-recursive).

    Args:
        directory: Path to the directory to search

    Returns:
        List of DICOM file paths
    """
    dicom_files = []

    # List all items in directory
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)

        # Skip if not a file
        if not os.path.isfile(filepath):
            continue

        # Check if it's a DICOM file by reading the header
        if is_dicom_file(filepath):
            dicom_files.append(filepath)

    return dicom_files


def is_dicom_file(filepath: str) -> bool:
    """Check if file is DICOM by looking for DICM magic number at byte 128."""
    with open(filepath, 'rb') as f:
        f.seek(128)
        return f.read(4) == b'DICM'


def is_ct_scan(dicom_files: List[str]) -> bool:
    """
    Check if DICOM files represent a CT scan.

    Args:
        dicom_files: List of DICOM file paths

    Returns:
        True if files are CT scans, False otherwise

    Raises:
        RuntimeError: If DICOM file cannot be read
    """
    if not dicom_files:
        return False

    import pydicom

    dcm = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)
    modality_element = dcm.get("Modality")

    if modality_element is None:
        return False

    # Handle both DataElement objects and plain values
    if hasattr(modality_element, 'value'):
        modality = modality_element.value
    else:
        modality = modality_element

    return modality == "CT"


def validate_ct_series(dicom_files: List[str]) -> None:
    """
    Validate that DICOM files represent a single CT series.

    Args:
        dicom_files: List of DICOM file paths

    Raises:
        ValueError: If files are not CT modality or contain multiple series
    """
    if not dicom_files:
        raise ValueError("No DICOM files found in directory")

    import pydicom

    # Check first file
    try:
        first_dcm = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)
    except Exception as e:
        raise ValueError(f"Failed to read DICOM file {dicom_files[0]}: {e}")

    # Get modality
    modality = first_dcm.get("Modality")
    if modality is None:
        raise ValueError("DICOM files do not contain Modality tag")

    modality_value = modality.value if hasattr(modality, "value") else str(modality)

    # Check if CT
    if modality_value != "CT":
        raise ValueError(f"DICOM modality is '{modality_value}', expected 'CT'")

    # Get series information from first file
    first_series_uid = first_dcm.get("SeriesInstanceUID")
    first_series_number = first_dcm.get("SeriesNumber")

    if first_series_uid is None:
        raise ValueError("DICOM files do not contain SeriesInstanceUID tag")

    first_series_uid_value = first_series_uid.value if hasattr(first_series_uid, "value") else str(first_series_uid)

    # Check all files belong to the same series
    unique_series = set()
    unique_series.add(first_series_uid_value)

    # Sample some files to check for consistency
    # For large datasets, we don't need to check every single file
    sample_size = min(len(dicom_files), 10)
    step = max(1, len(dicom_files) // sample_size)

    for i in range(0, len(dicom_files), step):
        dcm = pydicom.dcmread(dicom_files[i], stop_before_pixels=True)

        # Check modality
        modality = dcm.get("Modality")
        if modality:
            mod_value = modality.value if hasattr(modality, "value") else str(modality)
            if mod_value != "CT":
                raise ValueError(f"Mixed modalities found: CT and {mod_value}")

        # Check series UID
        series_uid = dcm.get("SeriesInstanceUID")
        if series_uid:
            uid_value = series_uid.value if hasattr(series_uid, "value") else str(series_uid)
            unique_series.add(uid_value)

    if len(unique_series) > 1:
        raise ValueError(f"Directory contains multiple series (found {len(unique_series)} unique SeriesInstanceUIDs). "
                        "Please ensure only one CT series is present in the directory.")


def extract_ct_metadata(dicom_files: List[str]) -> Dict[str, Any]:
    """
    Extract BIDS-compliant CT metadata from DICOM files.

    Args:
        dicom_files: List of DICOM file paths

    Returns:
        Dictionary with BIDS CT metadata fields

    Raises:
        ValueError: If no DICOM files provided
        RuntimeError: If DICOM files cannot be read
    """
    import pydicom
    import numpy as np

    if not dicom_files:
        raise ValueError("No DICOM files provided for metadata extraction")

    # Read first file for basic metadata
    ct_file = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)

    # Initialize parameters dictionary
    params: Dict[str, Any] = {}

    # Helper to get numeric DICOM values
    def get_float(dcm, tag, default="n/a"):
        value = dcm.get(tag)
        if value is None:
            return default
        value = value.value if hasattr(value, 'value') else value
        return float(value) if value else default

    def get_int(dcm, tag, default="n/a"):
        value = dcm.get(tag)
        if value is None:
            return default
        value = value.value if hasattr(value, 'value') else value
        return int(value) if value else default

    def get_str(dcm, tag, default="n/a"):
        value = dcm.get(tag)
        if value is None:
            return default
        value = value.value if hasattr(value, 'value') else value
        if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
            return list(value)
        return value if value else default

    # Extract all parameters
    params = {
        "Modality": get_str(ct_file, "Modality", "CT"),
        "Manufacturer": get_str(ct_file, "Manufacturer"),
        "ManufacturersModelName": get_str(ct_file, "ManufacturerModelName"),
        "SeriesDescription": get_str(ct_file, "SeriesDescription"),
        "ProtocolName": get_str(ct_file, "ProtocolName"),
        "TubeVoltage": get_float(ct_file, "KVP"),
        "SliceThickness": get_float(ct_file, "SliceThickness"),
        "FilterType": get_str(ct_file, "FilterType", "none"),
        "ConvolutionKernel": get_str(ct_file, "ConvolutionKernel", "none"),
        "GantryTilt": get_float(ct_file, "GantryDetectorTilt", 0.0),
        "DiameterFOV": get_float(ct_file, "DataCollectionDiameter"),
        "ReconstructionDiameter": get_float(ct_file, "ReconstructionDiameter"),
        "Pitch": get_float(ct_file, "SpiralPitchFactor"),
        "SingleCollimationWidth": get_float(ct_file, "SingleCollimationWidth"),
        "TotalCollimationWidth": get_float(ct_file, "TotalCollimationWidth"),
        "FocalSpots": get_str(ct_file, "FocalSpots"),
        "CTDIvol": get_float(ct_file, "CTDIvol"),
        "ContrastBolusAgent": get_str(ct_file, "ContrastBolusAgent", "none"),
        "ContrastBolusRoute": get_str(ct_file, "ContrastBolusRoute", "n/a"),
    }

    # Voxel size
    pixel_spacing = get_str(ct_file, "PixelSpacing")
    slice_thickness = params["SliceThickness"]
    if pixel_spacing != "n/a" and slice_thickness != "n/a":
        params["AcquisitionVoxelSize"] = [float(pixel_spacing[0]), float(pixel_spacing[1]), slice_thickness]

    # Matrix
    rows = get_int(ct_file, "Rows")
    cols = get_int(ct_file, "Columns")
    if rows != "n/a" and cols != "n/a":
        params["ReconMatrixSize"] = [rows, cols]
        params["ReconMatrix"] = [rows, cols, len(dicom_files)]

    # Per-slice parameters
    if len(dicom_files) > 1:
        z_positions, tube_currents, exposures = [], [], []
        for filepath in dicom_files:
            dcm = pydicom.dcmread(filepath, stop_before_pixels=True)
            pos = get_str(dcm, "ImagePositionPatient")
            if pos != "n/a":
                z_positions.append(pos[-1])
            tc = get_float(dcm, "XRayTubeCurrent")
            if tc != "n/a":
                tube_currents.append(tc)
            exp = get_float(dcm, "Exposure")
            if exp != "n/a":
                exposures.append(exp)

        if z_positions:
            ix = np.argsort(z_positions)
            if tube_currents and len(tube_currents) == len(z_positions):
                params["TubeCurrent"] = np.array(tube_currents)[ix].tolist()
            if exposures and len(exposures) == len(z_positions):
                params["Exposure"] = np.array(exposures)[ix].tolist()

    # Derived values
    if slice_thickness != "n/a":
        params["ScanLength"] = len(dicom_files) * slice_thickness / 10
        params["ScanLengthUnit"] = "cm"
        if params["CTDIvol"] != "n/a":
            params["DLP"] = params["ScanLength"] * params["CTDIvol"]
            params["DLPUnit"] = "mGy*cm"
            params["CTDIvolUnit"] = "mGy"

    # Sort so scalar values come first, then lists last
    scalars = {k: v for k, v in params.items() if not isinstance(v, list)}
    lists = {k: v for k, v in params.items() if isinstance(v, list)}
    return {**scalars, **lists}
