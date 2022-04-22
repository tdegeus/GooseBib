import argparse
import difflib
import inspect
import io
import os
import re
import textwrap
import warnings
from collections import defaultdict
from collections import OrderedDict
from functools import singledispatch
from typing import Union

import arxiv
import bibtexparser
import click
import numpy as np
import tqdm
import yaml

from . import journals
from . import recognise
from . import reformat
from ._version import version


def yaml_dump(filename, data, force=False):
    r"""
    Dump data to YAML file.

    :type filename: str
    :param filename: The output filename.

    :type data: list, dict
    :param data: The data to dump.

    :type force: bool, optional
    :param force: Do not prompt to overwrite file.
    """

    dirname = os.path.dirname(filename)

    if not force:
        if os.path.isfile(filename):
            if not click.confirm(f'Overwrite "{filename:s}"?'):
                raise OSError("Cancelled")
        elif not os.path.isdir(dirname) and len(dirname) > 0:
            if not click.confirm(f'Create "{os.path.dirname(filename):s}"?'):
                raise OSError("Cancelled")

    if not os.path.isdir(dirname) and len(dirname) > 0:
        os.makedirs(os.path.dirname(filename))

    with open(filename, "w") as file:
        yaml.dump(data, file)


def read_display_order(bibtex_str: str, tabsize: int = 2) -> (dict, int):
    """
    Read order of fields of all entries.

    :param bibtex_str: A BibTeX 'file'.
    :param tabsize: Replace "\t" by a number of spaces.
    :return:
        A dictionary with a list of fields per key.
        The typical indentation.
    """

    ret = {}
    indent = []

    matches = list(re.finditer(r"(\@\w*\{)", bibtex_str, re.I))

    for m in range(len(matches)):

        i = matches[m].start()

        if m < len(matches) - 1:
            j = matches[m + 1].start()
            entry = bibtex_str[i:j]
        else:
            entry = bibtex_str[i:]

        components = re.split(r"(.*)(\@\w*\{)", entry)

        if components[2].lower() in ["@string{", "@comment{", "@preamble{"]:
            continue

        key, data = components[3].split(",", 1)
        find = re.findall(r"([\n\t\ ]*)([\w\_\-]*)([\ ]?=)(.*)", data)
        ret[key] = [i[1] for i in find]
        indent += [len("".join(i[0].replace("\t", tabsize * " ").splitlines())) for i in find]

    if len(indent) == 0:
        indent = 0
    else:
        indent = int(np.ceil(np.mean(indent)))

    return ret, indent


def get_doi(entry: dict) -> str:
    """
    Get the doi from an entry. Returns ``None`` if no doi was found.

    :param entry: The bib-entry.
    :return: The doi or ``None``.
    """

    if "doi" in entry:
        return entry["doi"]

    return recognise.doi(
        *[
            val
            for key, val in entry.items()
            if key not in ["arxivid", "eprint", "DISPLAY_ORDER", "INDENT"]
        ]
    )


def get_arxivid(entry: dict) -> str:
    """
    Get the arxivid from an entry. Returns ``None`` if no arxivid was found.

    :param entry: The bib-entry.
    :return: The arxivid or ``None``.
    """

    if "arxivid" in entry:
        return entry["arxivid"]

    return recognise.arxivid(
        *[val for key, val in entry.items() if key not in ["doi", "DISPLAY_ORDER", "INDENT"]]
    )


def get_identifiers(entry: dict) -> dict:
    """
    Get entry's identifiers.

    :param entry: The bib-entry.
    :return: The identifiers found.
    """

    ret = {}

    doi = get_doi(entry)
    arxivid = get_arxivid(entry)

    if doi is not None:
        if arxivid is None:
            pattern = re.compile(r"(10.48550/arXiv.)([^\s]*)(.*)", re.IGNORECASE)
            if re.match(pattern, doi):
                arxivid = re.split(pattern, doi)[1].strip()

    if doi is not None:
        ret["doi"] = doi

    if arxivid is not None:
        ret["arxivid"] = arxivid

    return ret


class MyBibTexWriter(bibtexparser.bwriter.BibTexWriter):
    """
    Overload of ``bibtexparser.bwriter.BibTexWriter`` acting on an extra internal field
    "DISPLAY_ORDER" to preserve the order of each item.
    """

    def __init__(self, *args, **kwargs):
        sort = kwargs.pop("sort_entries", False)
        super().__init__(self, *args, **kwargs)
        if not sort:
            self.order_entries_by = []

    def _entry_to_bibtex(self, entry):
        self.display_order = entry.pop("DISPLAY_ORDER", [])
        self.indent = entry.pop("INDENT", " ")
        return bibtexparser.bwriter.BibTexWriter._entry_to_bibtex(self, entry)

    def write(self, *args, **kwargs):
        ret = bibtexparser.bwriter.BibTexWriter.write(self, *args, **kwargs)
        return ret.rstrip() + "\n"


class MyBibTexParser(bibtexparser.bparser.BibTexParser):
    """
    Overload of ``bibtexparser.bparser.BibTexParser`` adding an extra internal field
    "DISPLAY_ORDER" to preserve the order of each item.
    """

    def parse(self, bibtex_str, *args, **kwargs):

        order, indent = read_display_order(bibtex_str, kwargs.pop("tabsize", 2))
        data = bibtexparser.bparser.BibTexParser.parse(self, bibtex_str, *args, **kwargs)

        for key in order:
            order[key] = list(map(self.alt_dict.get, order[key], order[key]))

        for entry in data.entries:
            entry["INDENT"] = " " * indent
            entry["DISPLAY_ORDER"] = order.get(entry["ID"], [])

        return data


def parse(bibtex_str: str, aggresive: bool = False) -> str:
    """
    Parse a BibTeX string once.

    :param aggresive: Use aggressive interpretation strategy.
    """

    writer = MyBibTexWriter()

    if aggresive:
        parser = MyBibTexParser(
            homogenize_fields=True,
            ignore_nonstandard_types=True,
            add_missing_from_crossref=True,
            common_strings=True,
        )
    else:
        parser = MyBibTexParser()

    return writer.write(parser.parse(bibtex_str))


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
        base += ["ID", "ENTRYTYPE", "DISPLAY_ORDER", "INDENT"]

    base += ["author", "title", "year", "doi", "arxivid"]

    return dict(
        article=base + ["journal", "volume", "number", "pages"],
        unpublished=base,
        inproceedings=base + ["booktitle", "editor", "publisher", "volume", "number", "pages"],
        book=base + ["edition", "editor", "publisher", "isbn", "volume", "pages"],
        inbook=base + ["edition", "editor", "publisher", "isbn", "volume", "pages"],
        incollection=base + ["booktitle", "edition", "publisher", "isbn", "volume", "pages"],
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
        Fields to keep per entry type (default from :py:func:`selection`).
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
                ret[entry["ENTRYTYPE"]] = ["ID", "ENTRYTYPE", "DISPLAY_ORDER", "INDENT"] + fields
        fields = ret

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

    writer = MyBibTexWriter()
    parser = MyBibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )
    return writer.write(select(parser.parse(data), *args, **kwargs))


@select.register(io.IOBase)
def _(data, *args, **kwargs):

    writer = MyBibTexWriter()
    parser = MyBibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )

    return writer.write(select(parser.parse(data), *args, **kwargs))


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
    data: bibtexparser.bibdatabase.BibDatabase,
    journal_type: str = "abbreviation",
    journal_database: list[str] = ["pnas", "physics", "mechanics"],
    sep_name: str = "",
    sep_journal: str = "",
    title: bool = True,
    protect_math: bool = True,
    rm_unicode: bool = True,
    rm_comment: bool = True,
    rm_string: bool = True,
) -> bibtexparser.bibdatabase.BibDatabase:
    r"""
    Clean a BibTeX database:
    *   Remove unnecessary fields (see :py:func:`GooseBib.bibtex.select`).
    *   Unify the formatting of authors (see :py:func:`GooseBib.reformat.abbreviate_firstname`).
    *   Ensure proper math formatting (see :py:func:`GooseBib.reformat.protect_math`).
    *   Convert unicode to TeX (see :py:func:`GooseBib.reformat.rm_unicode`).
    *   Fill digital identifier if it is not present by can be found from a different field.

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
    :param sort_entries: Sort entries in output (only for string or file input).
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

        # find identifiers
        iden = get_identifiers(entry)
        for key in iden:
            if key not in entry:
                entry[key] = iden[key]

        # apply arXiv's doi
        if "arxivid" in entry:
            if "doi" not in entry:
                entry["doi"] = "10.48550/arXiv." + entry.pop("arxivid")
            elif entry["doi"] == "10.48550/arXiv." + entry["arxivid"]:
                del entry["arxivid"]

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
            entry["doi"] = re.sub(r"[\{}]?[\\]+\_[\}]?", r"\\_", entry["doi"])
        # -
        if "url" in entry:
            entry["url"] = entry["url"].replace(r"{\_}", r"\_")
            entry["url"] = re.sub(r"[\{}]?[\\]+\_[\}]?", r"\\_", entry["url"])
            entry["url"] = entry["url"].replace("{~}", "~")
            entry["url"] = entry["url"].replace(r"\&", "&")
        # -
        if "url" in entry:
            entry["url"] = _subr(re.compile(r"({)([^}])(})", re.UNICODE), r"\2", entry["url"])

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
def _(data: str, *args, **kwargs) -> str:

    writer = MyBibTexWriter(sort_entries=kwargs.pop("sort_entries", False))
    parser = MyBibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )
    return writer.write(clean(parser.parse(data), *args, **kwargs))


@clean.register(io.IOBase)
def _(data: io.IOBase, *args, **kwargs) -> str:

    writer = MyBibTexWriter(sort_entries=kwargs.pop("sort_entries", False))
    parser = MyBibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )
    return writer.write(clean(parser.parse(data), *args, **kwargs))


@singledispatch
def format_journal_arxiv(data, fmt: str, journal_database: list[str] = ["arxiv"]):
    """
    Format the journal entry for arXiv preprints.
    Use "{}" in the formatter to include the arxivid.

    :param data: The BibTeX database (file, string, or bibtexparser instance).
    :param fmt: Formatter, e.g. "Preprint" or "Preprint: arXiv {}".
    :param journal_database: Database(s) with known arXiv variants.
    """

    search = r"(" + re.escape("10.48550/arXiv.") + r")(.*)"
    pattern = ["arxiv", "preprint", "submitted", "in preparation"]

    for entry in data.entries:

        if "doi" in entry:
            if not re.match(search, entry["doi"]):
                continue

        if "arxivid" in entry:
            arxivid = entry["arxivid"]
        elif "doi" in entry:
            arxivid = re.split(search, entry["doi"])
            if len(arxivid) != 4:
                continue
            arxivid = arxivid[2]
        else:
            continue

        if "journal" not in entry:
            entry["journal"] = fmt.format(arxivid)
        else:
            for i in pattern:
                if i in entry["journal"].lower():
                    entry["journal"] = fmt.format(arxivid)
                    break

    if len(journal_database) > 0:

        revus = []
        for entry in data.entries:
            if "journal" in entry:
                revus.append(entry["journal"])

        db = journals.load(*journal_database)
        new = db.map2name(revus)
        mapping = {o: n for o, n in zip(revus, new)}

        for entry in data.entries:
            if "journal" in mapping and "arxivid" in entry:
                if "doi" in entry:
                    if not re.match(search, entry["doi"]):
                        continue
                entry["journal"] = fmt.format(arxivid)

    return data


@format_journal_arxiv.register(str)
def _(data, *args, **kwargs):

    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    return writer.write(format_journal_arxiv(parser.parse(data), *args, **kwargs))


@format_journal_arxiv.register(io.IOBase)
def _(data, *args, **kwargs):

    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    return writer.write(format_journal_arxiv(parser.parse(data), *args, **kwargs))


def _GbibClean_parser():
    """
    Return parser for :py:func:`GbibClean`.
    """

    class BlankLinesHelpFormatter(argparse.RawTextHelpFormatter):
        def _split_lines(self, text, width):
            return super()._split_lines(text, width) + [""]

    parser = argparse.ArgumentParser(
        formatter_class=BlankLinesHelpFormatter,
        description=textwrap.dedent(
            """\
            Clean a BibTeX database:
            *   Stripping it from unnecessary fields.
            *   Unifying the formatting of authors.
            *   Ensuring the proper special characters and math mode settings.
            *   Removing duplicates.
            *   Finding/unifying arxivid and doi.

            This script preserves order to help tracking changes.
            """
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file (required unless ``--in-place`` is used).",
    )

    parser.add_argument(
        "--in-place",
        action="store_true",
        help="If specified, each input file is separately treated and formatted in-place.",
    )

    parser.add_argument(
        "-j",
        "--journal-type",
        type=str,
        default="abbreviation",
        help=textwrap.dedent(
            """\
            Unify journal titles (if recognised).
            If "acronym" is selected, "abbreviation" is used for journals without an "acronym".
            """
        ),
    )

    parser.add_argument(
        "--journals",
        type=str,
        default="pnas,physics,mechanics",
        help=textwrap.dedent(
            """\
            Database(s) with official journal names, abbreviations, and acronyms.
            To make no modifications to journals use ``--journal=""``.
            """
        ),
    )

    parser.add_argument(
        "--arxiv",
        type=str,
        help=textwrap.dedent(
            """\
            Format arXiv preprints using a specific formatter.
            Use "{}" in the formatter to include the arxivid, e.g.: "arXiv preprint {}".
            """
        ),
    )

    parser.add_argument(
        "--no-title",
        action="store_true",
        help="Remove title from BibTeX file.",
    )

    parser.add_argument(
        "--author-sep",
        type=str,
        default="",
        help="Character to separate authors' initials.",
    )

    parser.add_argument(
        "--journal-sep",
        type=str,
        default="",
        help="Character to separate journal abbreviations.",
    )

    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="Do apply case protection of title.",
    )

    parser.add_argument(
        "--ignore-math",
        action="store_true",
        help="Do not apply math-mode fix.",
    )

    parser.add_argument(
        "--ignore-unicode",
        action="store_true",
        help="Do not apply unicode fix.",
    )

    parser.add_argument(
        "--sort-entries",
        action="store_true",
        help="Sort output by entries.",
    )

    parser.add_argument(
        "--diff",
        type=str,
        help=textwrap.dedent(
            """\
            Write diff to HTML file which shows the old and the reformatted file side-by-side.
            See ``difflib.HtmlDiff.make_file``.
            """
        ),
    )

    parser.add_argument(
        "--diff-context",
        type=bool,
        default=False,
        help="Show contextual differences. See ``difflib.HtmlDiff.make_file``.",
    )

    parser.add_argument(
        "--diff-numlines",
        type=int,
        default=5,
        help="Controls the number of context lines which surround the difference highlights.",
    )

    parser.add_argument(
        "--diff-type",
        type=str,
        default="select",
        help=textwrap.dedent(
            """\
            Show difference between ``<output>`` and compared to ``<input>`` that is:
            *   raw: not parsed at all (can lead to a mess because of sorting).
            *   plain: parsed as little as possible.
            *   select: parsed as little as possible, but with only selected output fields.
            """
        ),
    )

    parser.add_argument(
        "--diff-keys",
        type=str,
        help='Limit diff to certain keys separated by spaces (e.g. "author,journal,doi").',
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite of existing output file.",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=version,
    )

    parser.add_argument(
        "files",
        nargs="*",
        type=str,
        help=textwrap.dedent(
            """\
            Input files.
            If using ``--in-place`` files are treated separately.
            Otherwise they are merged to single output file.
            """
        ),
    )

    return parser


def GbibClean():
    """
    Command-line tool to clean a BibTeX database, see ``--help``.
    """

    parser = _GbibClean_parser()
    args = parser.parse_args()

    # read input/output filepaths

    if args.in_place:

        assert args.output is None
        assert not args.diff
        assert not args.force

        sourcepaths = args.files
        outpaths = sourcepaths
        assert all([os.path.isfile(i) for i in sourcepaths])

    else:

        if args.output is None:
            raise OSError("Specify --output STR")
        if os.path.isdir(args.output):
            raise OSError("--output cannot be a directory name")

        source = ""
        sourcepaths = [None]
        outpaths = [args.output]

        for filepath in args.files:
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
            sort_entries=args.sort_entries,
        )

        if data != parse(data):
            warnings.warn("Re-parsing is failing, there might be dangling {}", Warning)

        if args.arxiv:
            data = format_journal_arxiv(data, args.arxiv)

        if data == source:
            return 0

        with open(outpath, "w") as file:
            file.write(data)

        if args.diff is not None:

            if args.diff_type.lower() == "raw":
                simple = source
            elif args.diff_type.lower() == "plain":
                try:
                    simple = parse(source)
                except:
                    simple = parse(source, aggresive=True)
                    warnings.warn("Light parsing for diff failed", Warning)
            elif args.diff_type.lower() == "select":
                simple = select(source)
            else:
                raise OSError("Unknown option for --diff-type")

            if args.diff_keys:
                simple = select(
                    simple,
                    fields=args.diff_keys.split(","),
                    ensure_link=False,
                    remove_url=False,
                )
                data = select(
                    data,
                    fields=args.diff_keys.split(","),
                    ensure_link=False,
                    remove_url=False,
                )

            diff = difflib.HtmlDiff(wrapcolumn=100).make_file(
                simple.splitlines(keepends=True),
                data.splitlines(keepends=True),
                numlines=args.diff_numlines,
                context=args.diff_context,
            )

            with open(args.diff, "w") as file:
                file.write(diff)


def GbibShowAuthorRename():
    r"""
    Show author rename if ``GbibClean`` is applied.
    """

    funcname = inspect.getframeinfo(inspect.currentframe()).function
    doc = textwrap.dedent(inspect.getdoc(globals()[funcname]))

    class Parser(argparse.ArgumentParser):
        def print_help(self):
            print(doc)

    parser = Parser()
    parser.add_argument("-o", "--output", type=str)
    parser.add_argument("--author-sep", type=str, default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("files", nargs="+", type=str)
    args = parser.parse_args()

    assert all([os.path.isfile(i) for i in args.files])

    source = ""

    for filepath in args.files:
        with open(filepath) as file:
            source += file.read()

    parser = MyBibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )

    data = parser.parse(source)
    old = []
    new = []

    for entry in data.entries:
        for key in ["author", "editor"]:
            if key in entry:
                names = re.split(r"\ and\ ", entry[key].replace("\n", " "), flags=re.IGNORECASE)
                old += names
                if not re.match(r"(\{)(.*)(\})", entry[key]):
                    names = bibtexparser.customization.getnames(names)
                new += [reformat.abbreviate_firstname(i, args.author_sep) for i in names]

    _, index = np.unique(old, return_index=True)
    old = [old[i] for i in index]
    new = [new[i] for i in index]

    if args.all:
        opts = dict(context=False, numlines=1)
    else:
        opts = dict(context=True, numlines=0)

    diff = difflib.HtmlDiff(wrapcolumn=100).make_file(old, new, **opts)

    if args.output:
        with open(args.output, "w") as file:
            file.write(diff)
    else:
        print(diff)


def dbsearch_arxiv(
    data: bibtexparser.bibdatabase.BibDatabase,
    silent: bool = False,
) -> dict:
    """
    Check online databases (can be slow!).
    :param silent: Hide status bar.
    :return: Dictionary with discovered items.
    """

    output = defaultdict(lambda: defaultdict(list))

    # find arxivid based on journal doi

    for entry in tqdm.tqdm(data.entries, disable=silent):
        iden = get_identifiers(entry)
        if "arxivid" in iden:
            continue
        if "doi" not in iden:
            continue
        doi = iden["doi"]
        ret = []
        for result in arxiv.Search(query=f'"{doi}"').results():
            ret.append(re.sub(r"(http)(s?)(://arxiv.org/abs/)(.*)", r"\4", result.entry_id))
        for i in ret:
            output[entry["ID"]]["arxivid"].append(i)

    # arXiv preprint: check if journal id is present
    # possible optimisation: can be made faster to bluntly skip all entries that have a doi

    for entry in tqdm.tqdm(data.entries, disable=silent):
        iden = get_identifiers(entry)
        if "arxivid" not in iden:
            continue
        ret = []
        for result in arxiv.Search(id_list=[iden["arxivid"]]).results():
            ret.append(result.doi)
        if "doi" in iden:
            ret = [i for i in ret if i != iden["doi"]]
        for i in ret:
            output[entry["ID"]]["doi"].append(i)

    for key in output:
        output[key] = dict(output[key])

    return dict(output)


def _GbibDiscover_parser():
    """
    Return parser for :py:func:`GbibDiscover`.
    """

    class BlankLinesHelpFormatter(argparse.RawTextHelpFormatter):
        def _split_lines(self, text, width):
            return super()._split_lines(text, width) + [""]

    parser = argparse.ArgumentParser(
        formatter_class=BlankLinesHelpFormatter,
        description="Check online databases (can be slow!).",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=str,
        help="Output file (yaml).",
    )

    parser.add_argument(
        "--arxiv",
        action="store_true",
        help=textwrap.dedent(
            """\
            Check arXiv as follows:

            1.  If the item is an arXiv preprint: check if a journal doi was registered at arXiv.

            2.  If the item is a journal article: try to find the arxivid based on the journal doi.
            """
        ),
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite output file.",
    )

    parser.add_argument(
        "-s",
        "--silent",
        action="store_true",
        help="Run without status bars.",
    )

    parser.add_argument(
        "files",
        nargs="*",
        type=str,
        help="Bib-file(s) considered concatenated if more files are specified.",
    )

    return parser


def GbibDiscover():
    """
    Command-line tool to compare a BibTeX database for online databases, see ``--help``.
    """

    parser = _GbibDiscover_parser()
    args = parser.parse_args()

    source = ""

    for filepath in args.files:
        if not os.path.isfile(filepath):
            raise OSError(f'"{filepath}" does not exist')
        with open(filepath) as file:
            source += file.read()

    parser = MyBibTexParser(
        homogenize_fields=True,
        ignore_nonstandard_types=True,
        add_missing_from_crossref=True,
        common_strings=True,
    )

    data = parser.parse(source)
    output = {}

    if args.arxiv:
        output = dbsearch_arxiv(data, silent=args.silent)

    if len(output) > 0:
        yaml_dump(args.output, output, force=args.force)
