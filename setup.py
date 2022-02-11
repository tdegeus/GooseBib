from setuptools import find_packages
from setuptools import setup

setup(
    name="GooseBib",
    license="MIT",
    author="Tom de Geus",
    author_email="tom@geus.me",
    description="Reformat BibTeX files",
    long_description="Reformat BibTeX files",
    keywords="LaTeX; BibTeX",
    url="https://github.com/tdegeus/GooseBib",
    packages=find_packages(),
    package_data={"": ["*.yaml"]},
    use_scm_version={"write_to": "GooseBib/_version.py"},
    setup_requires=["setuptools_scm"],
    install_requires=[
        "bibtexparser",
        "click",
        "docopt",
        "GitPython",
        "numpy",
        "PyYAML",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "GbibCheckAuthors = GooseBib.cli.GbibCheckAuthors:main",
            "GbibCheckKeys = GooseBib.cli.GbibCheckKeys:main",
            "GbibCheckLink = GooseBib.cli.GbibCheckLink:main",
            "GbibClean = GooseBib.bibtex:GbibClean",
            "GbibList = GooseBib.cli.GbibList:main",
            "GbibParse = GooseBib.cli.GbibParse:main",
            "GbibSelect = GooseBib.cli.GbibSelect:main",
            "GbibSelectAlias = GooseBib.cli.GbibSelectAlias:main",
            "GbibShowAuthorRename = GooseBib.bibtex:GbibShowAuthorRename",
        ]
    },
)
