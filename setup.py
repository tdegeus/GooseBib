
from setuptools import setup
from setuptools import find_packages
import re

filepath = 'GooseBib/__init__.py'
__version__ = re.findall(r'__version__ = \'(.*)\'', open(filepath).read())[0]

setup(
    name = 'GooseBib',
    version = __version__,
    license = 'MIT',
    author = 'Tom de Geus',
    author_email = 'tom@geus.me',
    description = 'Reformat BibTeX files',
    long_description = 'Reformat BibTeX files',
    keywords = 'LaTeX; BibTeX',
    url = 'https://github.com/tdegeus/GooseBib',
    packages = find_packages(),
    install_requires = ['docopt>=0.6.2', 'click>=4.0', 'bibtexparser>=1.0.0', 'requests>=2.0.0'],
    entry_points = {
        'console_scripts': [
            'GbibCheckAuthors = GooseBib.cli.GbibCheckAuthors:main',
            'GbibCheckLink = GooseBib.cli.GbibCheckLink:main',
            'GbibCheckKeys = GooseBib.cli.GbibCheckKeys:main',
            'GbibClean = GooseBib.cli.GbibClean:main',
            'GbibList = GooseBib.cli.GbibList:main',
            'GbibParse = GooseBib.cli.GbibParse:main',
            'GbibSelect = GooseBib.cli.GbibSelect:main',
            'GbibSelectAlias = GooseBib.cli.GbibSelectAlias:main']})
