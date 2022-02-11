import argparse
import difflib
import inspect
import io
import os
import re
import textwrap
import warnings
from collections import OrderedDict
from functools import singledispatch
from typing import Union

import bibtexparser
import click
import numpy as np

from . import journals
from . import recognise
from . import reformat
from ._version import version


def read_display_order(bibtype: str, key: str, string: str) -> list[str]:
    """
    Read order of fields of an entry.
    Currently matching ignores cases, this should lead to erroneous results if only case is used
    to distinguish entries (not sure if that is legal in BibTeX).

    :param bibtype: "article", "book", "misc", etc.
    :param key: The citation key.
    :param string: A BibTeX file.
    """

    data = re.compile(r"\@" + bibtype + r"\{" + key + r".*", flags=re.IGNORECASE).split(string)[1]
    data = re.split(r"(.*)(\n\@\w*\{)", data)[0]
    return [i[1] for i in re.findall(r"([\n\t\ ]*)([\w\_\-]*)([\ ]?=)(.*)", data)]


class MyBibTexWriter(bibtexparser.bwriter.BibTexWriter):
    """
    Overload of ``bibtexparser.bwriter.BibTexWriter`` acting on an extra internal field
    "display_order" to preserve the order of each item.
    """

    def _entry_to_bibtex(self, entry):
        self.display_order = entry.pop("display_order", [])
        return bibtexparser.bwriter.BibTexWriter._entry_to_bibtex(self, entry)


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
def select(
    data,
    fields: Union[dict[list[str]], list[str]] = None,
    ensure_link: bool = True,
    remove_url: bool = True,
):
    """
    Remove unnecessary fields for BibTex file.

    :param data:
        The BibTeX database (file, string, or bibtexparser instance).

    :param fields:
        Fields to keep per entry type (default from :py:fund:`selection`).
        If a list is specified all entry types are treated the same.

    :param ensure_link:
        Add URL to ``fields`` if no ``doi`` or ``arxivid`` is present.

    :param remove_url:
        Remove URL with either a ``doi`` or an ``arxivid`` is present.
    """

    if fields is None:
        fields = selection(use_bibtexparser=True)

    if isinstance(fields, list):
        ret = {}
        for entry in data.entries:
            if entry["ENTRYTYPE"] not in ret:
                ret[entry["ENTRYTYPE"]] = ["ID", "ENTRYTYPE"] + fields
        fields = ret

    for entry in data.entries:

        select = fields[entry["ENTRYTYPE"]] + ["display_order"]

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

    writer = MyBibTexWriter()
    parser = bibtexparser.bparser.BibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )
    return writer.write(select(bibtexparser.loads(data, parser=parser), *args, **kwargs))


@select.register(io.IOBase)
def _(data, *args, **kwargs):

    writer = MyBibTexWriter()
    parser = bibtexparser.bparser.BibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )

    return writer.write(select(bibtexparser.load(data, parser=parser), *args, **kwargs))


def _parse_plain(string: str) -> bibtexparser.bibdatabase.BibDatabase:
    """
    Parse with as little as fixes possible
    """
    parser = bibtexparser.bparser.BibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )

    try:
        return bibtexparser.loads(string)
    except:
        warnings.warn("Light parsing for diff failed, trying aggressive parsing", Warning)
        return bibtexparser.loads(string, parser=parser)


def unique(data: bibtexparser.bibdatabase.BibDatabase, merge: bool = True):
    """
    Remove duplicate keys.
    :param data: The BibTeX database.
    :param merge: Try to keep as many keys as possible.
    :return: The BibTeX database.
    """

    keys = [entry["ID"] for entry in data.entries]
    _, ifoward, ibackward = np.unique(keys, return_index=True, return_inverse=True)

    if ifoward.size == len(keys):
        return data

    index = np.arange(ibackward.size)
    renum = index[ifoward][ibackward]
    old = index[index != renum]
    new = renum[index != renum]

    entries = [data.entries[i] for i in ifoward]
    merged = []

    for o, n in zip(old, new):
        merged.append(data.entries[o]["ID"])
        if merge:
            for key in data.entries[o]:
                if key not in data.entries[n]:
                    entries[n][key] = data.entries[o][key]

    sorter = np.argsort(ifoward)
    data.entries = [entries[i] for i in sorter]

    merged = "- " + "\n- ".join([str(i) for i in np.unique(merged)])
    warnings.warn(f"Merging duplicates, please check:\n{merged}", Warning)

    return data


@singledispatch
def clean(
    data,
    journal_type: str = "abbreviation",
    journal_database: list[str] = ["pnas", "physics", "mechanics"],
    sep_name: str = "",
    sep_journal: str = "",
    title: bool = True,
    protect_math: bool = True,
    rm_unicode: bool = True,
    rm_comment: bool = True,
    rm_string: bool = True,
    raw: str = None,
):
    r"""
    Clean a BibTeX database:
    *   Remove unnecessary fields (see :py:func:`GooseBib.bibtex.select`).
    *   Unify the formatting of authors (see :py:func:`GooseBib.reformat.abbreviate_firstname`).
    *   Ensure proper math formatting (see :py:func:`GooseBib.reformat.protect_math`).
    *   Convert unicode to TeX (see :py:func:`GooseBib.reformat.rm_unicode`).
    *   Fill digital identifier if it is not present by can be found from a different field
        (see :py:func:`GooseBib.recognise.doi` and :py:func:`GooseBib.recognise.arxivid`).

    :param data: The BibTeX database (file, string, or bibtexparser instance).
    :param journal_type: Use journal: "title", "abbreviation", or "acronym".
    :param journal_database: Database(s) with official journal names, abbreviations, and acronym.
    :param sep_name: Separate name initials (e.g. "", " ").
    :param sep_journal: Separate abbreviations in journal: replace ". " e.g. by ". " or ".\ ".
    :param title: Include title of relevant fields.
    :param protect_math: Apply fix of :py:func:`reformat.protect_math`.
    :param rm_unicode: Apply fix of :py:func:`reformat.rm_unicode`.
    :param rm_comment: Remove @comment.
    :param rm_string: Remove @string (as it is interpreted by the parser).
    """

    data = unique(data, merge=True)

    if rm_comment:
        data.comments = []

    if rm_string:
        data.strings = OrderedDict()

    journal_type = journal_type.lower()
    journal_database = [journal_database] if isinstance(journal_database, str) else journal_database

    revus = []
    ignored_authors = []

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
                names = re.split(r"\ and\ ", entry[key].replace("\n", " "), flags=re.IGNORECASE)
                if not re.match(r"(\{)(.*)(\})", entry[key]):
                    names = bibtexparser.customization.getnames(names)
                names = [reformat.abbreviate_firstname(i, sep_name) for i in names]
                entry[key] = " and ".join(names)

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
        for key in ["journal"]:
            if key in entry:
                entry[key] = entry[key].replace(". ", f".{sep_journal} ")
                entry[key] = entry[key].replace(r".\ ", f".{sep_journal} ")

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

        # add internal display order to preserve order in output
        # (add test just in case something went wrong)
        if raw is not None:
            display_order = read_display_order(entry["ENTRYTYPE"], entry["ID"], raw)
            if all([i in entry for i in display_order]):
                entry["display_order"] = display_order

    if len(ignored_authors) > 0:
        ignored_authors = "- " + "\n- ".join([str(i) for i in np.unique(ignored_authors)])
        warnings.warn(f"Protected authors found, please check:\n{ignored_authors}", Warning)

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

    writer = MyBibTexWriter()
    parser = bibtexparser.bparser.BibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )
    return writer.write(clean(bibtexparser.loads(data, parser=parser), *args, **kwargs, raw=data))


@clean.register(io.IOBase)
def _(data, *args, **kwargs):

    writer = MyBibTexWriter()
    parser = bibtexparser.bparser.BibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )
    return writer.write(
        clean(bibtexparser.load(data, parser=parser), *args, **kwargs, raw=data.read())
    )


@singledispatch
def format_journal_arxiv(data, fmt: str, journal_database: list[str] = ["arxiv"]):
    """
    Format the journal entry for arXiv preprints.
    Use "{}" in the formatter to include the arxivid.

    :param data: The BibTeX database (file, string, or bibtexparser instance).
    :param fmt: Formatter, e.g. "Preprint" or "Preprint: arXiv {}".
    :param journal_database: Database(s) with known arXiv variants.
    """

    for entry in data.entries:
        if "arxivid" in entry and "doi" not in entry:
            if "journal" not in entry:
                entry["journal"] = fmt.format(entry["arxivid"])
            elif "arxiv" in entry["journal"].lower() or "preprint" in entry["journal"].lower():
                entry["journal"] = fmt.format(entry["arxivid"])

    if len(journal_database) > 0:

        revus = []
        for entry in data.entries:
            if "journal" in entry:
                revus.append(entry["journal"])

        db = journals.load(*journal_database)
        new = db.map2name(revus)
        mapping = {o: n for o, n in zip(revus, new)}

        for entry in data.entries:
            if "journal" in mapping and "arxivid" in entry and "doi" not in entry:
                entry["journal"] = fmt.format(entry["arxivid"])

    return data


@format_journal_arxiv.register(str)
def _(data, *args, **kwargs):

    writer = MyBibTexWriter()
    parser = bibtexparser.bparser.BibTexParser()
    return writer.write(
        format_journal_arxiv(bibtexparser.load(data, parser=parser), *args, **kwargs, raw=data)
    )


@format_journal_arxiv.register(io.IOBase)
def _(data, *args, **kwargs):

    writer = MyBibTexWriter()
    parser = bibtexparser.bparser.BibTexParser()
    return writer.write(
        format_journal_arxiv(
            bibtexparser.load(data, parser=parser), *args, **kwargs, raw=data.read()
        )
    )


def GbibClean():
    r"""
    Clean a BibTeX database, stripping it from unnecessary fields,
    unifying the formatting of authors, and ensuring the proper special characters and
    math mode settings.

    :usage:

        GbibClean [options] <input>... <output>

    :arguments:

        <input>
            Input BibTeX-file(s).

        <output>
            Output file.
            If ``<output>`` is a directory, it is appended with the (first) filename of ``<input>``.
            Multiple input files are combined to a single output file, in every way they are
            considered as concatenated.
            See ``--in-place`` for different behaviour.

    :options:

        -j, --journal-type=STR (title, abbreviation, acronym)
            Unify journal titles (if recognised).
            If "acronym" is selected, "abbreviation" is used for journals without an "acronym".
            Default: abbreviation.

        --journals=STR (physics, mechanics, arxiv, pnas, pnas-usa, ...)
            Database(s) with official journal names, abbreviations, and acronyms.
            To make no modifications to journals use ``--journal=""``.
            Default: "pnas,physics,mechanics".

        --arxiv=STR
            Format arXiv preprints using a specific formatter.
            Use "{}" in the formatter to include the arxivid, e.g.: "arXiv preprint {}".

        --no-title
            Remove title from BibTeX file.

        --author-sep=STR
            Character to separate authors' initials.
            Default: "".

        --journal-sep=<str>
            Separate journal abbreviations by ".{sep} "
            Default: "".

        --ignore-case
            Do not protect case of title.

        --ignore-math
            Do not apply math-mode fix.

        --ignore-unicode
            Do not apply unicode fix.

        --diff=STR
            Write diff to HTML file which shows the old and the reformatted file side-by-side.

        --diff-type=STR (raw, plain, all, select)
            Show difference between ``<output>`` and compared to ``<input>`` that is:
            *   raw: not parsed at all (can lead to a mess because of sorting).
            *   plain: parsed as little as possible.
            *   select: parsed as little as possible, but with only selected output fields.
            Default: select.

        --diff-keys=STR
            Limit diff to certain keys separated by spaces (e.g. "author,journal,doi").

        --in-place
            If specified, each input file is separately treated and formatted in-place.

        -f, --force
            Force overwrite of existing files.

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
    parser.add_argument("--arxiv", type=str)
    parser.add_argument("--author-sep", type=str, default="")
    parser.add_argument("--diff", type=str)
    parser.add_argument("--diff-type", type=str, default="select")
    parser.add_argument("--diff-keys", type=str)
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("--ignore-math", action="store_true")
    parser.add_argument("--ignore-unicode", action="store_true")
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--journal-sep", type=str, default="")
    parser.add_argument("--journals", type=str, default="pnas,physics,mechanics")
    parser.add_argument("--no-title", action="store_true")
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("-j", "--journal-type", type=str, default="abbreviation")
    parser.add_argument("-v", "--version", action="version", version=version)
    parser.add_argument("files", nargs="*", type=str)
    args = parser.parse_args()

    # read input/output filepaths

    if args.in_place:

        assert not args.diff
        assert not args.force

        sourcepaths = args.files
        outpaths = sourcepaths
        assert all([os.path.isfile(i) for i in sourcepaths])

    else:

        if len(args.files) < 2:
            raise OSError("Specify <input> and <output>")

        output = args.files[-1]
        sources = args.files[:-1]
        source = ""

        if os.path.isdir(output):
            output = os.path.join(output, os.path.split(sources[0])[-1])

        sourcepaths = [None]
        outpaths = [output]

        for filepath in sources:
            if not os.path.isfile(filepath):
                raise OSError(f'"{filepath}" does not exist')
            with open(filepath) as file:
                source += file.read()

        if not args.force:

            overwrite = []

            for outpath in outpaths:
                if os.path.isfile(outpath):
                    overwrite += [os.path.normpath(outpath)]

            if args.diff:
                if os.path.isfile(args.diff):
                    overwrite += [os.path.normpath(args.diff)]

            if len(overwrite) > 0:
                files = ", ".join(overwrite)
                if not click.confirm(f'Overwrite "{files}"?'):
                    raise OSError("Cancelled")

    # formatting

    for sourcepath, outpath in zip(sourcepaths, outpaths):

        if sourcepath is not None:
            with open(sourcepath) as file:
                source = file.read()

        data = clean(
            source,
            journal_type=args.journal_type,
            journal_database=args.journals.split(","),
            sep_name=args.author_sep,
            sep_journal=args.journal_sep,
            title=not args.no_title,
            protect_math=not args.ignore_math,
            rm_unicode=not args.ignore_unicode,
        )

        print(data)
        print("---")
        print(bibtexparser.dumps(bibtexparser.loads(data)))

        if data != bibtexparser.dumps(bibtexparser.loads(data)):
            warnings.warn("Re-parsing is failing, there might be dangling {}", Warning)

        if args.arxiv:
            data = format_journal_arxiv(data, args.arxiv)

        with open(outpath, "w") as file:
            file.write(data)

        if args.diff:

            if args.diff_type.lower() == "raw":
                simple = source
            elif args.diff_type.lower() == "plain":
                simple = bibtexparser.dumps(_parse_plain(source))
            elif args.diff_type.lower() == "select":
                simple = bibtexparser.dumps(select(_parse_plain(source)))
            else:
                raise OSError("Unknown option for --diff-type")

            if args.diff_keys:
                simple = bibtexparser.dumps(
                    select(
                        _parse_plain(simple),
                        fields=args.diff_keys.split(","),
                        ensure_link=False,
                        remove_url=False,
                    )
                )
                data = bibtexparser.dumps(
                    select(
                        bibtexparser.loads(data),
                        fields=args.diff_keys.split(","),
                        ensure_link=False,
                        remove_url=False,
                    )
                )

            diff = difflib.HtmlDiff(wrapcolumn=100).make_file(
                simple.splitlines(keepends=True), data.splitlines(keepends=True)
            )

            with open(args.diff, "w") as file:
                file.write(diff)
