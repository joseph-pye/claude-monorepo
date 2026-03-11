"""
<project-name>

Replace this docstring with a one-liner describing what this script does.
"""

import argparse
import os

from dotenv import load_dotenv

load_dotenv()


def main(args: argparse.Namespace) -> None:
    # TODO: implement your idea here
    print(f"Hello from {args.name}!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="world", help="Name to greet")
    main(parser.parse_args())
