#!/usr/bin/env python3
"""Create a sparse file with a payload written near the end of the file."""

import argparse
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Location of the file to create")
    parser.add_argument(
        "--size-gib",
        type=float,
        default=5.0,
        help="Logical file size in GiB (default: 5)",
    )
    parser.add_argument(
        "--payload",
        default="LargeFileTestPayload\n",
        help="Payload string to write at the end of the file",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=None,
        help="Explicit byte offset for the payload; defaults to size minus payload length",
    )
    return parser.parse_args()


def create_sparse_file(path: Path, logical_size: int, payload: bytes, offset: int | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        if offset is None:
            offset = logical_size - len(payload)
        if offset < 0:
            raise ValueError("Payload is larger than the requested logical size")
        handle.seek(offset)
        handle.write(payload)


def main() -> int:
    args = parse_args()
    logical_size = int(args.size_gib * (1 << 30))
    if logical_size <= 0:
        print("Logical size must be positive", file=sys.stderr)
        return 1

    payload = args.payload.encode("utf-8")
    try:
        create_sparse_file(args.path, logical_size, payload, args.offset)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Failed to create sparse file: {exc}", file=sys.stderr)
        return 1

    print(
        f"Created sparse file '{args.path}' with logical size {logical_size} bytes;"
        f" payload written at offset {args.offset or (logical_size - len(payload))}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
