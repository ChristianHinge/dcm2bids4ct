"""
dcm2niix4ct: A wrapper for dcm2niix that adds BIDS-compliant CT metadata to JSON sidecars.
"""

from .wrapper import Dcm2niixWrapper, run_dcm2niix_wrapper
from .main import (
    find_dicom_files,
    is_dicom_file,
    is_ct_scan,
    validate_ct_series,
    extract_ct_metadata,
)

__version__ = "0.1.0"

__all__ = [
    "Dcm2niixWrapper",
    "run_dcm2niix_wrapper",
    "find_dicom_files",
    "is_dicom_file",
    "is_ct_scan",
    "validate_ct_series",
    "extract_ct_metadata",
]
