import numpy as np

import GooseBib as bib


def test_Journal():
    name = "name"
    abbreviation = "abbr"
    acronym = "acro"
    entry = bib.journals.Journal(
        name=name, abbreviation=abbreviation, variations=[name, abbreviation]
    )
    entry = entry.unique()

    assume = dict(
        name=name,
        abbreviation=abbreviation,
    )

    assert assume == dict(entry)

    # overwrite abbreviation

    entry.set_abbreviation(name)
    entry = entry.unique()

    assume = dict(
        name=name,
        variations=[abbreviation],
    )

    assert assume == dict(entry)

    entry.set_abbreviation(abbreviation)
    entry = entry.unique()

    assume = dict(
        name=name,
        abbreviation=abbreviation,
    )

    assert assume == dict(entry)

    # add acronym

    entry.set_acronym(acronym)
    entry = entry.unique()

    assume = dict(
        name=name,
        abbreviation=abbreviation,
        acronym=acronym,
    )

    assert assume == dict(entry)

    # overwrite name

    entry.set_name(abbreviation)
    entry = entry.unique()

    assume = dict(
        name=abbreviation,
        acronym=acronym,
        variations=[name],
    )

    assert assume == dict(entry)

    entry.set_name(name)
    entry.set_abbreviation(abbreviation)
    entry = entry.unique()

    # overwrite variations

    entry.add_variation(name)
    entry.add_variations([abbreviation, acronym])
    entry = entry.unique()

    assume = dict(
        name=name,
        abbreviation=abbreviation,
        acronym=acronym,
    )

    assert assume == dict(entry)


def test_JournalList():
    lst = bib.journals.JournalList()
    lst.names = np.array(["a", "b", "c", "a", "d"])
    lst.index = np.array([0, 0, 3, 2, 2])
    lst.name = -1 * np.array([1, 0, 0, 1, 0])
    lst.abbr = -1 * np.array([0, 1, 0, 0, 0])
    lst.acro = -1 * np.array([0, 0, 0, 0, 1])
    lst._renum()

    m = []
    for i in lst:
        m += [dict(i)]

    n = []
    for i in lst:
        n += [dict(i)]

    mylist = [dict(i) for i in lst.tolist()]

    assert m == n
    assert m == mylist

    lst.unique()

    assume = [dict(name="a", abbreviation="b", variations=["d"]), dict(name="c")]

    assert assume == [dict(i) for i in lst.tolist()]


def test_JournalList_no_force_first():
    lst = bib.journals.JournalList()
    lst.names = np.array(["a", "b", "c", "a", "d"])
    lst.index = np.array([0, 0, 3, 2, 2])
    lst.name = -1 * np.array([1, 0, 0, 1, 0])
    lst.abbr = -1 * np.array([0, 1, 0, 0, 0])
    lst.acro = -1 * np.array([0, 0, 0, 0, 1])
    lst._renum()

    m = []
    for i in lst:
        m += [dict(i)]

    n = []
    for i in lst:
        n += [dict(i)]

    mylist = [dict(i) for i in lst.tolist()]

    assert m == n
    assert m == mylist

    lst.unique(force_first=False)

    assume = [dict(name="a", abbreviation="b", acronym="d"), dict(name="c")]

    assert assume == [dict(i) for i in lst.tolist()]


def test_JournalList_map():
    lst = bib.journals.JournalList()
    lst.names = np.array(["a", "b", "c", "a", "d"])
    lst.index = np.array([0, 0, 3, 2, 2])
    lst.name = -1 * np.array([1, 0, 0, 1, 0])
    lst.abbr = -1 * np.array([0, 1, 0, 0, 0])
    lst.acro = -1 * np.array([0, 0, 0, 0, 1])
    lst._renum()
    lst.unique()

    assert lst.map2name(["b", "foo", "d"]) == ["a", "foo", "a"]
    assert lst.map2abbreviation(["b", "foo", "d"]) == ["b", "foo", "b"]
    assert lst.map2acronym(["b", "foo", "d"]) == ["a", "foo", "a"]


def test_JournalList_map_no_force_first():
    lst = bib.journals.JournalList()
    lst.names = np.array(["a", "b", "c", "a", "d"])
    lst.index = np.array([0, 0, 3, 2, 2])
    lst.name = -1 * np.array([1, 0, 0, 1, 0])
    lst.abbr = -1 * np.array([0, 1, 0, 0, 0])
    lst.acro = -1 * np.array([0, 0, 0, 0, 1])
    lst._renum()
    lst.unique(force_first=False)

    assert lst.map2name(["b", "foo", "d"]) == ["a", "foo", "a"]
    assert lst.map2abbreviation(["b", "foo", "d"]) == ["b", "foo", "b"]
    assert lst.map2acronym(["b", "foo", "d"]) == ["d", "foo", "d"]


def test_load():
    variations = [
        "Proc. Nat. Acad. Sci.",
        "Proc. Nat. Acad. Sci. U. S. A",
        "Proc. Nat. Acad. Sci. U.S.A",
        "Proc. Nat. Acad. Sci. U.S.A.",
        "Proc. Nat. Acad. Sci. USA",
        "Proc. Natl. Acad. Sci. U. S. A",
        "Proc. Natl. Acad. Sci. U.S.A",
        "Proc. Natl. Acad. Sci. U.S.A.",
        "Proc. Natl. Acad. Sci. USA",
        "Proceedings of the National Academy of Sciences of the United States of America",
        "Proceedings of the National academy of Sciences of the United States of America",
    ]

    expect = [
        {
            "name": "Proceedings of the National Academy of Sciences",
            "abbreviation": "Proc. Natl. Acad. Sci.",
            "acronym": "PNAS",
            "variations": variations,
        }
    ]
    read = bib.journals.load("pnas")
    read = [dict(r) for r in read.tolist()]

    assert expect == read
