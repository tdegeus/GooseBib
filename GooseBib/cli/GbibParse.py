"""GbibParse
  Basic parse of a BibTeX file to increase compliance with the standard.
  Use "GbibClean" for a more rigorous clean-up.

Usage:
  GbibParse <input> <output>

Arguments:
  input     Input BibTeX-file.
  output    Output file, or path (the "input" file-name is copied).

Options:
      --version   Show version.
  -h, --help      Show help.

(c - MIT) T.W.J. de Geus | tom@geus.me | www.geus.me | github.com/tdegeus/GooseBib
"""
# ==================================================================================================
import os
import re
import sys

import bibtexparser
import docopt

from .. import version

# ==================================== RAISE COMMAND LINE ERROR ====================================


def Error(msg, exit_code=1):

    print(msg)

    sys.exit(exit_code)


# ========================================== MAIN PROGRAM ==========================================


def main():

    # --------------------------------- parse command line arguments -------------------------------

    # parse command-line options/arguments
    args = docopt.docopt(__doc__, version=version)

    # change keys to simplify implementation:
    # - remove leading "-" and "--" from options
    args = {re.sub(r"([\-]{1,2})(.*)", r"\2", key): args[key] for key in args}
    # - change "-" to "_" to facilitate direct use in print format
    args = {key.replace("-", "_"): args[key] for key in args}
    # - remove "<...>"
    args = {re.sub(r"(<)(.*)(>)", r"\2", key): args[key] for key in args}

    # --------------------------------------- check arguments --------------------------------------

    # check that the BibTeX file exists
    if not os.path.isfile(args["input"]):
        Error('"{input:s}" does not exist'.format(**args))

    # if "output" is an existing directory; convert to file with same name as the input file
    if os.path.isdir(args["output"]):
        args["output"] = os.path.join(args["output"], os.path.split(args["input"])[-1])

    # ---------------------------------------- parse bib-file --------------------------------------

    # read
    with open(args["input"]) as file:
        bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

    # write
    open(args["output"], "w").write(bibtexparser.dumps(bib))
