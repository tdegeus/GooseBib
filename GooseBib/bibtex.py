import re
from functools import singledispatch

import bibtexparser

from . import recognise
from . import reformat


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
    :param output: Output BibTeX.
    :param sep_name: Separate name initials (e.g. "", " ").
    :param sep: Separate abbreviations in title and author: replace ". " e.g. by "." or ". ".
    :param title: Include title of relevant fields.
    :param protect_math: Apply fix of :py:func:`reformat.protect_math`.
    :param rm_unicode: Apply fix of :py:func:`reformat.rm_unicode`.
    """

    for entry in data.entries:

        # fix known Mendeley bugs : todo replace by journals
        if "journal" in entry:
            if entry["journal"] == "EPL (Europhysics Lett.":
                entry["journal"] = "EPL (Europhys. Lett.)"
            if entry["journal"] == "Science (80-. ).":
                entry["journal"] = "Science"

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

    return select(data, fields=selection(use_bibtexparser=True))


@clean.register(str)
def _(data, *args, **kwargs):

    with open(data) as file:
        bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

    bib = clean(bib, *args, **kwargs)

    return bibtexparser.dumps(bib)
