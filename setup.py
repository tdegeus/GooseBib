from pathlib import Path

from setuptools import find_packages
from setuptools import setup

project_name = "GooseBib"

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name=project_name,
    license="MIT",
    author="Tom de Geus",
    author_email="tom@geus.me",
    description="Reformat BibTeX files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="LaTeX; BibTeX",
    url=f"https://github.com/tdegeus/{project_name:s}",
    packages=find_packages(),
    package_data={"": ["*.yaml"]},
    use_scm_version={"write_to": f"{project_name}/_version.py"},
    setup_requires=["setuptools_scm"],
    install_requires=[
        "arxiv",
        "bibtexparser",
        "click",
        "docopt",
        "GitPython",
        "numpy",
        "PyYAML",
        "requests",
        "tqdm",
    ],
    entry_points={
        "console_scripts": [
            f"GbibCheckAuthors = {project_name}.cli.GbibCheckAuthors:main",
            f"GbibCheckKeys = {project_name}.cli.GbibCheckKeys:main",
            f"GbibCheckLink = {project_name}.cli.GbibCheckLink:main",
            f"GbibClean = {project_name}.bibtex:GbibClean",
            f"GbibList = {project_name}.cli.GbibList:main",
            f"GbibParse = {project_name}.cli.GbibParse:main",
            f"GbibSelect = {project_name}.cli.GbibSelect:main",
            f"GbibSelectAlias = {project_name}.cli.GbibSelectAlias:main",
            f"GbibShowAuthorRename = {project_name}.bibtex:GbibShowAuthorRename",
            f"GbibDiscover = {project_name}.bibtex:GbibDiscover",
        ]
    },
)
