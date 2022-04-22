******
Zetero
******

`Better BibTeX <https://retorque.re/zotero-better-bibtex>`_
is a great tool to export BibTeX-files from Zetero.
A tip to get even cleaner BibTeX-files is to add the following postscript code.

.. code-block:: js

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
