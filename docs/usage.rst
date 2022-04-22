*****
Usage
*****

The are three ways to use the tools provided here.

pre-commit
==========

For example:

.. code-block:: yaml

    repos:
    - repo: https://github.com/tdegeus/GooseBib
      rev: v0.6.0
      hooks:
      - id: GbibClean
        args: ['--arxiv=arXiv preprint: {}']

Command-line
============

:ref:`Command-line tools`

Python
======

:ref:`Python module`
