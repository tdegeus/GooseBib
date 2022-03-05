# GooseBib

[![ci](https://github.com/tdegeus/GooseBib/workflows/CI/badge.svg)](https://github.com/tdegeus/GooseBib/actions)
[![pre-commit](https://github.com/tdegeus/GooseBib/workflows/pre-commit/badge.svg)](https://github.com/tdegeus/GooseBib/actions)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/goosebib.svg)](https://anaconda.org/conda-forge/goosebib)

<!-- MarkdownTOC -->

- [Getting GooseBib](#getting-goosebib)
    - [Using conda](#using-conda)
    - [Using PyPi](#using-pypi)
    - [From source](#from-source)
- [Overview](#overview)
- [Tips](#tips)
    - [Zotero](#zotero)

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

    Basic parse of a BibTeX file to increase compliance with the standard. Use "GbibClean" for a more rigorous clean-up.

*   [GbibSelect](GooseBib/cli/GbibSelect.py)

    Select only those entries present in a TeX-file.

*   [GbibSelectAlias](GooseBib/cli/GbibSelectAlias.py)

    Select specific BibTeX fields and (optionally) choose the citation key. The selection is provided to the program using a json-file.

*   [GbibList](GooseBib/cli/GbibList.py)

    List a specific field (e.g. the journal) for all BibTeX entries.

*   [GbibCheckAuthors](GooseBib/cli/GbibCheckAuthors.py)

    List authors that are possibly stored in more than one way. Specifically, the algorithm finds those authors that are written in exactly the way after parsing such that first names are abbreviated.

*   [GbibCheckKeys](GooseBib/cli/GbibCheckKeys.py)

    List entries that do not have a citation key composed of "LastName + Year".

*   [GbibCheckLink](GooseBib/cli/GbibCheckLink.py)

    Check that the "doi", "arxivid", and "url" of the entries are valid links (slow!). Note that this function only checks the links to be valid. It does not check if they refer to the correct reference.

# Tips

## Zotero

[Better BibTeX](https://retorque.re/zotero-better-bibtex/) is a great tool to export BibTeX-files
from Zetero.
A tip to get even cleaner BibTeX-files is to add the following postscript code.

```js
if (Translator.BetterBibTeX) {
    if (reference.has.abstract) {
        reference.remove('abstract');
    }
    if (reference.has.note) {
        reference.remove('note');
    }
    if (reference.has.month) {
        reference.remove('month');
    }
    if (reference.has.keywords) {
        reference.remove('keywords');
    }
    if (reference.has.file) {
        reference.remove('file');
    }
    if (item.arXiv.id) {
        reference.add({name: 'arxivid', value: item.arXiv.id});
        if (!reference.has.journal) {
            reference.add({
                name: 'journal',
                bibtex: `{arXiv preprint: ${item.arXiv.id}}`
            });
        }
    }
}
```
