import unittest

import GooseBib as bib


class Test_reformat(unittest.TestCase):
    """
    GooseBib.reformat
    """

    def test_intials(self):

        self.assertEqual(
            bib.reformat.initials("de Geus, Thomas Willem Jan"), "de Geus, T. W. J."
        )

        self.assertEqual(
            bib.reformat.initials("de Geus, Thomas Willem Jan", sep=""),
            "de Geus, T.W.J.",
        )

    def test_protect_math(self):

        simple = r"$\tau$"
        self.assertEqual(bib.reformat.protect_math(simple), simple)


if __name__ == "__main__":

    unittest.main()
