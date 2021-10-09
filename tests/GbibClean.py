import os
import subprocess
import unittest

import bibtexparser
import yaml

dirname = os.path.dirname(__file__)


def run(cmd):
    out = list(filter(None, subprocess.check_output(cmd).decode("utf-8").split("\n")))
    return [i.rstrip().replace("\r", "") for i in out]


class Test_GooseBib(unittest.TestCase):
    """
    GooseBib
    """

    def test_mendeley(self):

        source = os.path.join(dirname, "library_mendeley.bib")
        output = os.path.join(dirname, "output.bib")
        data = os.path.join(dirname, "library.yaml")
        run(["GbibClean", source, output])

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


if __name__ == "__main__":

    unittest.main()
