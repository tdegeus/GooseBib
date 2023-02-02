"""
For BibTeX files:

*   Automatic formatting.
*   Check if up-to-date.
*   Compare.
"""
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
from typing import Tuple
from typing import Union

import arxiv
import bibtexparser
import click
import numpy as np
import tqdm
import yaml
from bibtexparser.latexenc import latex_to_unicode
from numpy.typing import ArrayLike

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


def _get_doi(entry: dict) -> str:
    """
    Get the doi from an entry. See :py:func:`GooseBib.recognise.doi`.

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


def _get_arxivid(entry: dict) -> str:
    """
    Get the arxivid from an entry.  See :py:func:`GooseBib.recognise.arxivid`.

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
    Get entry's digital identifiers. The following identifiers are returned (if found):

    *   ``"doi"``
    *   ``"arxivid"``. Note that an arxivid as doi is returned (only) as arxivid.

    :param entry: The bib-entry.
    :return: Dictionary with the found identifiers.
    """

    ret = {}

    doi = _get_doi(entry)
    arxivid = _get_arxivid(entry)

    if doi is not None:
        if arxivid is None:
            pattern = re.compile(r"(10.48550/arXiv.)([^\s]*)(.*)", re.IGNORECASE)
            if re.match(pattern, doi):
                arxivid = re.split(pattern, doi)[2].strip()

    if doi is not None:
        ret["doi"] = doi

    if arxivid is not None:
        ret["arxivid"] = arxivid

    return ret


class MyBibTexWriter(bibtexparser.bwriter.BibTexWriter):
    """
    Overload of ``bibtexparser.bwriter.BibTexWriter`` acting on an extra internal field
    ``"DISPLAY_ORDER"`` to preserve the order of each item.
    In addition, there is an extra parameter ``sort_entries = False`` that controls if entries will
    by sorted based on the citation-key.
    """

    def __init__(self, *args, **kwargs):
        sort = kwargs.pop("sort_entries", False)
        common_strings = kwargs.pop("write_common_strings", False)
        super().__init__(self, *args, **kwargs)
        if not sort:
            self.order_entries_by = []
        self.common_strings = common_strings

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
    ``"DISPLAY_ORDER"`` to preserve the order of each item.
    """

    def __init__(self, *args, **kwargs):

        kwargs.setdefault("homogenize_fields", True)
        kwargs.setdefault("ignore_nonstandard_types", True)
        kwargs.setdefault("add_missing_from_crossref", True)
        kwargs.setdefault("common_strings", True)

        super().__init__(self, *args, **kwargs)

    def parse(self, bibtex_str, *args, **kwargs):

        order, indent = read_display_order(bibtex_str, kwargs.pop("tabsize", 2))
        data = bibtexparser.bparser.BibTexParser.parse(self, bibtex_str, *args, **kwargs)

        for key in order:
            order[key] = list(map(self.alt_dict.get, order[key], order[key]))

        for entry in data.entries:
            entry["INDENT"] = " " * indent
            entry["DISPLAY_ORDER"] = order.get(entry["ID"], [])

        return data

    def __add__(self, other):

        self.entries += other.entries
        self.comments += other.comments
        self.strings.update(other.strings)

        assert self.expect_multiple_parse == other.expect_multiple_parse
        assert self.common_strings == other.common_strings
        assert self.customization == other.customization
        assert self.ignore_nonstandard_types == other.ignore_nonstandard_types
        assert self.homogenize_fields == other.homogenize_fields
        assert self.interpolate_strings == other.interpolate_strings
        assert self.encoding == other.encoding
        assert self.add_missing_from_crossref == other.add_missing_from_crossref
        return self


def parse(bibtex_str: str, aggresive: bool = False) -> str:
    """
    Parse a BibTeX string once.

    :param aggresive: Use aggressive interpretation strategy.
    """

    writer = MyBibTexWriter()

    if aggresive:
        parser = MyBibTexParser()
    else:
        parser = MyBibTexParser(
            homogenize_fields=False,
            ignore_nonstandard_types=False,
            add_missing_from_crossref=False,
            common_strings=False,
        )

    return writer.write(parser.parse(bibtex_str))


def _subr(pattern, repl, string):
    """
    Recursive replacement: apply ``re.subn`` until no more replacement is made.
    """

    string, nsub = re.subn(pattern, repl, string)

    if nsub:
        return _subr(pattern, repl, string)

    return string


def selection(use_bibtexparser: bool = False) -> dict:
    """
    List of fields to keep in a BibTeX file to get a useful list of references:
    fields that are not in this selection may be useful for a database,
    but might only cloud BibTeX output.

    :param use_bibtexparser: Add bibtexparser specific fields to select (not part of BibTeX output).
    """

    base = []

    if use_bibtexparser:
        base += ["ID", "ENTRYTYPE", "DISPLAY_ORDER", "INDENT"]

    base += ["author", "title", "year", "doi", "arxivid"]
    book = ["booktitle", "editor", "publisher", "volume", "pages"]

    return dict(
        article=base + ["journal", "volume", "number", "pages"],
        unpublished=base,
        inproceedings=base + book + ["number"],
        book=base + ["edition", "editor", "publisher", "isbn", "volume", "pages"],
        inbook=base + ["edition", "editor", "publisher", "isbn", "volume", "pages"],
        incollection=base + book + ["edition", "isbn"],
        phdthesis=base + ["school", "isbn", "url"],
        techreport=base + ["institution", "isbn", "url"],
        misc=base + ["pages", "url"],
    )


@singledispatch
def select(
    data: list[dict],
    fields: Union[dict[list[str]], list[str]] = None,
    ensure_link: bool = True,
    remove_url: bool = True,
) -> list[dict]:
    """
    Remove unnecessary fields from BibTex database.

    :param data:
        The BibTeX database.

    :param fields:
        Fields to keep per entry type (default from :py:func:`selection`).
        If a list is specified all entry types are treated the same.

    :param ensure_link:
        Add URL to ``fields`` if no ``doi`` or ``arxivid`` is present.

    :param remove_url:
        Remove URL when either a ``doi`` or an ``arxivid`` is present.
    """

    if fields is None:
        fields = selection(use_bibtexparser=True)

    if isinstance(fields, list):
        ret = {}
        for entry in data:
            if entry["ENTRYTYPE"] not in ret:
                ret[entry["ENTRYTYPE"]] = ["ID", "ENTRYTYPE", "DISPLAY_ORDER", "INDENT"] + fields
        fields = ret

    for entry in data:

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


@select.register(bibtexparser.bibdatabase.BibDatabase)
def _(data, *args, **kwargs) -> bibtexparser.bibdatabase.BibDatabase:
    data.entries = select(data.entries, *args, **kwargs)
    return data


@select.register(str)
def _(data, *args, **kwargs) -> str:
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    return writer.write(select(parser.parse(data), *args, **kwargs))


@select.register(io.IOBase)
def _(data, *args, **kwargs):
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    return writer.write(select(parser.parse(data), *args, **kwargs))


@singledispatch
def unique_keys(data: list[dict]) -> Tuple[list[dict], dict]:
    """
    Rename keys that occur more than once in the BibTeX database.

    :param data: The BibTeX database.
    :return:
        The BibTeX database.
        A dictionary mapping the new keys to the old keys.
    """

    keys = [entry["ID"] for entry in data]
    _, iforward = np.unique(keys, return_index=True)

    if iforward.size == len(data):
        return data, {}

    iremove = np.setdiff1d(np.arange(len(data)), iforward)
    renamed = {}

    for i in iremove:
        old_key = data[i]["ID"]
        for j in range(100):
            new_key = f"{old_key}_{j}"
            if new_key not in keys:
                data[i]["ID"] = new_key
                renamed[new_key] = old_key
                break
            if j > 95:
                raise OSError("Could not rename duplicate key.")

    return data, renamed


@unique_keys.register(bibtexparser.bibdatabase.BibDatabase)
def _(data, *args, **kwargs) -> Tuple[bibtexparser.bibdatabase.BibDatabase, dict]:
    data, renamed = unique_keys(data.entries, *args, **kwargs)
    data.entries = data
    return data, renamed


@unique_keys.register(str)
def _(data, *args, **kwargs) -> Tuple[str, dict]:
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    data, renamed = unique_keys(parser.parse(data), *args, **kwargs)
    return writer.write(data), renamed


def _merge(data: list[dict], iforward: ArrayLike, ibackward: ArrayLike, merge: bool) -> list[dict]:

    if iforward.size == len(data):
        return data, {}

    unique = [data[i] for i in iforward]
    keys = [entry["ID"] for entry in unique]
    merged = {keys[ibackward[i]]: [] for i in np.setdiff1d(np.arange(len(data)), iforward)}

    for o, n in enumerate(ibackward):
        if unique[n]["ID"] not in merged:
            continue
        merged[unique[n]["ID"]].append(data[o]["ID"])
        if merge:
            for key in data[o]:
                if key not in unique[n]:
                    unique[n][key] = data[o][key]
                elif not key.isupper():
                    if latex_to_unicode(
                        unique[n][key].strip("{").strip("}").lower()
                    ) != latex_to_unicode(data[o][key].strip("{").strip("}").lower()):
                        nk = unique[n]["ID"]
                        ok = data[o]["ID"]
                        msg = f'"{nk}:{key}" and "{ok}:{key}" inconsistent'
                        msg += f'\n"{unique[n][key]}"'
                        msg += f'\n"{data[o][key]}"'
                        warnings.warn(msg, Warning)

    sorter = np.argsort(iforward)
    data = [unique[i] for i in sorter]

    return data, dict(merged)


@singledispatch
def unique(data: list[dict], merge: bool = True) -> list[dict]:
    """
    Merge items that have the same keys from BibTex database.

    :param data: The BibTeX database.
    :param merge: Add fields from duplicate entries to the first entry.
    :return: The BibTeX database.
    """

    keys = [entry["ID"] for entry in data]
    _, iforward, ibackward = np.unique(keys, return_index=True, return_inverse=True)

    if iforward.size == len(data):
        return data

    data, merged = _merge(data, iforward, ibackward, merge)
    merged = ", ".join([f'"{str(i)}"' for i in np.unique([i for i in merged])])
    warnings.warn(f"Merging duplicates, please check:\n{merged}", Warning)
    return data


@unique.register(bibtexparser.bibdatabase.BibDatabase)
def _(data, *args, **kwargs) -> bibtexparser.bibdatabase.BibDatabase:
    data.entries = unique(data.entries, *args, **kwargs)
    return data


@unique.register(str)
def _(data, *args, **kwargs) -> str:
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    return writer.write(unique(parser.parse(data), *args, **kwargs))


@singledispatch
def clever_merge(data: list[dict], merge: bool = True) -> list[dict]:
    """
    Try to merge the same entries.

    :param data: The BibTeX database.
    """

    # first pass based on doi, arxivid, url, or title

    selector = []

    for i, entry in enumerate(data):
        if "doi" in entry:
            selector.append("doi: " + entry["doi"])
        elif "arxivid" in entry:
            selector.append("arxivid: " + entry["arxivid"])
        elif "eprint" in entry:
            selector.append("eprint: " + entry["eprint"])
        elif "url" in entry:
            selector.append("url: " + entry["url"])
        elif "title" in entry and "journal" in entry:
            selector.append(
                "title: "
                + entry["title"].lower().strip("{").strip("}")
                + "journal: "
                + entry["journal"].lower().strip("{").strip("}")
            )
        else:
            selector.append(f"keep: {i:d}")

    _, iforward, ibackward = np.unique(selector, return_index=True, return_inverse=True)
    data, merged = _merge(data, iforward, ibackward, merge)

    # second pass based on author, year, title, journal

    selector = []

    for i, entry in enumerate(data):
        if "editor" in entry and "author" not in entry and entry["ENTRYTYPE"] == "book":
            selector.append(
                "year: "
                + entry["year"].lower().strip("{").strip("}")
                + "title: "
                + entry["title"].lower().strip("{").strip("}")
                + "editor: "
                + entry["editor"].lower().strip("{").strip("}")
            )
        elif "author" not in entry:
            selector.append(f"keep: {i:d}")
        elif "year" not in entry:
            selector.append(f"keep: {i:d}")
        elif "title" not in entry:
            selector.append(f"keep: {i:d}")
        elif "journal" in entry and "pages" in entry:
            selector.append(
                "year: "
                + entry["year"].lower().strip("{").strip("}")
                + "title: "
                + entry["title"].lower().strip("{").strip("}")
                + "journal: "
                + entry["journal"].lower().strip("{").strip("}")
                + "pages: "
                + entry["pages"].lower().strip("{").strip("}").replace("--", "-")
            )
        elif "journal" in entry:
            selector.append(
                "author: "
                + entry["author"].lower().strip("{").strip("}")
                + "year: "
                + entry["year"].lower().strip("{").strip("}")
                + "title: "
                + entry["title"].lower().strip("{").strip("}")
                + "journal: "
                + entry["journal"].lower().strip("{").strip("}")
            )
        else:
            selector.append(
                "author: "
                + entry["author"].lower().strip("{").strip("}")
                + "year: "
                + entry["year"].lower().strip("{").strip("}")
                + "title: "
                + entry["title"].lower().strip("{").strip("}")
            )

    _, iforward, ibackward = np.unique(selector, return_index=True, return_inverse=True)
    data, m = _merge(data, iforward, ibackward, merge)

    for key in m:
        if key not in merged:
            merged[key] = m[key]
        else:
            merged[key] += m[key]

    for key in merged:
        if key in merged[key]:
            merged[key].remove(key)

    return data, merged


@clever_merge.register(bibtexparser.bibdatabase.BibDatabase)
def _(data: str, *args, **kwargs) -> bibtexparser.bibdatabase.BibDatabase:

    d, merge = clever_merge(data.entries, *args, **kwargs)
    data.entries = d
    return data, merge


@clever_merge.register(str)
def _(data, *args, **kwargs):
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    data, merge = clever_merge(parser.parse(data), *args, **kwargs)
    return writer.write(data), merge


@clever_merge.register(io.IOBase)
def _(data, *args, **kwargs):
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    data, merge = clever_merge(parser.parse(data), *args, **kwargs)
    return writer.write(data), merge


@singledispatch
def manual_merge(data: list[dict], keys: list[Tuple[str, str]]) -> Tuple[list[dict], dict]:
    """
    Merge items.

    :param data: The BibTeX database.
    :param keys: List of keys for merge (`key[1]` merged into `key[0]`).
    :return:
        The BibTeX database.
        A dictionary mapping the new keys to the old keys.
    """
    ids = [entry["ID"] for entry in data]

    for key1, key2 in keys:
        assert key1 in ids
        assert key2 in ids
        i = np.argmax(np.array(ids) == key2)
        ids[i] = key1

    _, iforward, ibackward = np.unique(ids, return_index=True, return_inverse=True)
    return _merge(data, iforward, ibackward, True)


@manual_merge.register(bibtexparser.bibdatabase.BibDatabase)
def _(data: str, *args, **kwargs) -> Tuple[bibtexparser.bibdatabase.BibDatabase, dict]:

    d, merge = manual_merge(data.entries, *args, **kwargs)
    data.entries = d
    return data, merge


@manual_merge.register(str)
def _(data, *args, **kwargs) -> Tuple[str, dict]:
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    data, merge = manual_merge(parser.parse(data), *args, **kwargs)
    return writer.write(data), merge


@manual_merge.register(io.IOBase)
def _(data, *args, **kwargs) -> Tuple[str, dict]:
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    data, merge = manual_merge(parser.parse(data), *args, **kwargs)
    return writer.write(data), merge


@singledispatch
def clean(
    data: list[dict],
    sep_name: str = "",
    sep_journal: str = "",
    title: bool = True,
    protect_math: bool = True,
    rm_unicode: bool = True,
    no_abbreviate: list[str] = [],
) -> list[dict]:
    r"""
    Clean a BibTeX database.

    *   Remove unnecessary fields (see :py:func:`GooseBib.bibtex.select`).
    *   Unify the formatting of authors (see :py:func:`GooseBib.reformat.abbreviate_firstname`).
    *   Ensure proper math formatting (see :py:func:`GooseBib.reformat.protect_math`).
    *   Convert unicode to TeX (see :py:func:`GooseBib.reformat.rm_unicode`).
    *   Fill digital identifier if it is not present but can be recognised from a different field,
        (see :py:func:`GooseBib.bibtex.get_identifiers`).

    :param data: The BibTeX database.
    :param sep_name: Separator for name initials (e.g. "", " ").
    :param sep_journal: Separator for journal abbreviations (e.g. "", " ").
    :param title: Include title.
    :param protect_math: Apply fix in :py:func:`GooseBib.reformat.protect_math`.
    :param rm_unicode: Apply fix in :py:func:`GooseBib.reformat.rm_unicode`.
    :param no_abbreviate: List of entries for which to skip author abbreviation.
    """

    ignored_authors = []

    for entry in data:

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
        if entry["ID"] not in no_abbreviate:
            for key in ["author", "editor"]:
                if key in entry:
                    entry[key] = reformat.autoformat_names(entry[key], sep_name)

        # uniform range 000--000
        for key in ["pages", "number", "volume"]:
            if key in entry:
                entry[key] = reformat.number_range(entry[key])

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

    # return selection of fields
    return select(data, fields=selection(use_bibtexparser=True))


@clean.register(bibtexparser.bibdatabase.BibDatabase)
def _(data: str, *args, **kwargs) -> bibtexparser.bibdatabase.BibDatabase:
    """
    Extra options:

    :param rm_comment: Remove @comment (default: ``True``).
    :param rm_string: Remove @string (default: ``True``). NB: strings are interpreted by the parser.
    """

    if kwargs.pop("rm_comment", True):
        data.comments = []

    if kwargs.pop("rm_string", True):
        data.strings = OrderedDict()

    data.entries = clean(data.entries, *args, **kwargs)
    return data


@clean.register(str)
def _(data: str, *args, **kwargs) -> str:
    """
    Extra options (on top of those of the ``bibtexparser.bibdatabase.BibDatabase`` overload:

    :param sort_entries: Sort entries in output.
    """
    writer = MyBibTexWriter(sort_entries=kwargs.pop("sort_entries", False))
    parser = MyBibTexParser()
    return writer.write(clean(parser.parse(data), *args, **kwargs))


@clean.register(io.IOBase)
def _(data: io.IOBase, *args, **kwargs) -> str:
    """
    Extra options (on top of those of the ``bibtexparser.bibdatabase.BibDatabase`` overload:

    :param sort_entries: Sort entries in output.
    """
    writer = MyBibTexWriter(sort_entries=kwargs.pop("sort_entries", False))
    parser = MyBibTexParser()
    return writer.write(clean(parser.parse(data), *args, **kwargs))


@singledispatch
def abbreviate_journal(
    data: list[dict],
    journal_type: str = "abbreviation",
    journal_database: list[str] = ["pnas", "physics", "mechanics"],
) -> list[dict]:
    """
    Abbreviate journals based on a standard library.

    :param data: The BibTeX database.
    :param journal_type: Rename journal to its ``"title"``, ``"abbreviation"``, or ``"acronym"``.
    :param journal_database: Database(s) with official journal names/abbreviations/acronyms to use.
    """

    if len(journal_database) == 0:
        return data

    journal_type = journal_type.lower()
    journal_database = [journal_database] if isinstance(journal_database, str) else journal_database
    revus = [entry["journal"] for entry in data if "journal" in entry]

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

    for entry in data:
        if "journal" in entry:
            try:
                entry["journal"] = mapping[entry["journal"]]
            except KeyError:
                warnings.warn(
                    f'"{entry["journal"]}" in "{entry["ID"]}" not found in database', Warning
                )

    return data


@abbreviate_journal.register(bibtexparser.bibdatabase.BibDatabase)
def _(data: str, *args, **kwargs) -> bibtexparser.bibdatabase.BibDatabase:
    data.entries = abbreviate_journal(data.entries, *args, **kwargs)
    return data


@abbreviate_journal.register(str)
def _(data, *args, **kwargs):
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    return writer.write(abbreviate_journal(parser.parse(data), *args, **kwargs))


@abbreviate_journal.register(io.IOBase)
def _(data, *args, **kwargs):
    writer = MyBibTexWriter()
    parser = MyBibTexParser()
    return writer.write(abbreviate_journal(parser.parse(data), *args, **kwargs))


@singledispatch
def format_journal_arxiv(
    data: list[dict], fmt: str, journal_database: list[str] = ["arxiv"]
) -> list[dict]:
    """
    Format the journal entry for arXiv preprints.
    Use ``"{}"`` in the formatter to include the arxivid.

    :param data: The BibTeX database.
    :param fmt: Formatter, e.g. ``"Preprint"`` or ``"Preprint: arXiv {}"``.
    :param journal_database: Database(s) with known arXiv variants.
    """

    search = r"(" + re.escape("10.48550/arXiv.") + r")(.*)"
    pattern = ["arxiv", "preprint", "submitted", "in preparation"]

    for entry in data:

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
        for entry in data:
            if "journal" in entry:
                revus.append(entry["journal"])

        db = journals.load(*journal_database)
        new = db.map2name(revus)
        mapping = {o: n for o, n in zip(revus, new)}

        for entry in data:
            if "journal" in mapping and "arxivid" in entry:
                if "doi" in entry:
                    if not re.match(search, entry["doi"]):
                        continue
                entry["journal"] = fmt.format(arxivid)

    return data


@format_journal_arxiv.register(bibtexparser.bibdatabase.BibDatabase)
def _(data: str, *args, **kwargs) -> bibtexparser.bibdatabase.BibDatabase:
    data.entries = format_journal_arxiv(data.entries, *args, **kwargs)
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

    class BlankLinesHelpFormatter(
        argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
    ):
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
        "--raw-author",
        type=str,
        action="append",
        help="List entries for which names are not abbreviated.",
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
        "--rename",
        type=str,
        nargs=2,
        action="append",
        help="Rename citation keys (applied after merging).",
    )

    parser.add_argument(
        "--merge",
        type=str,
        nargs=2,
        action="append",
        help="Force merging of items.",
    )

    parser.add_argument(
        "--sort-entries",
        action="store_true",
        help="Sort output by entries.",
    )

    parser.add_argument(
        "--unique",
        type=str,
        help="Merge identical entries with different keys. Argument: output YAML file.",
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
        action="store_true",
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
    renamed = {}
    merged = {}
    is_unique = False

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

        raw = ""
        data = []
        sourcepaths = [None]
        outpaths = [args.output]

        if len(args.files) == 1:

            filepath = args.files[0]
            if not os.path.isfile(filepath):
                raise OSError(f'"{filepath}" does not exist')
            with open(filepath) as file:
                text = file.read()
                raw += text
                parsed = MyBibTexParser().parse(text)
                data = parsed.entries
        else:

            for filepath in args.files:
                if not os.path.isfile(filepath):
                    raise OSError(f'"{filepath}" does not exist')
                with open(filepath) as file:
                    text = file.read()
                    raw += text
                    parsed = MyBibTexParser().parse(text)
                    data += unique(parsed.entries)
                    data, r = unique_keys(data)
                    renamed = {**renamed, **r}
                    is_unique = True

        if not args.force:

            overwrite = []

            for outpath in outpaths:
                if os.path.isfile(outpath):
                    overwrite += [os.path.normpath(outpath)]

            if args.diff:
                if os.path.isfile(args.diff):
                    overwrite += [os.path.normpath(args.diff)]

            if args.unique:
                if os.path.isfile(args.unique):
                    overwrite += [os.path.normpath(args.unique)]

            if len(overwrite) > 0:
                files = ", ".join(overwrite)
                if not click.confirm(f'Overwrite "{files}"?'):
                    raise OSError("Cancelled")

    # formatting

    for sourcepath, outpath in zip(sourcepaths, outpaths):

        if sourcepath is not None:
            with open(sourcepath) as file:
                raw = file.read()
                parsed = MyBibTexParser().parse(raw)
                data = parsed.entries

        # basic clean

        parsed.comments = []
        parsed.strings = OrderedDict()

        data = clean(
            data,
            sep_name=args.author_sep,
            sep_journal=args.journal_sep,
            title=not args.no_title,
            protect_math=not args.ignore_math,
            rm_unicode=not args.ignore_unicode,
            no_abbreviate=args.raw_author if args.raw_author else [],
        )

        # reformat arXiv entries

        if args.arxiv:
            data = format_journal_arxiv(data, args.arxiv)

        # abbreviate journals

        data = abbreviate_journal(
            data,
            journal_type=args.journal_type,
            journal_database=args.journals.split(","),
        )

        # merge identical entries

        if not is_unique:
            data = unique(data)

        # hand merge duplicates

        if args.merge:

            data, merged = manual_merge(data, args.merge)

        # clever merge duplicates

        if args.unique:

            data, m = clever_merge(data)
            merged = {**merged, **m}

        # rename keys

        if args.rename:

            keys = [entry["ID"] for entry in data]

            for oldkey, newkey in args.rename:
                assert oldkey in keys
                assert newkey not in keys
                for i in np.argwhere(np.array(keys) == oldkey).ravel():
                    data[i]["ID"] = newkey
                    if oldkey in merged:
                        merged[newkey] = merged.pop(oldkey)
                    if oldkey in renamed:
                        renamed[newkey] = renamed.pop(oldkey)

        # write changed keys

        if args.unique:

            newnames = {k: v for k, v in renamed.items()}

            for key in merged:
                for i, value in enumerate(merged[key]):
                    if value in renamed:
                        merged[key][i] = renamed[value]
                        renamed.pop(value)

            for key in renamed:
                if key in merged:
                    merged[key].append(renamed[key])
                else:
                    merged[key] = [renamed[key]]

            for key in merged:
                merged[key] = list(set(merged[key]))
                for value in merged[key]:
                    if value == key:
                        merged[key].remove(value)

            merged = {key: merged[key] for key in merged if len(merged[key]) > 0}

            keys = [entry["ID"] for entry in data]
            for i, key in enumerate(keys):
                if key in newnames:
                    if newnames[key] not in keys:
                        data[i]["ID"] = newnames[key]
                        merged[newnames[key]] = merged.pop(key)

            yaml_dump(args.unique, merged, force=True)

        elif len(renamed) > 0:

            merged = ", ".join([f'"{i}" -> "{renamed[i]}"' for i in renamed])
            warnings.warn(f"Renaming conflicts, please check:\n{merged}", Warning)

        # write output

        parsed.entries = data
        data = MyBibTexWriter(sort_entries=args.sort_entries).write(parsed)

        if data != parse(data):
            warnings.warn("Re-parsing is failing, there might be dangling {}", Warning)

        if data == raw:
            return 0

        with open(outpath, "w") as file:
            file.write(data)

        if args.diff is not None:

            if args.diff_type.lower() == "raw":
                simple = raw
            elif args.diff_type.lower() == "plain":
                try:
                    simple = parse(raw)
                except:
                    simple = parse(raw, aggresive=True)
                    warnings.warn("Light parsing for diff failed", Warning)
            elif args.diff_type.lower() == "select":
                simple = select(raw)
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
    Show author rename if ``GbibClean`` is applied, see ``--help``.
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

    parser = MyBibTexParser()

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


@singledispatch
def dbsearch_arxiv(
    data: list[dict],
    silent: bool = False,
) -> dict:
    """
    Check online databases (can be slow!).

    :param silent: Hide status bar.
    :return: Dictionary with discovered items.
    """

    output = defaultdict(lambda: defaultdict(list))

    # find arxivid based on journal doi

    for entry in tqdm.tqdm(data, disable=silent):
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

    for entry in tqdm.tqdm(data, disable=silent):
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


@dbsearch_arxiv.register(bibtexparser.bibdatabase.BibDatabase)
def _(data: str, *args, **kwargs) -> bibtexparser.bibdatabase.BibDatabase:

    return dbsearch_arxiv(data.entries, *args, **kwargs)


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
        "-v",
        "--version",
        action="version",
        version=version,
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

    parser = MyBibTexParser()

    data = parser.parse(source)
    output = {}

    if args.arxiv:
        output = dbsearch_arxiv(data, silent=args.silent)

    if len(output) > 0:
        yaml_dump(args.output, output, force=args.force)
