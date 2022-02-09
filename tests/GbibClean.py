import os
import shutil
import subprocess
import unittest

import bibtexparser
import yaml

dirname = os.path.dirname(__file__)


class Test_GooseBib(unittest.TestCase):
    """
    GooseBib
    """

    def test_inplace(self):

        source = os.path.join(dirname, "library_mendeley.bib")
        output = os.path.join(dirname, "output.bib")
        shutil.copy2(source, output)
        data = os.path.join(dirname, "library.yaml")
        subprocess.check_output(["GbibClean", "--in-place", output])

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

    def test_mendeley(self):

        source = os.path.join(dirname, "library_mendeley.bib")
        output = os.path.join(dirname, "output.bib")
        data = os.path.join(dirname, "library.yaml")
        subprocess.check_output(["GbibClean", "-f", source, output])

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
        subprocess.check_output(["GbibClean", "-f", source, output])

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

    def test_arxiv_preprint(self):

        source = os.path.join(dirname, "library_arxiv_preprint.bib")
        output = os.path.join(dirname, "output.bib")
        data = os.path.join(dirname, "library_arxiv_preprint.yaml")
        subprocess.check_output(
            ["GbibClean", "-f", "--arxiv", "arXiv preprint: {}", source, output]
        )

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
        subprocess.check_output(["GbibClean", "-f", "--author-sep", " ", source, output])

        with open(output) as file:
            bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

        with open(data) as file:
            data = yaml.load(file.read(), Loader=yaml.FullLoader)

        for key in data:
            data[key]["author"] = data[key]["author"].replace("T.W.J.", "T. W. J.")
            data[key]["author"] = data[key]["author"].replace("R.H.J.", "R. H. J.")
            data[key]["author"] = data[key]["author"].replace("M.G.D.", "M. G. D.")
            data[key]["author"] = data[key]["author"].replace("C.B.", "C. B.")

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
        subprocess.check_output(["GbibClean", "-f", "--no-title", source, output])

        with open(output) as file:
            bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

        for entry in bib.entries:
            self.assertFalse("title" in entry)

        os.remove(output)

    def test_journalrename(self):

        lookup = dict(
            official={
                "IJSS": "International Journal of Solids and Structures",
                "PNAS": "Proceedings of the National Academy of Sciences",
                "MRS": "Mechanics Research Communications",
            },
            abbreviation={
                "IJSS": "Int. J. Solids Struct.",
                "PNAS": "Proc. Natl. Acad. Sci.",
                "MRS": "Mech. Res. Commun.",
            },
            acronym={
                "IJSS": "IJSS",
                "PNAS": "PNAS",
                "MRS": "Mech. Res. Commun.",
            },
        )

        for key in lookup:

            source = os.path.join(dirname, "library_mendeley.bib")
            output = os.path.join(dirname, "output.bib")
            data = os.path.join(dirname, "library.yaml")
            subprocess.check_output(["GbibClean", "-f", "-j", key, source, output])

            with open(output) as file:
                bib = bibtexparser.load(file, parser=bibtexparser.bparser.BibTexParser())

            with open(data) as file:
                data = yaml.load(file.read(), Loader=yaml.FullLoader)

            data["DeGeus2015a"]["journal"] = lookup[key]["IJSS"]
            data["DeGeus2015b"]["journal"] = lookup[key]["IJSS"]
            data["DeGeus2019"]["journal"] = lookup[key]["PNAS"]
            data["DeGeus2013"]["journal"] = lookup[key]["MRS"]

            for entry in bib.entries:

                d = data[entry["ID"]]

                for key in d:
                    if entry[key][0] == "{":
                        self.assertEqual("{" + str(d[key]) + "}", entry[key])
                    else:
                        self.assertEqual(str(d[key]), entry[key])

            os.remove(output)


if __name__ == "__main__":

    unittest.main()
