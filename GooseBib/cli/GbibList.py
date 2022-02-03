"""GbibList
  List a specific field (e.g. the journal) for all BibTeX entries.

Usage:
  GbibList [options] <input>

Arguments:
  input                   Input BibTeX-file.

Options:
  -j, --journal           List the journal field.
      --version           Show version.
  -h, --help              Show help.

(c - MIT) T.W.J. de Geus | tom@geus.me | www.geus.me | github.com/tdegeus/GooseBib
"""
# ==================================================================================================
import os
import re

import bibtexparser
import docopt

from .. import version

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
        raise OSError('"{input:s}" does not exist'.format(**args))

    # ---------------------------------------- parse bib-file --------------------------------------

    # read
    # ----

    with open(args["input"]) as file:
        bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

    # list journals
    # -------------

    if args["journal"]:

        out = []

        for entry in bib.entries:
            if "journal" in entry:
                out += [entry["journal"]]

        out = sorted(list(set(out)))

        print("\n".join(out))
