"""GbibCheckKeys
  List entries that do not have a citation key composed of "LastName + Year".

Usage:
  GbibCheckKeys [options] <input>

Arguments:
  input                   Input BibTeX-file.

Options:
  -s, --view-skipped      View skipped entries that cannot be composed in the standard way.
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

# ==================================================================================================


def replaceUnicode(text):

    match = [
        ("ç", "c"),
        ("è", "e"),
        ("é", "e"),
        ("ë", "e"),
        ("ô", "o"),
        ("ö", "o"),
        ("ü", "y"),
        ("g̃", "g"),
        ("ñ", "n"),
        ("İ", "I"),
        ("à", "a"),
        ("ă", "a"),
        ("ř", "r"),
        (r"\c{c}", "c"),
        (r"\`{e}", "e"),
        (r"\'{e}", "e"),
        (r"\"{e}", "e"),
        (r"\^{o}", "o"),
        (r"\"{o}", "o"),
        (r"\"{y}", "y"),
        (r"\~{g}", "g"),
        (r"\~{n}", "n"),
        (r"\.{I}", "I"),
        (r"\'{a}", "a"),
        (r"\v{a}", "a"),
        (r"\v{r}", "r"),
        (r"{\"{a}}", "a"),
        (r"{\"{u}}", "u"),
        (r"{\'{c}}", "c"),
        (r"{\'{s}}", "s"),
        (r"{\^{i}}", "i"),
        (r"{\v{s}}", "s"),
        (r"{\v{z}}", "z"),
        (r"\aa", "a"),
        (r"{\o}", "o"),
        (r"'", ""),
        (r" ", ""),
    ]

    for ex, sub in match:
        text = text.replace(ex, sub)

    return text


# ==================================================================================================


def getPlainLastName(full_name):

    last = full_name.split(",")[0]

    last = replaceUnicode(last)
    last = last.replace("{", "")
    last = last.replace("}", "")
    last = last[0].upper() + last[1:]

    return last


# ========================================== MAIN PROGRAM ==========================================


def main():

    # parse command-line options/arguments
    # change keys to simplify implementation:
    # - remove leading "-" and "--" from options
    # - change "-" to "_" to facilitate direct use in print format
    # - remove "<...>"
    args = docopt.docopt(__doc__, version=version)
    args = {re.sub(r"([\-]{1,2})(.*)", r"\2", key): args[key] for key in args}
    args = {key.replace("-", "_"): args[key] for key in args}
    args = {re.sub(r"(<)(.*)(>)", r"\2", key): args[key] for key in args}

    if not os.path.isfile(args["input"]):
        print('"{input:s}" does not exist'.format(**args))
        sys.exit(1)

    alphabet = "abcdefghijklmnopqrstuvwxyz"
    alphabet_list = list(alphabet)

    # get all keys and auto-generated equivalent

    with open(args["input"]) as file:
        bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

    keys = []

    for entry in bib.entries:

        old_key = entry["ID"]
        new_key = entry["ID"]
        generated = False

        if "author" in entry and "year" in entry:
            name = getPlainLastName(entry["author"].split(" and ")[0])
            year = entry["year"]
            new_key = name + year
            generated = True

        if not generated:
            if "editor" in entry and "year" in entry:
                name = getPlainLastName(entry["editor"].split(" and ")[0])
                year = entry["year"]
                new_key = name + year
                generated = True

        keys += [[old_key, new_key, generated]]

    keys = sorted(keys, key=lambda x: x[0])

    # handle duplicate keys by adding (a, b, c, ...); respect old

    ntimes = {new_key: 0 for _, new_key, _ in keys}

    for old_key, new_key, generated in keys:
        ntimes[new_key] += 1

    for idx, (old_key, new_key, generated) in enumerate(keys):
        if old_key != new_key:
            if ntimes[new_key] > 1:
                if re.match(r"[a-z]", old_key[-1]):
                    new_key += old_key[-1]
                    keys[idx][1] = new_key

    # handle duplicate keys by adding (a, b, c, ...)

    ntimes = {new_key: 0 for _, new_key, _ in keys}

    for old_key, new_key, generated in keys:
        ntimes[new_key] += 1

    for idx, (old_key, new_key, generated) in enumerate(keys):
        if not generated:
            continue
        if ntimes[new_key] > 1:
            ntimes[new_key] -= 1
            if not re.match(r"[a-z]", new_key[-1]):
                new_key += "a"
            if new_key in ntimes:
                new_key = new_key[:-1] + alphabet_list[alphabet.find(new_key[-1]) + 1]
            keys[idx][1] = new_key
            ntimes[new_key] = 1

    # make sure that duplicate suffix (a, b, c, ...) is as low as possible

    ntimes = {new_key: 0 for _, new_key, _ in keys}

    for old_key, new_key, generated in keys:
        ntimes[new_key] += 1

    for idx, (old_key, new_key, generated) in enumerate(keys):

        if not generated:
            continue

        if not re.match(r"[a-z]", new_key[-1]):
            continue

        if new_key[:-1] not in ntimes:
            keys[idx][1] = new_key[:-1]
            ntimes[new_key[:-1]] = 1
            ntimes[new_key] -= 1
            continue

        if ntimes[new_key[:-1]] == 0:
            keys[idx][1] = new_key[:-1]
            ntimes[new_key[:-1]] += 1
            ntimes[new_key] -= 1
            continue

        for j in range(alphabet.find(new_key[:-1])):
            if new_key[:-1] + alphabet[j] not in ntimes:
                keys[idx][1] = new_key[:-1] + alphabet[j]
                ntimes[keys[idx][1]] = 1
                ntimes[new_key] -= 1
                break

            if ntimes[new_key[:-1] + alphabet[j]] == 0:
                keys[idx][1] = new_key[:-1] + alphabet[j]
                ntimes[keys[idx][1]] += 1
                ntimes[new_key] -= 1
                break

    # print respect

    n = max(len(old_key) for old_key, _, _ in keys)
    fmt = "{0:%ds} : {1:s}" % (n)

    for old_key, new_key, generated in keys:
        if old_key != new_key:
            print(fmt.format(old_key, new_key))

    if args["view_skipped"]:
        skipped = [new_key for old_key, new_key, generated in keys if not generated]
        if len(skipped) > 0:
            print("")
            print("Skipped keys:")
            print("\n".join(skipped))
