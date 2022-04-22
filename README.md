[![ci](https://github.com/tdegeus/GooseBib/workflows/CI/badge.svg)](https://github.com/tdegeus/GooseBib/actions)
[![Documentation Status](https://readthedocs.org/projects/goosebib/badge/?version=latest)](https://goosebib.readthedocs.io/en/latest/?badge=latest)
[![pre-commit](https://github.com/tdegeus/GooseBib/workflows/pre-commit/badge.svg)](https://github.com/tdegeus/GooseBib/actions)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/goosebib.svg)](https://anaconda.org/conda-forge/goosebib)

**Documentation: [https://goosebib.readthedocs.io](goosebib.readthedocs.io)**

<!-- MarkdownTOC -->

- [Usage](#usage)
    - [pre-commit](#pre-commit)
    - [From the command-line](#from-the-command-line)
    - [From Python](#from-python)
- [Disclaimer](#disclaimer)
- [Getting GooseBib](#getting-goosebib)
    - [Using conda](#using-conda)
    - [Using PyPi](#using-pypi)
    - [From source](#from-source)

<!-- /MarkdownTOC -->

# Usage

Clean-up and correct BibTeX files.

## pre-commit

For example:

```yaml
repos:
- repo: https://github.com/tdegeus/GooseBib
  rev: v0.6.0
  hooks:
  - id: GbibClean
    args: ['--arxiv=arXiv preprint: {}']

```

## From the command-line

*   [`GbibClean`](https://goosebib.readthedocs.io/en/latest/tools.html#GbibClean)
    Clean-up a BibTeX file, removing it from unnecessary fields and applying several fixes,
    including abbreviating authors.

*   [`GbibDiscover`](https://goosebib.readthedocs.io/en/latest/tools.html#GbibDiscover)
    Check online databases to see if entries in a BibTeX file went out-to-data.

## From Python

All of these tools wrap around a
[Python module](https://texplain.readthedocs.io/en/latest/module.html)
that you can use just as well!

# Disclaimer

This library is free to use under the
[MIT license](https://github.com/tdegeus/GooseBib/blob/master/LICENSE).
Any additions are very much appreciated, in terms of suggested functionality, code, documentation,
testimonials, word-of-mouth advertisement, etc.
Bug reports or feature requests can be filed on [GitHub](https://github.com/tdegeus/GooseBib).
As always, the code comes with no guarantee.
None of the developers can be held responsible for possible mistakes.

Download:
[.zip file](https://github.com/tdegeus/GooseBib/zipball/master) |
[.tar.gz file](https://github.com/tdegeus/GooseBib/tarball/master).

(c - [MIT](https://github.com/tdegeus/GooseBib/blob/master/LICENSE)) T.W.J. de Geus (Tom) |
tom@geus.me |
www.geus.me |
[github.com/tdegeus/GooseBib](https://github.com/tdegeus/GooseBib)

# Getting GooseBib

## Using conda

```bash
conda install -c conda-forge goosebib
```

## Using PyPi

```bash
python -m pip install GooseBib
```

## From source

```bash
# Download GooseBib
git checkout https://github.com/tdegeus/GooseBib.git
cd GooseBib

# Install
python -m pip install .
```
