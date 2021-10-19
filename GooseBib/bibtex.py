import argparse
import difflib
import inspect
import os
import re
import sys
import textwrap
from functools import singledispatch

import bibtexparser

from . import journals
from . import recognise
from . import reformat
from ._version import version


def _subr(pattern, repl, string):
    """
    Recursive replacement: apply ``re.subn`` until no more replacement is made.
    """

    string, nsub = re.subn(pattern, repl, string)

    if nsub:
        return _subr(pattern, repl, string)

    return string


def selection(use_bibtexparser: bool = False):
    """
    List of fields to keep in a BibTeX file to get a useful list of references:
    fields that are not in this selection may be useful for a database, but might only cloud
    BibTeX output.

    :param use_bibtexparser: Add bibtexparser specific fields to select (not part of BibTeX output).
    """

    base = []

    if use_bibtexparser:
        base += ["ID", "ENTRYTYPE"]

    base += ["author", "title", "year", "doi", "arxivid"]

    return dict(
        article=base + ["journal", "volume", "number", "pages"],
        unpublished=base,
        inproceedings=base + ["booktitle", "editor", "publisher", "volume", "number", "pages"],
        book=base + ["edition", "editor", "publisher", "isbn"],
        inbook=base + ["edition", "editor", "publisher", "isbn"],
        incollection=base + ["booktitle", "edition", "publisher", "isbn"],
        phdthesis=base + ["school", "isbn", "url"],
        techreport=base + ["institution", "isbn", "url"],
        misc=base + ["pages", "url"],
    )


@singledispatch
def select(data, fields: dict[list] = None, ensure_link: bool = True, remove_url: bool = True):
    """
    Remove unnecessary fields for BibTex file.

    :param data:
        The BibTeX database (filename or bibtexparser instance).

    :param fields:
        Fields to keep per entry type (default from :py:fund:`selection`).

    :param ensure_link:
        Add URL to ``fields`` if no ``doi`` or ``arxivid`` is present.

    :param remove_url:
        Remove URL with either a ``doi`` or an ``arxivid`` is present.
    """

    if fields is None:
        fields = selection(use_bibtexparser=True)

    for entry in data.entries:

        select = fields[entry["ENTRYTYPE"]]

        if ensure_link:
            if "url" not in select:
                if "doi" not in entry and "arxivid" not in entry:
                    select.append("url")

        rm = [key for key in entry if key not in select]
        for key in rm:
            del entry[key]

        if remove_url:
            if "url" in entry and ("doi" in entry or "arxivid" in entry):
                del entry["url"]

    return data


@select.register(str)
def _(data, *args, **kwargs):

    with open(data) as file:
        bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

    bib = select(bib, *args, **kwargs)

    return bibtexparser.dumps(bib)


@singledispatch
def clean(
    data,
    journal_type: str = "abbreviation",
    journal_database: list[str] = ["pnas", "physics", "mechanics"],
    sep_name: str = "",
    sep: str = "",
    title: bool = True,
    protect_math: bool = True,
    rm_unicode: bool = True,
):
    """
    Clean a BibTeX database:
    *   Remove unnecessary fields (see :py:func:`GooseBib.bibtex.select`).
    *   Unify the formatting of authors (see :py:func:`GooseBib.reformat.abbreviate_firstname`).
    *   Ensure proper math formatting (see :py:func:`GooseBib.reformat.protect_math`).
    *   Convert unicode to TeX (see :py:func:`GooseBib.reformat.rm_unicode`).
    *   Fill digital identifier if it is not present by can be found from a different field
        (see :py:func:`GooseBib.recognise.doi` and :py:func:`GooseBib.recognise.arxivid`).

    :param data: The BibTeX database (filename or bibtexparser instance).
    :param journal_type: Use journal: "title", "abbreviation", or "acronym".
    :param journal_database: Database(s) with official journal names, abbreviations, and acronym.
    :param sep_name: Separate name initials (e.g. "", " ").
    :param sep: Separate abbreviations in title and author: replace ". " e.g. by "." or ". ".
    :param title: Include title of relevant fields.
    :param protect_math: Apply fix of :py:func:`reformat.protect_math`.
    :param rm_unicode: Apply fix of :py:func:`reformat.rm_unicode`.
    """

    journal_type = journal_type.lower()
    journal_database = [journal_database] if isinstance(journal_database, str) else journal_database

    revus = []

    for entry in data.entries:

        # prepare journal rename
        if "journal" in entry:
            revus.append(entry["journal"])

        # find doi
        if "doi" not in entry:
            doi = recognise.doi(
                *[val for key, val in entry.items() if key not in ["arxivid", "eprint"]]
            )
            if doi:
                entry["doi"] = doi

        # find arXiv-id
        if "arxivid" not in entry:
            arxivid = recognise.arxivid(*[val for key, val in entry.items() if key not in ["doi"]])
            if arxivid:
                entry["arxivid"] = arxivid

        # fix author abbreviations
        for key in ["author", "editor"]:
            if key in entry:
                entry[key] = " and ".join(
                    [reformat.abbreviate_firstname(i, sep_name) for i in entry[key].split(" and ")]
                )

        # remove title
        if not title:
            entry.pop("title", None)

        # protect math-mode
        if protect_math:
            for key in ["title"]:
                if key in entry:
                    entry[key] = reformat.protect_math(entry[key])

        # convert unicode to LaTeX
        if rm_unicode:
            for key in ["author", "editor", "title"]:
                if key in entry:
                    entry[key] = reformat.rm_unicode(entry[key])

        # abbreviations: change symbol after "."
        for key in ["journal", "author"]:
            if key in entry:
                entry[key] = entry[key].replace(". ", f".{sep} ")

        # fix underscore problems
        # -
        if "doi" in entry:
            entry["doi"] = entry["doi"].replace("_", r"\_")
            entry["doi"] = entry["doi"].replace("{\\\\_}", r"\_")
            entry["doi"] = entry["doi"].replace("{\\_}", r"\_")
            entry["doi"] = entry["doi"].replace(r"{\_}", r"\_")
        # -
        if "url" in entry:
            entry["url"] = entry["url"].replace(r"{\_}", r"\_")
            entry["url"] = entry["url"].replace("{\\_}", r"\_")
            entry["url"] = entry["url"].replace("{~}", "~")
            entry["url"] = entry["url"].replace(r"\&", "&")
        # -
        if "url" in entry:
            entry["url"] = _subr(re.compile(r"({)([^}])(})", re.UNICODE), r"\2", entry["url"])

    # rename journal

    if len(journal_database) > 0:

        db = journals.load(*journal_database)
        if journal_type in ["title", "name", "official", "off"]:
            new = db.map2name(revus)
        elif journal_type in ["abbreviation", "abbr"]:
            new = db.map2abbreviation(revus)
        elif journal_type in ["acronym", "acro"]:
            new = db.map2acronym(revus)
        else:
            raise OSError(f'Unknown journal type selection "{journal_type}"')

        mapping = {o: n for o, n in zip(revus, new)}

        for entry in data.entries:
            if "journal" in entry:
                entry["journal"] = mapping[entry["journal"]]

    # return selection of fields

    return select(data, fields=selection(use_bibtexparser=True))


@clean.register(str)
def _(data, *args, **kwargs):

    with open(data) as file:
        bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

    bib = clean(bib, *args, **kwargs)

    return bibtexparser.dumps(bib)


def GbibClean():
    r"""
    Clean a BibTeX database, stripping it from unnecessary fields,
    unifying the formatting of authors, and ensuring the proper special characters and
    math mode settings.

    :usage:

        GbibClean [options] <input> <output>

    :arguments:

        <input>
            Input BibTeX-file.

        <output>
            Output file.
            If ``<output>`` is a directory, it is appended with the filename of ``<input>``.

    :options:

        -j, --journal-type=STR
            Use journal: "title", "abbreviation", or "acronym". Default: "abbreviation".

        --journals=STR
            Database(s) with official journal names, abbreviations, and acronym.
            Default: "pnas,physics,mechanics".

        --no-title
            Remove title from BibTeX file.

        --author-sep=STR
            Character to separate authors' initials. Default: "".

        --dot-space=<str>
            Character separating abbreviation dots. Default: "".

        --ignore-case
            Do not protect case of title.

        --ignore-math
            Do not apply math-mode fix.

        --ignore-unicode
            Do not apply unicode fix.

        --verbose
            Show interpretation.

        -v, --version
            Show version.

        -h, --help
            Show help.

    (c - MIT) T.W.J. de Geus | tom@geus.me | www.geus.me | github.com/tdegeus/GooseBib
    """

    funcname = inspect.getframeinfo(inspect.currentframe()).function
    doc = textwrap.dedent(inspect.getdoc(globals()[funcname]))

    class Parser(argparse.ArgumentParser):
        def print_help(self):
            print(doc)

    parser = Parser()
    parser.add_argument("--author-sep", type=str, default="")
    parser.add_argument("--dot-space", type=str, default="")
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("--ignore-math", action="store_true")
    parser.add_argument("--ignore-unicode", action="store_true")
    parser.add_argument("--journals", type=str, default="pnas,physics,mechanics")
    parser.add_argument("--no-title", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("-j", "--journal-type", type=str, default="abbreviation")
    parser.add_argument("-v", "--version", action="version", version=version)
    parser.add_argument("input", type=str)
    parser.add_argument("output", type=str)
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        raise OSError(f'"{args.input:s}" does not exist')

    if os.path.isdir(args.output):
        args.output = os.path.join(args.output, os.path.split(args.input)[-1])

    data = clean(
        args.input,
        journal_type=args.journal_type,
        journal_database=args.journals.split(","),
        sep_name=args.author_sep,
        sep=args.dot_space,
        title=not args.no_title,
        protect_math=not args.ignore_math,
        rm_unicode=not args.ignore_unicode,
    )

    with open(args.output, "w") as file:
        file.write(data)

    if args.verbose:
        simple = select(args.input)
        sys.stdout.writelines(difflib.unified_diff(simple, data))
