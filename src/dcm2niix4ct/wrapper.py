"""
Core wrapper for dcm2niix that modifies JSON sidecars with BIDS CT metadata.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any


class Dcm2niixWrapper:
    """Wrapper for dcm2niix that adds BIDS CT metadata to JSON sidecars."""

    def __init__(self, dcm2niix_path: str = "dcm2niix"):
        """
        Initialize the wrapper.

        Args:
            dcm2niix_path: Path to dcm2niix executable (default: "dcm2niix" from PATH)
        """
        self.dcm2niix_path = dcm2niix_path

    def run(self, input_dir: str, output_dir: Optional[str] = None,
            dcm2niix_args: Optional[List[str]] = None) -> subprocess.CompletedProcess:
        """
        Run dcm2niix and modify the output JSON sidecars with CT metadata.

        Args:
            input_dir: Directory containing DICOM files
            output_dir: Output directory (if None, uses dcm2niix default)
            dcm2niix_args: Additional arguments to pass to dcm2niix

        Returns:
            CompletedProcess object from subprocess

        Raises:
            ValueError: If not a CT scan or multiple series found
        """
        from .main import is_dicom_file, validate_ct_series

        # Validate the input directory
        input_path = Path(input_dir)
        dicom_files = []
        if input_path.is_dir():
            for file in input_path.iterdir():
                if file.is_file() and is_dicom_file(str(file)):
                    dicom_files.append(str(file))

        if dicom_files:
            validate_ct_series(dicom_files)

        # Build dcm2niix command
        cmd = [self.dcm2niix_path]

        if dcm2niix_args:
            cmd.extend(dcm2niix_args)

        if output_dir:
            cmd.extend(["-o", output_dir])

        cmd.append(input_dir)

        # Get the actual output directory
        if output_dir:
            out_path = Path(output_dir)
        else:
            out_path = Path(input_dir)

        # List existing JSON files before conversion
        existing_jsons = set(out_path.glob("*.json")) if out_path.exists() else set()

        # Run dcm2niix
        print(f"Running: {' '.join(cmd)}", file=sys.stderr)
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Print dcm2niix output
        if result.stdout:
            print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)

        if result.returncode != 0:
            return result

        # Find newly created JSON files
        current_jsons = set(out_path.glob("*.json")) if out_path.exists() else set()
        new_jsons = current_jsons - existing_jsons

        # Modify each new JSON sidecar
        for json_file in new_jsons:
            self._modify_json_sidecar(json_file, dicom_files)

        return result

    def _modify_json_sidecar(self, json_file: Path, dicom_files: List[str]):
        """Add CT metadata to JSON sidecar."""
        from .main import extract_ct_metadata, is_ct_scan

        if not dicom_files:
            raise ValueError("No DICOM files found")

        if not is_ct_scan(dicom_files):
            raise ValueError("Not a CT scan")

        with open(json_file, 'r') as f:
            data = json.load(f)

        ct_metadata = extract_ct_metadata(dicom_files)
        data.update(ct_metadata)

        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Added {len(ct_metadata)} CT metadata fields to {json_file.name}", file=sys.stderr)


def run_dcm2niix_wrapper(input_dir: str, output_dir: Optional[str] = None,
                         dcm2niix_args: Optional[List[str]] = None,
                         additional_metadata: Optional[Dict[str, Any]] = None,
                         dcm2niix_path: str = "dcm2niix") -> int:
    """
    Convenience function to run the dcm2niix wrapper.

    Args:
        input_dir: Directory containing DICOM files
        output_dir: Output directory (if None, uses dcm2niix default)
        dcm2niix_args: Additional arguments to pass to dcm2niix
        additional_metadata: Additional metadata to add to JSON sidecars
        dcm2niix_path: Path to dcm2niix executable

    Returns:
        Exit code from dcm2niix
    """
    wrapper = Dcm2niixWrapper(dcm2niix_path)
    result = wrapper.run(input_dir, output_dir, dcm2niix_args, additional_metadata)
    return result.returncode
