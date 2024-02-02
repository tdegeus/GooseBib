import GooseBib as bib


def test_list_cite():
    key = "DeGeus2021"
    mytext = r"The authors of \cite{DeGeus2021} claim that ..."
    assert bib.tex.list_cite(mytext) == [key]
