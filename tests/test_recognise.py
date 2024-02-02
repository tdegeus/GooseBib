import GooseBib as bib


def test_doi():
    doi = "10.1073/pnas.1906551116"
    assert doi == bib.recognise.doi(f"https://doi.org/{doi}")
    assert doi == bib.recognise.doi(f"https://dx.doi.org/{doi}")
    assert doi == bib.recognise.doi(*[f"https://doi.org/{doi}"])
    assert doi == bib.recognise.doi(dict(doi=f"https://doi.org/{doi}"))
    assert doi == bib.recognise.doi(dict(doi=f"https://journals.aps.org/pre/abstract/{doi}"))
    assert doi == bib.recognise.doi(dict(doi=f"https://link.aps.org/doi/{doi}"))
    assert doi == bib.recognise.doi(f"doi: {doi}")
    assert doi == bib.recognise.doi(f"doi:{doi}")


def test_arxiv():
    arxivid = "1904.07635"
    assert arxivid == bib.recognise.arxivid(f"https://arxiv.org/abs/{arxivid}")
    assert arxivid == bib.recognise.arxivid(*[f"https://arxiv.org/abs/{arxivid}"])
    assert arxivid == bib.recognise.arxivid(dict(eprint=f"https://arxiv.org/abs/{arxivid}"))
    assert arxivid == bib.recognise.arxivid(dict(arxivid=f"https://arxiv.org/abs/{arxivid}"))
    assert arxivid == bib.recognise.arxivid(f"arXiv preprint: {arxivid}")
    assert arxivid == bib.recognise.arxivid(f"arXiv prep. {arxivid}")
    assert arxivid == bib.recognise.arxivid(f"arXiv Prep. {arxivid}")
    assert arxivid == bib.recognise.arxivid(f"arXiv: {arxivid}")
    assert arxivid == bib.recognise.arxivid(f"arXiv:{arxivid}")
