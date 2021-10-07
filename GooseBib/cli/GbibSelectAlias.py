"""GbibSelectAlias
  Select specific BibTeX fields and (optionally) choose the citation key.
  The selection is provided to the program using a json-file.

  ```json
  {
    "new_key" : "old_key",
    ...
  }
  ```

Usage:
  GbibSelectAlias [options] <json>

Options:
  -o, --output=<FILE>   Name of the output BibTeX file.
  -b, --bib=<FILE>      Name of the input BibTeX file.
      --version         Show version.
  -h, --help            Show help.

(c - MIT) T.W.J. de Geus | tom@geus.me | www.geus.me | github.com/tdegeus/GooseBib
"""
# ==================================================================================================
import json
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

# ---------------------------------- parse command line arguments ----------------------------------

# parse command-line options/arguments
args = docopt.docopt(__doc__, version=version)

# change keys to simplify implementation:
# - remove leading "-" and "--" from options
args = {re.sub(r"([\-]{1,2})(.*)", r"\2", key): args[key] for key in args}
# - change "-" to "_" to facilitate direct use in print format
args = {key.replace("-", "_"): args[key] for key in args}
# - remove "<...>"
args = {re.sub(r"(<)(.*)(>)", r"\2", key): args[key] for key in args}

# ---------------------------------------- check arguments -----------------------------------------

# check that the TeX files exist
if not os.path.isfile(args["json"]):
    Error('"{:s}" does not exist'.format(args["json"]))

# check that the BibTeX file exists
if args["bib"]:
    if not os.path.isfile(args["bib"]):
        Error('"{:s}" does not exist'.format(args["bib"]))

# if the file is an existing directory -> convert to file with same name as the input file
if args["output"]:
    if os.path.isdir(args["output"]):
        args["output"] = os.path.join(args["output"], os.path.split(args["bib"])[-1])

# -------------------------------------- select from bib-file --------------------------------------

# data
with open(args["json"]) as json_file:
    data = json.load(json_file)

# inverse data
data_inv = {data[key]: key for key in data}

# extract lists
keys_new = [key for key in sorted(data)]
keys_old = [data[key] for key in sorted(data)]

# read BibTeX file
bib = bibtexparser.load(open(args["bib"]), parser=bibtexparser.bparser.BibTexParser())

# get citation keys in the BibTeX files
bibkeys = [entry["ID"] for entry in bib.entries]

# find entries that are present in the TeX files, but missing in the BibTeX files
missing = [key for key in keys_old if key not in bibkeys]

# print missing entries
if len(missing) > 0:
    Error("Not found: " + ", ".join(missing))

# select entries based on the keys found in the TeX file
bib.entries = [entry for entry in bib.entries if entry["ID"] in keys_old]

# modify citation keys
for entry in bib.entries:
    entry["ID"] = data_inv[entry["ID"]]

# convert to text
bib = bibtexparser.dumps(bib)

# write bib-file, or print to screen
if args["output"]:
    open(args["output"], "w").write(bib)
else:
    print(bib)
