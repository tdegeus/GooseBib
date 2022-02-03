"""GbibCheckAuthors
  List authors that are possibly stored in more than one way.
  Specifically, the algorithm finds those authors that are written in exactly
  the way after parsing such that first names are abbreviated.

Usage:
  GbibCheckAuthors [options] <input>

Arguments:
  input                   Input BibTeX-file.

Options:
      --version           Show version.
  -h, --help              Show help.

(c - MIT) T.W.J. de Geus | tom@geus.me | www.geus.me | github.com/tdegeus/GooseBib
"""
# ==================================================================================================
import os
import re
import sys

import bibtexparser
import docopt

from .. import version

# ======================================== REFORMAT AUTHORS ========================================


def reformatAuthor(text, sep=" "):

    # skip authors that cannot be split in first and last name
    if len(text.split(",")) <= 1:
        return text

    # define find/replace criteria
    match = [
        (re.compile(r"(.*)(\(.*\))", re.UNICODE), r"\1"),
        (re.compile(r"([A-Za-z][\}]?)([\w0-9\{\}\'\"\\\.\^\{]*)", re.UNICODE), r"\1."),
        (re.compile(r"([A-Za-z\.][\-]?)([\ ]*)", re.UNICODE), r"\1"),
        (re.compile(r"([A-Za-z\.][\-]?)([A-Za-z])", re.UNICODE), r"\1" + sep + r"\2"),
    ]

    # extract first and last name
    last, first = text.split(",")

    # update extend all "." with a space, to distinguish initials
    first = first.replace(".", ". ")

    # loop over over find/replace criteria
    for regex, sub in match:
        first = re.sub(regex, sub, first)

    # remove spaces from the beginning and end
    first = first.strip()

    # rejoin first and last name
    return last + ", " + first.upper()


# ================================ CONVERT UNICODE SYMBOLS TO LATEX ================================


def replaceUnicode(text):

    # NB list not exhaustive, please extend!
    match = [
        ("ç", r"\c{c}"),
        ("è", r"\`{e}"),
        ("é", r"\'{e}"),
        ("ë", r"\"{e}"),
        ("ô", r"\^{o}"),
        ("ö", r"\"{o}"),
        ("ü", r"\"{y}"),
        ("g̃", r"\~{g}"),
        ("ñ", r"\~{n}"),
        ("İ", r"\.{I}"),
        ("à", r"\'{a}"),
        ("ă", r"\v{a}"),
        ("ř", r"\v{r}"),
        ("–", "--"),
        ("—", "--"),
        ("“", "``"),
        ("”", "''"),
        ("×", r"$\times$"),
    ]

    # loop over over find/replace criteria
    for ex, sub in match:
        text = text.replace(ex, sub)

    return text


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
        print('"{input:s}" does not exist'.format(**args))
        sys.exit(1)

    # ---------------------------------------- parse bib-file --------------------------------------

    # read
    # ----

    with open(args["input"]) as file:
        bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

    # check entries
    # -------------

    names = {}

    for entry in bib.entries:

        # set author separation
        sep = ""

        # fix author abbreviations
        for key in ["author", "editor"]:
            if key in entry:
                for name in entry[key].split(" and "):
                    fmtName = replaceUnicode(reformatAuthor(name, sep))
                    if fmtName not in names:
                        names[fmtName] = [name]
                    if name not in names[fmtName]:
                        names[fmtName] += [name]

    # filter unique
    names = {name: names[name] for name in names if len(names[name]) > 1}

    # output format
    n = max(len(name) for name in names)

    # print
    for name in sorted(names):
        print(("{0:%ds} : {1:s}" % (n)).format(name, "; ".join(names[name])))
