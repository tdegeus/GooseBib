"""GbibClean
  Clean a BibTeX database, stripping it from unnecessary fields, unifying the formatting of authors,
  and ensuring the proper special characters and math mode settings.

Usage:
  GbibClean [options] <input> <output>

Arguments:
  input                   Input BibTeX-file.
  output                  Output file, or path (the "input" file-name is copied).

Options:
      --author-sep=<str>  Character to separate authors' initials. [default: ]
      --ignore-case       Do not protect case of title.
      --ignore-math       Do not apply math-mode fix.
      --ignore-unicode    Do not apply unicode fix.
      --dot-space=<str>   Character separating abbreviation dots. [default: ]
      --no-title          Remove title from BibTeX file.
      --verbose           Show interpretation.
      --version           Show version.
  -h, --help              Show help.

(c - MIT) T.W.J. de Geus | tom@geus.me | www.geus.me | github.com/tdegeus/GooseBib
"""
# ==================================================================================================
import difflib
import os
import re
import sys

import argparse

from .. import bibtex
from .. import version

# ==================================== RAISE COMMAND LINE ERROR ====================================


def Error(msg, exit_code=1):

    print(msg)

    sys.exit(exit_code)


# ========================================== MAIN PROGRAM ==========================================


def main():

    class Parser(argparse.ArgumentParser):
        def print_help(self):
            print(__doc__)

    parser = Parser()
    parser.add_argument("--author-sep", type=str, default="")
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("--ignore-math", action="store_true")
    parser.add_argument("--ignore-unicode", action="store_true")
    parser.add_argument("--dot-space", ype=str, default="")
    parser.add_argument("--no-title", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("-v", "--version", action="version", version=version)
    parser.add_argument("input", type=str)
    parser.add_argument("output", type=str)
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        Error('"{:s}" does not exist'.format(args.input))

    if os.path.isdir(args.output):
        args.output = os.path.join(args.output, os.path.split(args.input)[-1])

    data = bibtex.clean(
        args.input,
        sep_name=args.author_sep,
        sep=args.dot_space,
        title=not args.no_title,
        protect_math=not args.ignore_math,
        rm_unicode=not args.ignore_unicode,
    )

    with open(args.output, "w") as file:
        file.write(data)

    if args.verbose:
        simple = bibtex.select(args.input)
        sys.stdout.writelines(difflib.unified_diff(simple, data))
