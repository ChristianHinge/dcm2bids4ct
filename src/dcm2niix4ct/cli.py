"""Command-line interface for dcm2niix4ct wrapper."""

import sys
from pathlib import Path
from .wrapper import Dcm2niixWrapper


def main(argv=None):
    """Run dcm2niix and add CT metadata to JSON sidecars."""
    args = argv or sys.argv[1:]

    if not args or args[0] in ['-h', '--help']:
        print("Usage: dcm2niix4ct <input_dir> [dcm2niix_args...]")
        print("\nWrapper for dcm2niix that adds BIDS CT metadata to JSON sidecars")
        print("All arguments are passed directly to dcm2niix")
        return 0

    input_dir = args[0]
    dcm2niix_args = args[1:]

    # Extract and remove output dir from args if specified
    output_dir = None
    if '-o' in dcm2niix_args:
        idx = dcm2niix_args.index('-o')
        if idx + 1 < len(dcm2niix_args):
            output_dir = dcm2niix_args[idx + 1]
            # Remove -o and its argument from dcm2niix_args
            dcm2niix_args = dcm2niix_args[:idx] + dcm2niix_args[idx+2:]

    if not Path(input_dir).is_dir():
        print(f"Error: {input_dir} is not a directory", file=sys.stderr)
        return 1

    wrapper = Dcm2niixWrapper()
    result = wrapper.run(input_dir, output_dir, dcm2niix_args)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
