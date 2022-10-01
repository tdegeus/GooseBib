import unittest

import GooseBib as bib


class Test_bibtex(unittest.TestCase):
    """
    GooseBib.bibtex
    """

    def test_clever_merge(self):

        text = """
        @article{DeGeus2021,
            author = {De Geus, T.W.J},
            title = {My new hello world},
            journal = {Journal of GooseBib},
            year = {2021},
            volume = {1},
            number = {1},
            pages = {1--6}
        }

        @article{DeGeus2019,
            author = {De Geus, T.W.J},
            title = {My new hello world},
            journal = {arXiv preprint: arXiv:1901.00001},
            year = {2019}
        }

        @article{DeGeus21,
            author = {De Geus, T.W.J},
            title = {My new hello world},
            journal = {Journal of GooseBib},
            year = {2021},
            volume = {1},
            number = {1},
            pages = {1--6},
            doi = {10.1234/1234567890}
        }
        """

        out = """
        @article{DeGeus2021,
            author = {De Geus, T.W.J},
            title = {My new hello world},
            journal = {Journal of GooseBib},
            year = {2021},
            volume = {1},
            number = {1},
            pages = {1--6},
            doi = {10.1234/1234567890}
        }

        @article{DeGeus2019,
            author = {De Geus, T.W.J},
            title = {My new hello world},
            journal = {arXiv preprint: arXiv:1901.00001},
            year = {2019}
        }
        """

        out = out.split("\n")
        out[1] = out[1].strip(" ")
        out[10] = out[10].strip(" ")
        out[12] = out[12].strip(" ")
        out[-2] = out[-2].strip(" ")
        out[-1] = out[-1].strip(" ")
        out = "\n".join(out[1:])

        self.assertEqual(bib.bibtex.clever_merge(text)[0], out)

        text = text.split("\n")
        text[-5] = "            number = {100},"
        text = "\n".join(text)

        with self.assertWarns(Warning):
            self.assertEqual(bib.bibtex.clever_merge(text)[0], out)


if __name__ == "__main__":

    unittest.main()
