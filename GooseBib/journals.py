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

    :param abbreviation_is_acronym: Use abbreviation as acronym if no acronym is specified.
    """

    def __init__(
        self,
        name: str = None,
        abbreviation: str = None,
        acronym: str = None,
        variations: list[str] = None,
        index: list[int] = None,
        abbreviation_is_acronym: bool = False,
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
            self.set_abbreviation(abbreviation, abbreviation_is_acronym and acronym is None)

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

    def set_abbreviation(self, arg: str, also_acronym: bool = False):
        """
        (Over)write the abbreviation of the journal's name.
        :param arg: Name.
        :param also_acronym: Use also as acronym.
        """
        n = len(self.data)
        if also_acronym:
            self.acro = n
        self.abbr = n
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
                data = [value for (key, value) in sorted(data.items())]
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
            variations = self.names
            search = journals
        else:
            variations = [str(i).lower() for i in self.names]
            search = [i.lower() for i in journals]

        _, v_index, s_index = np.intersect1d(variations, search, return_indices=True)

        for j, s in zip(self.index[v_index], s_index):
            sel = self.index == j
            n = np.argmin(field[sel])
            r = str(self.names[sel][n])
            for i in np.argwhere(np.array(ret) == ret[s]).ravel():
                ret[i] = r

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


def read(filepath: str, abbreviation_is_acronym: bool = True) -> JournalList:
    """
    Load a database.

    :param filepath: Filename.
    :param abbreviation_is_acronym: Use abbreviation for missing acronym (otherwise title is used).
    """

    if not os.path.isfile(filepath):
        raise OSError(f'"{filepath:s} does not exist')

    with open(filepath) as file:
        ret = yaml.load(file.read(), Loader=yaml.FullLoader)

    return JournalList(
        [Journal(abbreviation_is_acronym=abbreviation_is_acronym, **entry) for entry in ret]
    )


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


def _database_merge(
    db: dict[Journal],
    name: str,
    merge: list[str] = [],
    abbreviation: str = None,
    acronym: str = None,
) -> dict[Journal]:
    """
    Merge several database entries

    :oaram db: The database.
    :param name: The official name to keep (also new key).
    :param merge: The keys to merge.
    :param abbreviation: Overwrite journal abbreviation (optional).
    :param acronym: Overwrite journal acronym (optional).
    :return: The database
    """

    if isinstance(merge, str):
        merge = [merge]

    assert name in db or len(merge) > 0

    if name not in db:
        db[name] = db.pop(merge[0])
        merge = merge[1:]

    for m in merge:
        db[name] += db.pop(m)

    db[name].set_name(name)

    if abbreviation:
        db[name].set_abbreviation(abbreviation)

    if acronym:
        db[name].set_acronym(acronym)

    db[name].unique()

    return db


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

        _database_merge(
            db=db,
            name="Proceedings of the National Academy of Sciences of the United States of America",
            abbreviation="Proc. Natl. Acad. Sci. U.S.A.",
            acronym="PNAS",
            merge=[
                "Proceedings of the National academy of Sciences of the United States of America"
            ],
        )

        _database_merge(
            db=db,
            name="Proceedings of the National Academy of Sciences",
            abbreviation="Proc. Natl. Acad. Sci.",
            acronym="PNAS",
        )

        _database_merge(
            db=db,
            name="Physical Review A",
            abbreviation="Phys. Rev. A",
            acronym="PRA",
            merge=["Physical Review A: Atomic, Molecular, and Optical Physics"],
        )

        _database_merge(
            db=db,
            name="Physical Review B",
            abbreviation="Phys. Rev. B",
            acronym="PRB",
            merge=["Physical Review B: Condensed Matter"],
        )

        _database_merge(
            db=db,
            name="Physical Review C",
            abbreviation="Phys. Rev. C",
            acronym="PRC",
            merge=["Physical Review C: Nuclear Physics"],
        )

        _database_merge(
            db=db,
            name="Physical Review D",
            abbreviation="Phys. Rev. D",
            acronym="PRD",
            merge=["Physical Review D: Particles and Fields"],
        )

        base = "Physical Review E:"
        _database_merge(
            db=db,
            name="Physical Review E",
            abbreviation="Phys. Rev. E",
            acronym="PRE",
            merge=[
                f"{base} Statistical Physics, Plasmas, Fluids, and Related Interdisciplinary Topics"
            ],
        )

        _database_merge(
            db=db,
            name="Journal of Physics A",
            abbreviation="J. Phys. A",
            merge=[
                "Journal of Physics A: General Physics",
                "Journal of Physics A: Mathematical and General",
                "Journal of Physics A: Mathematical and Theoretical",
                "Journal of Physics A: Mathematical, Nuclear and General",
            ],
        )

        _database_merge(
            db=db,
            name="Journal of Physics B",
            abbreviation="J. Phys. B",
            merge=[
                "Journal of Physics B: Atomic, Molecular and Optical",
                "Journal of Physics B: Atomic, Molecular and Optical Physics",
                "Journal of Physics B: Atomic and Molecular Physics",
            ],
        )

        _database_merge(
            db=db,
            name="Journal of Physics C",
            abbreviation="J. Phys. C",
            merge=["Journal of Physics C: Solid State Physics"],
        )

        _database_merge(
            db=db,
            name="Journal of Physics D",
            abbreviation="J. Phys. D",
            merge=["Journal of Physics D: Applied Physics"],
        )

        _database_merge(
            db=db,
            name="Journal of Physics E",
            abbreviation="J. Phys. E",
            merge=["Journal of Physics E: Scientific Instruments"],
        )

        _database_merge(
            db=db,
            name="Journal of Physics F",
            abbreviation="J. Phys. F",
            merge=["Journal of Physics F: Metal Physics"],
        )

        _database_merge(
            db=db,
            name="Journal of Physics G",
            abbreviation="J. Phys. G",
            merge=["Journal of Physics G: Nuclear and Particle Physics"],
        )

        _database_merge(
            db=db,
            name="Physica A",
            abbreviation="Phys. A",
            merge=["Physica A: Statistical Mechanics and its Applications"],
        )

        _database_merge(
            db=db,
            name="Physica B",
            abbreviation="Phys. B",
            merge=["Physica B: Condensed Matter"],
        )

        _database_merge(
            db=db,
            name="Physica C",
            abbreviation="Phys. C",
            merge=["Physica C: Superconductivity and its Applications"],
        )

        _database_merge(
            db=db,
            name="Physica D",
            abbreviation="Phys. D",
            merge=["Physica D: Nonlinear Phenomena"],
        )

        _database_merge(
            db=db,
            name="Physica E",
            abbreviation="Phys. E",
            merge=[
                "Physica E-low-dimensional Systems & Nanostructures",
                "Physica E: Low-dimensional Systems and Nanostructures",
            ],
        )

        _database_merge(
            db=db,
            name="Zeitschrift für Physik A",
            abbreviation="Z. Phys. A",
            merge=[
                "Zeitschrift für Physik A: Atoms and Nuclei",
                "Zeitschrift für Physik A Hadrons and Nuclei",
            ],
        )

        _database_merge(
            db=db,
            name="Science in China, Series A: Mathematics",
            abbreviation="Sci. China A",
        )

        _database_merge(
            db=db,
            name="Science in China, Series C: Life Sciences",
            abbreviation="Sci. China C",
        )

        _database_merge(
            db=db,
            name="Science in China, Series D: Earth Sciences",
            abbreviation="Sci. China D",
        )

        _database_merge(
            db=db,
            name="Science in China, Series G: Physics Mechanics and Astronomy",
            abbreviation="Sci. China G",
        )

        _database_merge(
            db=db,
            name="Astrophysics and Space Science",
            abbreviation="Astrophys. Space Sci.",
        )

        _database_merge(
            db=db,
            name="Annalen der Physik",
            abbreviation="Ann. Phys.",
        )

        _database_merge(
            db=db,
            name="European Physical Journal B: Condensed Matter and Complex Systems",
            abbreviation="Eur. Phys. J. B",
        )

        _database_merge(
            db=db,
            name="Czechoslovak Journal of Physics",
            abbreviation="Czech. J. Phys.",
        )

        _database_merge(
            db=db,
            name="General Relativity and Gravitation",
            abbreviation="Gen. Relativ. Gravit.",
        )

        _database_merge(
            db=db,
            name="Comptes Rendus Physique",
            abbreviation="C. R. Physique",
        )

        _database_merge(
            db=db,
            name="Journal of Electronic Materials",
            abbreviation="J. Electron. Mater.",
        )

        _database_merge(
            db=db,
            name="Helvetica Physica Acta",
            abbreviation="Helv. Phys. Acta",
        )

        _database_merge(
            db=db,
            name="Beiträge Zur Physik der Atmosphäre",
            abbreviation="Beitr. Zur Phys. Atmos.",
        )

        _database_merge(
            db=db,
            name="IEEE Transactions on Microwave Theory and Techniques",
            abbreviation="IEEE Trans. Microw. Theory Tech.",
        )

        _database_merge(
            db=db,
            name="Journal of Physics: Condensed Matter",
            abbreviation="J. Phys. Condens. Matter",
        )

        _database_merge(
            db=db,
            name="Journal of Quantitative Spectroscopy & Radiative Transfer",
            abbreviation="J. Quant. Spectrosc. Radiat. Transf.",
        )

        _database_merge(
            db=db,
            name="Journal of Statistical Mechanics: Theory and Experiment",
            abbreviation="J. Stat. Mech.",
        )

        _database_merge(
            db=db,
            name="Materials Research Society Symposium Proceedings",
            abbreviation="Mat. Res. Soc. Symp. Proc.",
        )

        base = "Philosophical Transactions of the Royal Society"
        _database_merge(
            db=db,
            name=f"{base} A: Mathematical, Physical and Engineering Sciences",
            abbreviation="Philos. Trans. R. Soc. A",
        )

        base = "Proceedings of the Royal Society of London"
        _database_merge(
            db=db,
            name=f"{base}, Series A: Mathematical and Physical Sciences",
            abbreviation="Proc. R. Soc. London, Ser. A",
        )

        _database_merge(
            db=db,
            name="Proceedings of the Royal Society of London A",
            abbreviation="Proc. R. Soc. Lond. A",
        )

        _database_merge(
            db=db,
            name="Physical Chemistry Chemical Physics",
            abbreviation="Phys. Chem. Chem. Phys.",
        )

        _database_merge(
            db=db,
            name="Quantum Electronics",
            abbreviation="Quantum Electron.",
        )

        _database_merge(
            db=db,
            name="Transactions of the American Geophysical Union",
            abbreviation="Trans. Am. Geophys. Union",
        )

        _database_merge(
            db=db,
            name="Zeitschrift für Kristallographie",
            abbreviation="Z. für Krist.",
        )

        _database_merge(
            db=db,
            name="Proceedings of SPIE",
            abbreviation="Proc. SPIE",
        )

        _database_merge(
            db=db,
            name="Comptes Rendus de l'Académie des Sciences - Series I - Mathematics",
            abbreviation="C. R. Acad. Sci., Ser. I",
        )

        _database_merge(
            db=db,
            name="Comptes Rendus Hebdomadaires des Séances de l'Académie des Sciences",
            abbreviation="C. R. Acad. Sci.",
        )

        _database_merge(
            db=db,
            name="Journal de Physique IV",
            abbreviation="J. Phys. IV",
        )

        _database_merge(
            db=db,
            name="Zeitschrift für Physik",
            abbreviation="Z. Phys.",
        )

        _database_merge(
            db=db,
            name="IEEE Journal of Selected Topics in Quantum Electronics",
            abbreviation="IEEE J. Sel. Top. Quantum Electron.",
        )

        _database_merge(
            db=db,
            name="Phase Transitions",
            abbreviation="Phase Transit.",
        )

        _database_merge(
            db=db,
            name="Nano Futures",
            abbreviation="Nano Futur.",
        )

        _database_merge(
            db=db,
            name="Kongelige Danske Videnskabernes Selskab, Matematisk-Fysiske Meddelelser",
            abbreviation="K. Dan. Vidensk. Selsk. Mat. Fys. Medd.",
        )

        _database_merge(
            db=db,
            name="Modelling and Simulation in Materials Science and Engineering",
            abbreviation="Model. Simul. Mater. Sci. Eng.",
        )

        db["Physical Review Letters"].set_acronym("PRL")
        db["Physical Review X"].set_acronym("PRX")
        db["Journal of the Mechanics and Physics of Solids"].set_acronym("JMPS")
        db["International Journal of Solids and Structures"].set_acronym("IJSS")
        db["Science"].add_variation("Science (80-. ).")
        db["EPL (Europhysics Letters)"].add_variation("EPL (Europhysics Lett.")

    elif domain == "mechanics":

        db = generate_jabref("mechanical")

        _database_merge(
            db=db,
            name="Proceedings of the National Academy of Sciences of the United States of America",
            abbreviation="Proc. Natl. Acad. Sci. U.S.A.",
            acronym="PNAS",
            merge=[
                "Proceedings of the National academy of Sciences of the United States of America"
            ],
        )

        base = "Comptes Rendus de"
        _database_merge(
            db=db,
            name=f"{base} l'Academie des Sciences Serie III: Sciences de la Vie",
            abbreviation="C. R. Acad. Sci., Ser. III",
            merge=[f"{base} l' Academie des Sciences Serie III: Sciences de la Vie"],
        )

        _database_merge(
            db=db,
            name=f"{base} l'Academie des Sciences Serie IIa: Sciences de la Terre et des Planets",
            abbreviation="C. R. Acad. Sci., Ser. IIa",
            merge=[
                f"{base} l' Academie des Sciences Serie IIa:Sciences de la Terre et des Planets"
            ],
        )

        _database_merge(
            db=db,
            name=f"{base} l'Academie des Sciences Serie IIb: Mecanique Physique Chimie Astronomie",
            abbreviation="C. R. Acad. Sci., Ser. IIb",
            merge=[
                f"{base} l' Academie des Sciences Serie IIb:Mecanique Physique Chimie Astronomie"
            ],
        )

        _database_merge(
            db=db,
            name="Comptes Rendus de l'Academie des Sciences Serie IIc: Chemie",
            abbreviation="C. R. Acad. Sci., Ser. IIc",
            merge=["Comptes Rendus de l' Academie des Sciences Serie IIc:Chemie"],
        )

        base = "Proceedings of the Institution of Mechanical Engineers"
        _database_merge(
            db=db,
            name=f"{base}, Part A: Journal of Power and Energy",
            abbreviation="Proc. Inst. Mech. Eng. Part A",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part B: Journal of Engineering Manufacture",
            abbreviation="Proc. Inst. Mech. Eng. Part B",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part C: Journal of Mechanical Engineering Science",
            abbreviation="Proc. Inst. Mech. Eng. Part C",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part D: Journal of Automobile Engineering",
            abbreviation="Proc. Inst. Mech. Eng. Part D",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part E: Journal of Process Mechanical Engineering",
            abbreviation="Proc. Inst. Mech. Eng. Part E",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part F: Journal of Rail and Rapid Transit",
            abbreviation="Proc. Inst. Mech. Eng. Part F",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part G: Journal of Aerospace Engineering",
            abbreviation="Proc. Inst. Mech. Eng. Part G",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part H: Journal of Engineering in Medicine",
            abbreviation="Proc. Inst. Mech. Eng. Part H",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part J: Journal of Engineering Tribology",
            abbreviation="Proc. Inst. Mech. Eng. Part J",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part K: Journal of Multi-body Dynamics",
            abbreviation="Proc. Inst. Mech. Eng. Part K",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part L: Journal of Materials: Design and Applications",
            abbreviation="Proc. Inst. Mech. Eng. Part L",
        )

        _database_merge(
            db=db,
            name=f"{base}, Part M: Journal of Engineering for the Maritime Environment",
            abbreviation="Proc. Inst. Mech. Eng. Part M",
        )

        _database_merge(
            db=db,
            name=f"{base}. Part I: Journal of Systems and Control Engineering",
            abbreviation="Proc. Inst. Mech. Eng. Part I",
        )

        db["International Journal for Numerical Methods in Engineering"].set_acronym("IJNME")
        db["Journal of the Mechanics and Physics of Solids"].set_acronym("JMPS")
        db["International Journal of Solids and Structures"].set_acronym("IJSS")

        key = "Materials Science and Engineering A"
        db[key].add_variation("Materials Science and Engineering: A")
        db[key].set_abbreviation("Mater. Sci. Eng. A")

        db["Procedia Materials Science"] = Journal(
            name="Procedia Materials Science", abbreviation="Procedia Mater. Sci."
        )

    elif domain == "pnas":

        db = generate_default("physics")
        name = "Proceedings of the National Academy of Sciences"
        alias = "Proceedings of the National Academy of Sciences of the United States of America"
        db = {name: db[name] + db[alias]}
        db[name].add_variation("Proc. Nat. Acad. Sci.")
        db[name].add_variation("Proc. Natl. Acad. Sci.")
        db[name].add_variation("Proc. Nat. Acad. Sci. USA")
        db[name].add_variation("Proc. Natl. Acad. Sci. USA")
        db[name].add_variation("Proc. Nat. Acad. Sci. U.S.A")
        db[name].add_variation("Proc. Natl. Acad. Sci. U.S.A")
        db[name].add_variation("Proc. Nat. Acad. Sci. U. S. A")
        db[name].add_variation("Proc. Natl. Acad. Sci. U. S. A")
        db[name].unique()

    elif domain == "pnas-usa":

        db = generate_default("physics")
        name = "Proceedings of the National Academy of Sciences of the United States of America"
        alias = "Proceedings of the National Academy of Sciences"
        db = {name: db[name] + db[alias]}
        db[name].add_variation("Proc. Nat. Acad. Sci.")
        db[name].add_variation("Proc. Natl. Acad. Sci.")
        db[name].add_variation("Proc. Nat. Acad. Sci. USA")
        db[name].add_variation("Proc. Natl. Acad. Sci. USA")
        db[name].add_variation("Proc. Nat. Acad. Sci. U.S.A")
        db[name].add_variation("Proc. Natl. Acad. Sci. U.S.A")
        db[name].add_variation("Proc. Nat. Acad. Sci. U. S. A")
        db[name].add_variation("Proc. Natl. Acad. Sci. U. S. A")
        db[name].unique()

    elif domain == "arxiv":

        db = dict(arXiv=Journal(name="arXiv preprint", abbreviation="arXiv"))

        r = generate_default("physics")
        db["arXiv"] += r["arXiv.org, e-Print Archive Astrophysics"]
        db["arXiv"] += r["arXiv.org, e-Print Archive Condensed Matter"]
        db["arXiv"] += r["arXiv.org, e-Print Archive Physics"]

        r = generate_default("mechanics")
        db["arXiv"] += r["arXiv.org, e-Print Archive Astrophysics"]
        db["arXiv"] += r["arXiv.org, e-Print Archive Condensed Matter"]
        db["arXiv"] += r["arXiv.org, e-Print Archive General Relativity and Quantum Cosmology"]
        db["arXiv"] += r["arXiv.org, e-Print Archive High Energy Physics - Experimental"]
        db["arXiv"] += r["arXiv.org, e-Print Archive High Energy Physics - Lattice"]
        db["arXiv"] += r["arXiv.org, e-Print Archive High Energy Physics - Phenomenology"]
        db["arXiv"] += r["arXiv.org, e-Print Archive High Energy Physics - Theory"]
        db["arXiv"] += r["arXiv.org, e-Print Archive Nuclear Experiment"]
        db["arXiv"] += r["arXiv.org, e-Print Archive Nuclear Theory"]
        db["arXiv"] += r["arXiv.org, e-Print Archive Physics"]
        db["arXiv"] += r["arXiv.org, e-Print Archive Quantitative Biology"]
        db["arXiv"] += r["arXiv.org, e-Print Archive Quantum Physics"]

    else:
        raise OSError(f'Unknown domain "{domain}"')

    return db


def update_default():
    """
    Update the default databases shipped with GooseBib.
    """

    dirname = os.path.dirname(__file__)

    for name in ["physics", "mechanics", "PNAS", "PNAS-USA", "arXiv"]:
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
