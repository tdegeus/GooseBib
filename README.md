# GooseBib

<!-- MarkdownTOC -->

- [Overview](#overview)
- [Installation](#installation)

<!-- /MarkdownTOC -->

# Overview

Some simple command-line tools to clean-up BibTeX files. The following tools are available:

*   [GbibSelect](bin/GbibSelect)

    Select only those entries present in a TeX file (or in a project composed of several TeX files).

*   [GbibParse](bin/GbibParse)

    Basic parse of a BibTeX file, to increase compliance with the standard.

*   [GbibClean](bin/GbibClean)

    Clean-up a BibTeX file, removing it from unnecessary fields and applying several fixes, including abbreviating authors.

*   [GbibList](bin/GbibList)

    List a specific field for all BibTeX entries.

*   [GbibCheckAuthors](bin/GbibCheckAuthors)

    Check for authors that are possibly stored in more than one way.

*   [GbibCheckLink](bin/GbibCheckLink)

    Check that the "doi", "arxivid", and "url" of the entries are valid links (slow!). Note that this function only checks the links to be valid. It does not check if they refer to the correct reference.

# Installation

To get these scripts to work you can:

-   Point the `$PATH` to the `bin/` folder of this directory, for example by adding the following line to the `~/.bashrc`:
  
    ```bash
    export PATH=/path/to/GooseBib/bin:$PATH
    ```

-   'Install' GooseBib's scripts in a default location:

    ```bash
    cd /path/to/GooseBib
    mkdir build
    cd build
    cmake .. 
    make install
    ```

-   'Install' the scripts in your home folder:
  
    1.  Create a directory to store libraries in the home folder. For example:
  
        ```bash
        mkdir ~/opt
        ```

    2.  'Install' GooseBib's scripts. For example
  
        ```bash
        cd /path/to/GooseBib
        mkdir build
        cd build
        cmake .. -DCMAKE_INSTALL_PREFIX:PATH=$HOME/opt
        make install
        ```
     
    3.  Make the `bin/` folder of this 'installation' directory locatable, by adding to the `~/.bashrc`:
 
        ```bash
        export PATH=$HOME/opt/bin:$PATH
        ```

> Note that one has to have Python3 is needed. Additionally:
>      
> *    [Install "docopt"](https://pypi.python.org/pypi/docopt/) using
> 
>      ```bash
>      pip3 install docopt
>      ```
>      
> *    [Install "bibtexparser"](https://github.com/sciunto-org/python-bibtexparser) using
> 
>      ```bash
>      pip3 install bibtexparser
>      ```
>      
> The `--user` option can be used to install the library to your own home-folder. 


