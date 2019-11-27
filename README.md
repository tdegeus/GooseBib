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
conda install -c conda-forge GooseBib
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

*   [GbibClean](bin/GbibClean)

    Clean-up a BibTeX file, removing it from unnecessary fields and applying several fixes, including abbreviating authors.

*   [GbibParse](bin/GbibParse)

    Basic parse of a BibTeX file, to increase compliance with the standard.

*   [GbibSelect](bin/GbibSelect)

    Select only those entries present in a TeX file (or in a project composed of several TeX files).

*   [GbibSelectAlias](bin/GbibSelectAlias)

    Select specific BibTeX fields and (optionally) choose the citation key. The selection is provided to the program using a json-file.

*   [GbibList](bin/GbibList)

    List a specific field for all BibTeX entries.

*   [GbibCheckAuthors](bin/GbibCheckAuthors)

    Check for authors that are possibly stored in more than one way.

*   [GbibCheckLink](bin/GbibCheckLink)

    Check that the "doi", "arxivid", and "url" of the entries are valid links (slow!). Note that this function only checks the links to be valid. It does not check if they refer to the correct reference.

