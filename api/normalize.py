"""Isolate HTSlib stdout handling from the API and concurrent tests."""

import sys

from pysam import bcftools


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m api.normalize REFERENCE INPUT")
    bcftools.norm("-f", sys.argv[1], "-m", "-any", "-Ov", sys.argv[2], catch_stdout=False)


if __name__ == "__main__":
    main()
