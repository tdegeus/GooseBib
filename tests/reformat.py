import unittest

import GooseBib as bib


class Test_reformat(unittest.TestCase):
    """
    GooseBib.reformat
    """

    def test_abbreviate_firstname(self):

        self.assertEqual(
            bib.reformat.abbreviate_firstname("de Geus, Thomas Willem Jan"),
            "de Geus, T. W. J.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname("de Geus, Thomas Willem Jan", sep="   "),
            "de Geus, T.   W.   J.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname("de Geus, Thomas W. J.", sep="   "),
            "de Geus, T.   W.   J.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname("de Geus, Thomas W.J.", sep="   "),
            "de Geus, T.   W.   J.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname(r"Molinari, Jean-Fran{\c c}ois", sep="   "),
            "Molinari, J.-   F.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname(r"Temizer, \.{I}.", sep="   "),
            r"Temizer, \.{I}.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname(r"Temizer, \.{I}.\.{I}.", sep="   "),
            r"Temizer, \.{I}.   \.{I}.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname(r"Temizer, \.{I}.\.{I}zemer", sep="   "),
            r"Temizer, \.{I}.   \.{I}.",
        )

    def test_protect_math(self):

        simple = r"$\tau$"
        self.assertEqual(bib.reformat.protect_math(simple), simple)

    def test_rm_unicode(self):

        simple = r"$de Geus, Tom$"
        self.assertEqual(bib.reformat.rm_unicode(simple), simple)

    def test_rm_accents(self):

        self.assertEqual(bib.reformat.rm_accents("école"), "ecole")
        self.assertEqual(bib.reformat.rm_accents("École"), "Ecole")

    def test_name2key(self):

        self.assertEqual(bib.reformat.name2key("de Geus, Tom"), "DeGeus")


if __name__ == "__main__":

    unittest.main()
