"""Command-line entry: run the benchmark from hand-authored JSON files.

    python -m incar_eval.cli --cases cases.json --responses responses.json
    python -m incar_eval.cli --cases cases.json --responses responses.json --baseline strong
"""

import argparse

from .loader import run_from_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the in-car eval benchmark from JSON files.")
    parser.add_argument("--cases", required=True, help="path to the gold cases JSON")
    parser.add_argument("--responses", required=True, help="path to the recorded model responses JSON")
    parser.add_argument("--baseline", default=None, help="model name to compare others against (default: first)")
    args = parser.parse_args()
    print(run_from_files(args.cases, args.responses, baseline=args.baseline))


if __name__ == "__main__":
    main()
