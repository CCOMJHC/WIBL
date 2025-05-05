import sys
from pathlib import Path
import argparse
import json

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Convert JSON files in a directory to OpenVBI B-12 metadata format'
    )
    parser.add_argument('input_dir', type=str,
                        help='Input directory containing B-12 JSON metadata in WIBL 1.0.4 format')
    parser.add_argument('output_dir', type=str,
                        help=('Name of directory to write B-12 JSON metadata in OpenVBI/WIBL 1.1.0 format. '
                              'If directory does not exist it will be created.')
                        )
    args = parser.parse_args()

    input_dir: Path = Path(args.input_dir)
    if not input_dir.is_dir():
        sys.exit(f"input_dir {args.input_dir} is not an existing directory, but must be.")

    output_dir: Path = Path(args.output_dir)
    if output_dir.exists():
        if not output_dir.is_dir():
            sys.exit(f"output_dir path {args.output_dir} exists but is not a directory.")
    else:
        output_dir.mkdir()

    for ifile in input_dir.glob('*.json'):
        print(f"In file: {ifile}")
        ofile: Path = output_dir / ifile.name
        print(f"\tout file: {ofile}")
        # Read data
        try:
            with open(ifile, mode='r') as f:
                    src_md: dict = json.load(f)
        except Exception as e:
            print(f"Unable to read file {ifile} due to error: {e}, continuing with next file")
            continue

        # Prepare output data
        dest_md = {}
        p = {}
        dest_md['properties'] = p
        if 'trustedNode' in src_md:
            p['trustedNode'] = src_md['trustedNode']
        if 'platform' in src_md:
            p['platform'] = src_md['platform']
        if 'processing' in src_md:
            p['processing'] = src_md['processing']

        # Write it
        try:
            with open(ofile, 'w', encoding='utf-8') as f:
                json.dump(dest_md, f, indent=4)
        except Exception as e:
            print(f"Unable to write file {ofile} due to error: {e}, continuing with next file")
            continue

    return 0


if __name__ == '__main__':
    main()
