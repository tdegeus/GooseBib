import csv
import io
import os
import re
import shutil
import tempfile
from typing import Union

import click
import git
import numpy as np
import yaml
from numpy.typing import ArrayLike


def get_configdir() -> str:
    """
    Return the config directory.
    """
    return os.path.expanduser("~/.config/GooseBib")


class Journal:
    """
    Simple class to store journal info.

    :param name: Journal's name.
    :param abbreviation: Abbreviation of the journal's name (optional).
    :param acronym: Acronym of the journal's name (optional).
    :param variations: Known variation used for the journal's name, abbreviation, etc. (optional).

    :param index:
        For internal use only. Construction can be simplified by specifying name, abbreviation,
        acronym, and variations as a single list for the ``variations`` option.
        ``index`` than indicates the indices in this list corresponding to
        ``[name, abbreviation, acronym]`` (the same index may be use multiple times if there is no
        abbreviation or acronym).
    """

    def __init__(
        self,
        name: str = None,
        abbreviation: str = None,
        acronym: str = None,
        variations: list[str] = None,
        index: list[int] = None,
    ):

        if index:
            assert name is None
            assert abbreviation is None
            assert variations is not None
            assert len(index) > 0
            assert max(index) < len(variations)
            self.data = [str(i) for i in variations]
            self.name = index[0]
            self.abbr = index[1]
            self.acro = index[2]
            return

        self.name = 0
        self.abbr = 0
        self.acro = 0
        self.data = []

        if name:
            self.set_name(name)

        if abbreviation:
            self.set_abbreviation(abbreviation)

        if acronym:
            self.set_acronym(acronym)

        if variations:
            self.add_variations(variations)

    def set_name(self, arg):
        """
        (Over)write the journal's name.
        :param arg: Name.
        """
        n = len(self.data)
        if self.abbr == self.name:
            self.abbr = n
        if self.acro == self.name:
            self.acro = n
        self.name = n
        self.data.append(arg)

    def set_abbreviation(self, arg: str):
        """
        (Over)write the abbreviation of the journal's name.
        :param arg: Name.
        """
        self.abbr = len(self.data)
        self.data.append(arg)

    def set_acronym(self, arg: str):
        """
        (Over)write the acronym of the journal's name.
        :param arg: Name.
        """
        self.acro = len(self.data)
        self.data.append(arg)

    def add_variation(self, arg: str):
        """
        Add a variation (does not change the name, abbreviation, or acronym).
        :param arg: Name.
        """
        self.data.append(arg)

    def add_variations(self, arg: list[str]):
        """
        Add a list of variations (does not change the name, abbreviation, or acronym).
        :param arg: Names.
        """
        self.data += arg

    def unique(self):
        """
        In place operation.
        Removes duplicates from list of stored name, abbreviation, acronym, variations.
        Does not change the output in any way.
        """
        data, index = np.unique(self.data, return_inverse=True)
        self.data = [str(d) for d in data]
        self.name = index[self.name]
        self.abbr = index[self.abbr]
        self.acro = index[self.acro]
        return self

    def __add__(self, other):
        """
        Merge two :py:class`Journal` entries. The name, abbreviation, and acronym of the first
        occurring item are prioritised, and are taken from the second occurrence only if not
        present in the first.

        Internally duplicate entries are removed.
        """

        e = Journal()
        n = len(self.data)

        if n == 0:
            e.data = other.data
            e.name = other.name
            e.abbr = other.abbr
            e.acro = other.acro
            return e.unique()

        e.data = self.data + other.data
        e.name = self.name
        e.abbr = self.abbr
        e.acro = self.acro

        if self.abbr == self.name and other.abbr != other.name:
            e.abbr = n + other.abbr

        if self.acro == self.name and other.acro != other.name:
            e.acro = n + other.acro

        return e.unique()

    def __iter__(self):
        """
        Allow ``dict(myjournal)``.
        """

        yield "name", self.data[self.name]

        if self.abbr != self.name:
            yield "abbreviation", self.data[self.abbr]

        if self.acro != self.name:
            yield "acronym", self.data[self.acro]

        idx = np.arange(len(self.data))
        idx = idx[np.logical_not(np.in1d(idx, np.unique([self.name, self.abbr, self.acro])))]

        if idx.size > 0:
            yield "variations", [self.data[i] for i in idx]

    def __repr__(self):
        return str(dict(self))


class JournalList:
    """
    Store journal database as list of journals, which allows efficient handling.

    :param data: Database to map.
    """

    def __init__(self, data: Union[dict[Journal], list[Journal]] = None):

        self.count = 0

        if data is None:
            self.names = []
        else:
            if isinstance(data, dict):
                data = list(data.values())
            self.names = []
            for entry in data:
                self.names += entry.data

        n = len(self.names)
        self.names = np.array(self.names)
        self.index = np.empty(n, dtype=int)
        self.name = np.zeros(n, dtype=int)
        self.abbr = np.zeros(n, dtype=int)
        self.acro = np.zeros(n, dtype=int)

        if data is None:
            return

        i = 0
        for ientry, entry in enumerate(data):
            j = i + len(entry.data)
            self.index[i:j] = ientry
            self.name[i + entry.name] = -1
            self.abbr[i + entry.abbr] = -1
            self.acro[i + entry.acro] = -1
            i = j

        self._renum()

    def _renum(self):
        """
        Internal renumbering.
        Private function: external call only needed after outside manipulation of member variables.
        """

        old = np.sort(np.unique(self.index))
        renum = np.empty(np.max(old) + 1, dtype=int)
        renum[old] = np.arange(old.size)
        self.index = renum[self.index]

    def _map(self, journals: list[str], case_sensitive: bool, field: ArrayLike) -> list[str]:
        """
        Map List of names.

        :param journals: List to map.
        :param case_sensitive: Keep case during look-up.
        :param field: Type identifier to use in case of positive match.
        :return: Input list with mapped items replaced where a positive match was found.
        """

        ret = [i for i in journals]

        if case_sensitive:
            varations = self.names
            search = journals
        else:
            varations = [str(i).lower() for i in self.names]
            search = [i.lower() for i in journals]

        _, v_index, s_index = np.intersect1d(varations, search, return_indices=True)

        for j, s in zip(self.index[v_index], s_index):
            sel = self.index == j
            n = np.argmin(field[sel])
            ret[s] = str(self.names[sel][n])

        return ret

    def map2name(self, journals: list[str], case_sensitive: bool = False) -> list[str]:
        """
        Map List of names.

        :param journals: List to map.
        :param case_sensitive: Keep case during look-up.
        :return: Input list with official name replaced where a positive match was found.
        """
        return self._map(journals, case_sensitive, self.name)

    def map2abbreviation(self, journals: list[str], case_sensitive: bool = False) -> list[str]:
        """
        Map List of names.

        :param journals: List to map.
        :param case_sensitive: Keep case during look-up.
        :return: Input list with abbreviation replaced where a positive match was found.
        """
        return self._map(journals, case_sensitive, self.abbr)

    def map2acronym(self, journals: list[str], case_sensitive: bool = False) -> list[str]:
        """
        Map List of names.

        :param journals: List to map.
        :param case_sensitive: Keep case during look-up.
        :return: Input list with acronym replaced where a positive match was found.
        """
        return self._map(journals, case_sensitive, self.acro)

    def unique(self, force_first=True) -> bool:
        """
        Merge journal that have a common entry.
        Note that this applies changes in-place.

        :param force_first:
            Add the second, third, ... duplicates only as name variations, do not change
            name, abbreviation, and acronym of the first duplicate.
            If ``False``, the name, abbreviation, and acronym of all duplicates are considered
            if they are not present in the first duplicate.

        :return: ``True`` if the list was unique, i.e. if no changes were applied.
        """

        names, ifoward, ibackward = np.unique(self.names, return_index=True, return_inverse=True)

        if names.size == self.names.size:
            return False

        self.count = 0
        self.names = names
        renum = self.index[ifoward][ibackward]
        old = self.index[self.index != renum]
        new = renum[self.index != renum]

        for o, n in zip(old, new):
            i = min(o, n)
            j = max(o, n)
            flip = self.index == j

            if force_first:
                self.name[flip] = 0
                self.abbr[flip] = 0
                self.acro[flip] = 0

            self.index[flip] = i

        self.index = self.index[ifoward]
        self.name = self.name[ifoward]
        self.abbr = self.abbr[ifoward]
        self.acro = self.acro[ifoward]

        self._renum()

        return True

    def tolist(self) -> list[dict]:
        """
        Return as list of dictionaries. Same as::

            ret = []

            for i in data:
                ret += [dict(i)]
        """

        ret = []

        for i in range(np.max(self.index) + 1):

            i = self.index == i
            e = Journal(
                variations=self.names[i],
                index=[
                    np.argmin(self.name[i]),
                    np.argmin(self.abbr[i]),
                    np.argmin(self.acro[i]),
                ],
            )
            ret += [e]

        return ret

    def __add__(self, other, force_first=True):
        """
        Merge two journal lists.

        :param force_first:
            Add the second list only as name variations, do not change
            name, abbreviation, and acronym of the first list.
            If ``False``, the name, abbreviation, and acronym of the second list are considered
            if they are not present in the first list.
        """

        ret = JournalList()
        ret.names = np.concatenate((self.names, other.names))
        ret.index = np.concatenate((self.index, other.index + np.max(self.index) + 1))
        ret.name = np.concatenate((self.name, other.name))
        ret.abbr = np.concatenate((self.abbr, other.abbr))
        ret.acro = np.concatenate((self.acro, other.acro))
        ret.unique(force_first)
        return ret

    def __iter__(self):
        """
        Reset counter.
        """
        self.count = 0
        return self

    def __next__(self) -> Journal:
        """
        Return next entry as Journal.
        """

        if self.count > np.max(self.index):
            raise StopIteration

        sel = self.index == self.count
        ret = Journal(
            variations=self.names[sel],
            index=[
                np.argmin(self.name[sel]),
                np.argmin(self.abbr[sel]),
                np.argmin(self.acro[sel]),
            ],
        )

        self.count += 1

        return ret

    def __repr__(self):
        return str([dict(i) for i in self.tolist()])


def _database_tolist(data: Union[dict[Journal], list[Journal]]) -> list[dict]:
    """
    Convert database to list of dictionaries.

    :param data: The database.
    :return: List of dictionaries.
    """

    ret = []

    if isinstance(data, dict):
        for key in sorted(data):
            ret.append(dict(data[key]))
    else:
        for entry in data:
            ret.append(dict(entry))

    return ret


def dump(
    filepath: str,
    data: Union[dict[Journal], list[Journal], JournalList],
    force: bool = False,
):
    r"""
    Dump database to YAML file.

    :param filepath: Filename.
    :param data: The database.
    :param force: Do not prompt to overwrite file.
    """

    dirname = os.path.dirname(filepath)

    if not force:
        if os.path.isfile(filepath):
            if not click.confirm(f'Overwrite "{filepath:s}"?'):
                raise OSError("Cancelled")
        elif not os.path.isdir(dirname) and len(dirname) > 0:
            if not click.confirm(f'Create "{os.path.dirname(filepath):s}"?'):
                raise OSError("Cancelled")

    if not os.path.isdir(dirname) and len(dirname) > 0:
        os.makedirs(os.path.dirname(filepath))

    with open(filepath, "w") as file:
        yaml.dump(_database_tolist(data), file, allow_unicode=True, width=200)


def read(filepath: str) -> JournalList:
    """
    Load a database.

    :param filepath: Filename.
    """

    if not os.path.isfile(filepath):
        raise OSError(f'"{filepath:s} does not exist')

    with open(filepath) as file:
        ret = yaml.load(file.read(), Loader=yaml.FullLoader)

    return JournalList([Journal(**entry) for entry in ret])


def generate_jabref(*domains):
    """
    Generate a database entry from JabRef.

    :param domains:
        Domain(s) to include in the database. Choose from:
        - acs
        - ams
        - annee-philologique
        - dainst
        - entrez
        - general
        - geology_physics
        - geology_physics_variations
        - ieee
        - ieee_strings
        - lifescience
        - mathematics
        - mechanical
        - medicus
        - meteorology
        - sociology
        - webofscience-dots
        - webofscience

    :return: tood
    """

    alllowed = [
        "acs",
        "ams",
        "annee-philologique",
        "dainst",
        "entrez",
        "general",
        "geology_physics",
        "geology_physics_variations",
        "ieee",
        "ieee_strings",
        "lifescience",
        "mathematics",
        "mechanical",
        "medicus",
        "meteorology",
        "sociology",
        "webofscience-dots",
        "webofscience",
    ]

    domains = [domain.lower() for domain in domains]

    filenames = []
    for domain in domains:
        if domain not in alllowed:
            raise OSError(f'Unknown domain "{domain}"')
        filenames.append(f"journal_abbreviations_{domain}.csv")

    tempdir = tempfile.mkdtemp()
    git.Repo.clone_from("https://github.com/JabRef/abbrv.jabref.org.git", tempdir)

    text = []
    for filename in filenames:
        filepath = os.path.join(tempdir, "journals", filename)
        with open(filepath, newline="") as file:
            text += list(filter(None, file.read().replace("’", "'").replace("–", "-").split("\n")))

    shutil.rmtree(tempdir)

    csvfile = io.StringIO("\n".join(set(text)))
    reader = csv.reader(csvfile, delimiter=";")
    ret = dict()

    for name, abbr in reader:
        if name not in ret:
            ret[name] = Journal(name=name, abbreviation=abbr)
        else:
            ret[name] += Journal(name=name, abbreviation=abbr)

    return ret


def generate_default(domain: str):
    """
    Generate default database:

        {
            "Official Journal Name": ``Journal``
            ...
        }

    :param domain: Domain (physics, mechanics, PNAS, PNAS-USA).
    :return: Database.
    """

    domain = domain.lower()

    if domain == "physics":

        # basic list from JabRef

        db = generate_jabref("geology_physics", "geology_physics_variations")

        # merge know aliases / set acronyms / add know variations

        j = "Proceedings of the National Academy of Sciences of the United States of America"
        a = "Proceedings of the National academy of Sciences of the United States of America"
        db[j] += db.pop(a)
        db[j].set_acronym("PNAS")

        j = "Physical Review A"
        a = "Physical Review A: Atomic, Molecular, and Optical Physics"
        db[j] += db.pop(a)
        db[j].set_acronym("PRA")

        j = "Physical Review B"
        a = "Physical Review B: Condensed Matter"
        db[j] += db.pop(a)
        db[j].set_acronym("PRB")

        j = "Physical Review C"
        a = "Physical Review C: Nuclear Physics"
        db[j] += db.pop(a)
        db[j].set_acronym("PRC")

        j = "Physical Review D"
        a = "Physical Review D: Particles and Fields"
        db[j] += db.pop(a)
        db[j].set_acronym("PRD")

        j = "Physical Review E"
        a = "Physical Review E: Statistical Physics, Plasmas, Fluids, and Related Interdisciplinary Topics"
        db[j] += db.pop(a)
        db[j].set_acronym("PRE")

        db["Proceedings of the National Academy of Sciences"].set_acronym("PNAS")
        db["Physical Review Letters"].set_acronym("PRL")
        db["Physical Review X"].set_acronym("PRX")
        db["Journal of the Mechanics and Physics of Solids"].set_acronym("JMPS")
        db["International Journal of Solids and Structures"].set_acronym("IJSS")

        db["Science"].add_variation("Science (80-. ).")
        db["EPL (Europhysics Letters)"].add_variation("EPL (Europhysics Lett.")

    elif domain == "mechanics":

        db = generate_jabref("mechanical")
        db["International Journal for Numerical Methods in Engineering"].set_acronym("IJNME")
        db["Journal of the Mechanics and Physics of Solids"].set_acronym("JMPS")
        db["International Journal of Solids and Structures"].set_acronym("IJSS")

    elif domain == "pnas":

        db = generate_default("physics")
        name = "Proceedings of the National Academy of Sciences"
        alias = "Proceedings of the National Academy of Sciences of the United States of America"
        db = {name: db[name] + db[alias]}

    elif domain == "pnas-usa":

        db = generate_default("physics")
        name = "Proceedings of the National Academy of Sciences of the United States of America"
        alias = "Proceedings of the National Academy of Sciences"
        db = {name: db[name] + db[alias]}

    else:
        raise OSError(f'Unknown domain "{domain}"')

    return db


def update_default():
    """
    Update the default databases shipped with GooseBib.
    """

    dirname = os.path.dirname(__file__)

    for name in ["physics", "mechanics", "PNAS", "PNAS-USA"]:
        db = JournalList(generate_default(name))
        dump(os.path.join(dirname, f"{name}.yaml"), db, force=True)


def _get_yaml_files(dirname: str) -> list[str]:
    """
    Return YAML-files in a directory.

    :param dirname: Directory to search.
    :return: List of files.
    """

    ret = [f for f in os.listdir(dirname)]
    return [f for f in ret if re.match(r"(\.y)([a]?)(ml)", os.path.splitext(f)[1])]


def load(*args: str) -> JournalList:
    """
    Load database(s) from files (in default locations).
    Note that the order matters: in case of duplicates the first match is leading.

    Custom databases: Store a YAML file to::

        dirname = GooseBib.get_configdir()
        stylename = "mystyle"
        filepath = os.path.join(dirname, f"{stylename}.yaml")

    To file should have the following structure::

        - name: Proceedings of the National Academy of Sciences
          abbreviation: Proc. Natl. Acad. Sci.
          acronym: PNAS
          variations:
          - Proc. Nat. Acad. Sci. U.S.A.
        - name: ...

    whereby all fields except "name" are optional.
    Files stored in ``GooseBib.get_configdir()`` are prioritised over default files shipped
    with the library.

    :param args: physics, mechanics, PNAS, PNAS-USA, ...
    :return: JournalList
    """

    assert len(args) > 0

    search = dict(
        config={"dirname": os.path.abspath(get_configdir())},
        default={"dirname": os.path.abspath(os.path.dirname(__file__))},
    )

    if os.path.exists(search["config"]["dirname"]):
        search_order = ["config", "default"]
    else:
        search_order = ["default"]
        search.pop("config")

    for key in search:
        search[key]["files"] = _get_yaml_files(search[key]["dirname"])
        search[key]["names"] = [os.path.splitext(f)[0].lower() for f in search[key]["files"]]

    db = []

    for arg in args:

        found = False
        name = arg.lower()

        for key in search_order:
            if name in search[key]["names"]:
                names = np.array(search[key]["names"])
                path = search[key]["files"][np.argwhere(names == name).ravel()[0]]
                db += [read(os.path.join(search[key]["dirname"], path))]
                found = True
                break

        if not found:
            raise OSError(f'Could not find "{arg}"')

    ret = db[0]
    for d in db[1:]:
        ret += d
    return ret


if __name__ == "__main__":

    update_default()
