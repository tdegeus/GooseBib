import os
import subprocess
import unittest

import bibtexparser
import yaml

dirname = os.path.dirname(__file__)


class Test_GooseBib(unittest.TestCase):
    """
    GooseBib
    """

    def test_mendeley(self):

        source = os.path.join(dirname, "library_mendeley.bib")
        output = os.path.join(dirname, "output.bib")
        data = os.path.join(dirname, "library.yaml")
        subprocess.check_output(["GbibClean", source, output])

        with open(output) as file:
            bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

        with open(data) as file:
            data = yaml.load(file.read(), Loader=yaml.FullLoader)

        for entry in bib.entries:

            d = data[entry["ID"]]

            for key in d:
                if entry[key][0] == "{":
                    self.assertEqual("{" + str(d[key]) + "}", entry[key])
                else:
                    self.assertEqual(str(d[key]), entry[key])

        os.remove(output)

    def test_hidden_doi_arxiv(self):

        source = os.path.join(dirname, "library_hidden_doi_arxiv.bib")
        output = os.path.join(dirname, "output.bib")
        data = os.path.join(dirname, "library.yaml")
        subprocess.check_output(["GbibClean", source, output])

        with open(output) as file:
            bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

        with open(data) as file:
            data = yaml.load(file.read(), Loader=yaml.FullLoader)

        for entry in bib.entries:

            d = data[entry["ID"]]

            for key in d:
                if entry[key][0] == "{":
                    self.assertEqual("{" + str(d[key]) + "}", entry[key])
                else:
                    self.assertEqual(str(d[key]), entry[key])

        os.remove(output)

    def test_authorsep(self):

        source = os.path.join(dirname, "library_mendeley.bib")
        output = os.path.join(dirname, "output.bib")
        data = os.path.join(dirname, "library.yaml")
        subprocess.check_output(["GbibClean", "--author-sep", " ", source, output])

        with open(output) as file:
            bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

        with open(data) as file:
            data = yaml.load(file.read(), Loader=yaml.FullLoader)

        for key in data:
            data[key]["author"] = data[key]["author"].replace("T.W.J.", "T. W. J.")
            data[key]["author"] = data[key]["author"].replace("R.H.J.", "R. H. J.")
            data[key]["author"] = data[key]["author"].replace("M.G.D.", "M. G. D.")

        for entry in bib.entries:

            d = data[entry["ID"]]

            for key in d:
                if entry[key][0] == "{":
                    self.assertEqual("{" + str(d[key]) + "}", entry[key])
                else:
                    self.assertEqual(str(d[key]), entry[key])

        os.remove(output)

    def test_no_title(self):

        source = os.path.join(dirname, "library_mendeley.bib")
        output = os.path.join(dirname, "output.bib")
        subprocess.check_output(["GbibClean", "--no-title", source, output])

        with open(output) as file:
            bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

        for entry in bib.entries:
            self.assertFalse("title" in entry)

        os.remove(output)


if __name__ == "__main__":

    unittest.main()
