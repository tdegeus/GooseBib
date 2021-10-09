import unittest

import GooseBib as bib


class Test_recognise(unittest.TestCase):
    """
    GooseBib.recognise
    """

    def test_doi(self):

        doi = "10.1073/pnas.1906551116"
        self.assertEqual(doi, bib.recognise.doi(f"https://doi.org/{doi}"))
        self.assertEqual(doi, bib.recognise.doi(*[f"https://doi.org/{doi}"]))
        self.assertEqual(doi, bib.recognise.doi(dict(doi=f"https://doi.org/{doi}")))

    def test_arxiv(self):

        arxivid = "1904.07635"
        self.assertEqual(
            arxivid, bib.recognise.arxivid(f"https://arxiv.org/abs/{arxivid}")
        )
        self.assertEqual(
            arxivid, bib.recognise.arxivid(*[f"https://arxiv.org/abs/{arxivid}"])
        )
        self.assertEqual(
            arxivid,
            bib.recognise.arxivid(dict(eprint=f"https://arxiv.org/abs/{arxivid}")),
        )
        self.assertEqual(
            arxivid,
            bib.recognise.arxivid(dict(arxivid=f"https://arxiv.org/abs/{arxivid}")),
        )
        self.assertEqual(arxivid, bib.recognise.arxivid(f"arXiv preprint: {arxivid}"))


if __name__ == "__main__":

    unittest.main()
