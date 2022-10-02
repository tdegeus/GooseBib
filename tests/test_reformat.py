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
            bib.reformat.abbreviate_firstname("de Geus, Thomas W. J.\\", sep="   "),
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

        self.assertEqual(
            bib.reformat.abbreviate_firstname(r"{Ben Arous}, {G{\'{e}}rard}", sep="   "),
            r"{Ben Arous}, G.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname(r"Lema{\^{i}}tre, Ana{\"{e}}l", sep="   "),
            r"Lema{\^{i}}tre, A.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname(r"Lema{\^i}tre, Ana{\"e}l", sep="   "),
            r"Lema{\^i}tre, A.",
        )

        self.assertEqual(
            bib.reformat.abbreviate_firstname(r"Manneville, S{\' e}bastien", sep="   "),
            r"Manneville, S.",
        )

        self.assertEqual(
            bib.reformat.autoformat_names(
                r"Chattoraj, Joyjit and Caroli, Christiane and Lemaitre, Ana{\" e}l"
            ),
            r"Chattoraj, J. and Caroli, C. and Lemaitre, A.",
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

    def test_page_range(self):

        self.assertEqual(bib.reformat.number_range("1-6"), "1--6")
        self.assertEqual(bib.reformat.number_range("47–58"), "47--58")
        self.assertEqual(bib.reformat.number_range("100"), "100")


if __name__ == "__main__":

    unittest.main()
