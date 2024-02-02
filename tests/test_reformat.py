import GooseBib as bib


def test_abbreviate_firstname():
    names = [
        ["de Geus, Thomas Willem Jan", " ", "de Geus, T. W. J."],
        ["de Geus, Thomas Willem Jan", "   ", "de Geus, T.   W.   J."],
        ["de Geus, Thomas W. J.", "   ", "de Geus, T.   W.   J."],
        ["de Geus, Thomas W. J.\\", "   ", "de Geus, T.   W.   J."],
        ["de Geus, Thomas W.J.", "   ", "de Geus, T.   W.   J."],
        [r"Molinari, Jean-Fran{\c c}ois", "   ", "Molinari, J.-   F."],
        [r"Temizer, \.{I}.", "   ", r"Temizer, \.{I}."],
        [r"Temizer, \.{I}.\.{I}.", "   ", r"Temizer, \.{I}.   \.{I}."],
        [r"Temizer, \.{I}.\.{I}zemer", "   ", r"Temizer, \.{I}.   \.{I}."],
        [r"{Ben Arous}, {G{\'{e}}rard}", "   ", r"{Ben Arous}, G."],
        [r"Lema{\^{i}}tre, Ana{\"{e}}l", "   ", r"Lema{\^{i}}tre, A."],
        [r"Lema{\^i}tre, Ana{\"e}l", "   ", r"Lema{\^i}tre, A."],
        [r"Manneville, S{\' e}bastien", "   ", r"Manneville, S."],
    ]

    for oldname, sep, newname in names:
        assert bib.reformat.abbreviate_firstname(oldname, sep=sep) == newname


def test_autoformat_names():
    names = [
        [
            r"Chattoraj, Joyjit and Caroli, Christiane and Lemaitre, Ana{\" e}l",
            r"Chattoraj, J. and Caroli, C. and Lemaitre, A.",
        ]
    ]

    for oldname, newname in names:
        assert bib.reformat.autoformat_names(oldname) == newname


def test_protect_math():
    simple = r"$\tau$"
    assert bib.reformat.protect_math(simple) == simple


def test_rm_unicode():
    simple = r"$de Geus, Tom$"
    assert bib.reformat.rm_unicode(simple) == simple


def test_rm_accents():
    assert bib.reformat.rm_accents("école") == "ecole"
    assert bib.reformat.rm_accents("École") == "Ecole"


def test_name2key():
    assert bib.reformat.name2key("de Geus, Tom") == "DeGeus"


def test_page_range():
    assert bib.reformat.number_range("1-6") == "1--6"
    assert bib.reformat.number_range("47–58") == "47--58"
    assert bib.reformat.number_range("100") == "100"
