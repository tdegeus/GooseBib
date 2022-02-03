"""GbibCheckLink
  Check if the "doi", "arxivid", and "url" in a BibTeX file exists. Note: this function has to
  actually browse to the sites, it is thus quite slow!

Usage:
  GbibCheckLink [options] <bibfile>

Options:
  -n, --no-link   Print entries that do not have any of the listed links.
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
import requests

from .. import version

# ==================================== RAISE COMMAND LINE ERROR ====================================


def Error(msg, exit_code=1):

    print(msg)

    sys.exit(exit_code)


# ====================================== CHECK IF URL EXISTS =======================================


def urlExists(url):

    request = requests.get(url)

    if request.status_code == 200:
        return True
    else:
        return False


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
    if args["bibfile"]:
        if not os.path.isfile(args["bibfile"]):
            Error('"{:s}" does not exist'.format(args["bibfile"]))

    # ------------------------------------------ check file ----------------------------------------

    # read BibTeX file
    with open(args["bibfile"]) as file:
        bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

    # list with incorrect refs
    # - allocate
    doi = []
    # - check
    for entry in bib.entries:
        if "doi" in entry:
            if not urlExists("http://dx.doi.org/" + entry["doi"]):
                doi += [entry["ID"]]

    # list with incorrect refs
    # - allocate
    arxivid = []
    # - check
    for entry in bib.entries:
        if "arxivid" in entry:
            if not urlExists("http://arxiv.org/abs/" + entry["arxivid"]):
                arxivid += [entry["ID"]]

    # list with incorrect refs
    # - allocate
    url = []
    # - check
    for entry in bib.entries:
        if "url" in entry:
            if not urlExists(entry["url"]):
                url += [entry["ID"]]

    # list entries without any link
    # - allocate
    nolink = []
    # - check
    if args["no_link"]:
        for entry in bib.entries:
            if "doi" not in entry and "arxivid" not in entry and "url" not in entry:
                nolink += [entry["ID"]]

    # ---------------------------------------- print diagnosis -------------------------------------

    diag = {}

    for key in doi:
        diag[key] = diag.get(key, []) + ["doi"]
    for key in arxivid:
        diag[key] = diag.get(key, []) + ["arxivid"]
    for key in url:
        diag[key] = diag.get(key, []) + ["url"]
    for key in nolink:
        diag[key] = diag.get(key, []) + ["no-link"]

    if len(diag) == 0:
        print("No errors")
        sys.exit(0)

    fmt = r"{key:%ds} : {value:s}" % max(len(key) for key in diag)

    for key in sorted(diag):
        print(fmt.format(key=key, value=", ".join(diag[key])))
