# GooseBib

<!-- MarkdownTOC -->

- [Getting GooseBib](#getting-goosebib)
    - [Using conda](#using-conda)
    - [Using PyPi](#using-pypi)
    - [From source](#from-source)
- [Overview](#overview)

<!-- /MarkdownTOC -->

# Getting GooseBib

## Using conda

```bash
conda install -c conda-forge goosebib
```

## Using PyPi

```bash
pip install GooseBib
```

## From source

```bash
# Download GooseBib
git checkout https://github.com/tdegeus/GooseBib.git
cd GooseBib

# Install
python -m pip install .
```

# Overview

Some simple command-line tools to clean-up BibTeX files. The following tools are available:

*   [GbibClean](GooseBib/cli/GbibClean.py)

    Clean-up a BibTeX file, removing it from unnecessary fields and applying several fixes, including abbreviating authors.

*   [GbibParse](GooseBib/cli/GbibParse.py)

    Basic parse of a BibTeX file, to increase compliance with the standard.

*   [GbibSelect](GooseBib/cli/GbibSelect.py)

    Select only those entries present in a TeX file (or in a project composed of several TeX files).

*   [GbibSelectAlias](GooseBib/cli/GbibSelectAlias.py)

    Select specific BibTeX fields and (optionally) choose the citation key. The selection is provided to the program using a json-file.

*   [GbibList](GooseBib/cli/GbibList.py)

    List a specific field for all BibTeX entries.

*   [GbibCheckAuthors](GooseBib/cli/GbibCheckAuthors.py)

    Check for authors that are possibly stored in more than one way.

*   [GbibCheckLink](GooseBib/cli/GbibCheckLink.py)

    Check that the "doi", "arxivid", and "url" of the entries are valid links (slow!). Note that this function only checks the links to be valid. It does not check if they refer to the correct reference.

*   [GbibCheckKeys](GooseBib/cli/GbibCheckKeys.py)

    Check which entries do not have a citation key composed of "LastName + Year".
