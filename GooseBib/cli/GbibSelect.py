"""GbibSelect
  Select only those entries present in a TeX-file.

Usage:
  GbibSelect [options] <tex>...

Options:
  -o, --output=<FILE>   Name of the output BibTeX file.
  -b, --bib=<FILE>      Name of the input BibTeX file.
      --version         Show version.
  -h, --help            Show help.

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


# ===================================== EXTRACT CITATION KEYS ======================================


def tex2cite(tex):

    # extract keys from "cite"
    def extract(s):
        try:
            return list(
                re.split(r"([pt])?(\[.*\]\[.*\])?(\{[a-zA-Z0-9\,\-\ ]*\})", s)[3][1:-1].split(",")
            )
        except:
            print("Error in interpreting\n {0} ...").format(s[:100])

    # read all keys in "cite", "citet", "citep" commands
    cite = [extract(i) for i in tex.split(r"\cite")[1:]]
    cite = list({item for sublist in cite for item in sublist})
    cite = [i.replace(" ", "") for i in cite]

    return cite


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

    # check that the TeX files exist
    for fname in args["tex"]:
        if not os.path.isfile(fname):
            Error(f'"{fname:s}" does not exist')

    # check that the BibTeX file exists
    if args["bib"]:
        if not os.path.isfile(args["bib"]):
            Error('"{:s}" does not exist'.format(args["bib"]))

    # if the file is an existing directory -> convert to file with same name as the input file
    if args["output"]:
        if os.path.isdir(args["output"]):
            args["output"] = os.path.join(args["output"], os.path.split(args["bib"])[-1])

    # -------------------------------------- get citation keys -------------------------------------

    # initialize
    keys = []

    # read from TeX files
    for fname in args["tex"]:
        keys += tex2cite(open(fname).read())

    # sort citation keys
    keys = sorted(list(set(keys)))

    # optionally: print and quit
    if not args["bib"] and not args["output"]:
        print("\n".join(keys))

    # ------------------------------------- select from bib-file -----------------------------------

    # read BibTeX file
    bib = bibtexparser.load(open(args["bib"]), parser=bibtexparser.bparser.BibTexParser())

    # get citation keys in the BibTeX files
    bibkeys = [entry["ID"] for entry in bib.entries]

    # find entries that are present in the TeX files, but missing in the BibTeX files
    missing = [key for key in keys if key not in bibkeys]

    # print missing entries
    if len(missing) > 0:
        Error("Not found: " + ", ".join(missing))

    # select entries based on the keys found in the TeX file
    bib.entries = [entry for entry in bib.entries if entry["ID"] in keys]

    # convert to text
    bib = bibtexparser.dumps(bib)

    # write bib-file, or print to screen
    if args["output"]:
        open(args["output"], "w").write(bib)
    else:
        print(bib)
