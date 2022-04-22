import unittest

import GooseBib as bib


class Test_tex(unittest.TestCase):
    """
    GooseBib.tex
    """

    def test_list_cise(self):

        key = "DeGeus2021"
        mytext = r"The authors of \cite{DeGeus2021} claim that ..."
        self.assertEqual(bib.tex.list_cite(mytext), [key])


if __name__ == "__main__":

    unittest.main()
