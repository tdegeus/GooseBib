"""
Automatic formatting.
"""
import re

import bibtexparser
from bibtexparser.latexenc import latex_to_unicode


def _subr(regex, sub, text):
    """
    Recursive replacement.
    """

    # make substitutions, get the number of substitutions "n"
    text, n = re.subn(regex, sub, text)

    # continue substituting
    if n:
        return _subr(regex, sub, text)

    return text


def number_range(string: str) -> str:
    """
    Format page range.
    This replaces "-" with "--".

    :param string: A string.
    :return: The reformatted string.
    """

    match = [
        (re.compile(r"([0-9]*)(-)(-?)([0-9]*)"), r"\1--\4"),
        (re.compile(r"([0-9]*)(–)(–?)([0-9]*)", re.UNICODE), r"\1--\4"),
    ]

    for regex, sub in match:
        if re.match(regex, string):
            string = re.sub(regex, sub, string)

    return string


def remove_wrapping_braces(string: str) -> str:
    """
    Remove wrapping "{...}".
    :param string: A string.
    :return: The reformatted string.
    """
    return _subr(r"(\{)(.*)(\})", r"\2", string)


def autoformat_names(names: str, sep: str = " ") -> str:
    """
    Automatically format names. E.g.::

        de Geus, Thomas Willem Jan and Wyart, Matthieu
        de Geus, T.W.J. and Wyart, M.

    :param name: Names formatted as "lastname, firstname and lastname, firstname ...".
    :param sep: Separator to place between initials.
    :return: Formatted names.
    """

    ret = re.split(r"\ and\ ", names.replace("\n", " "), flags=re.IGNORECASE)
    if not re.match(r"(\{)(.*)(\})", names):
        ret = bibtexparser.customization.getnames(ret)
    return " and ".join([abbreviate_firstname(i, sep) for i in ret])


def abbreviate_firstname(name: str, sep: str = " ") -> str:
    """
    Abbreviate first name(s) to initials.

    For example::

        de Geus, Thomas Willem Jan ->
        de Geus, T. W. J.

    :param name: The name formatted as "Lastname, firstname secondname ...".
    :param sep: Separator to place between initials.
    :return: Formatted name.
    """

    if len(name.split(",")) == 1:
        return name

    if len(name.split(",")) > 2:
        raise OSError(f'Unable to interpret name "{name}"')

    # convert:
    # - trailing ".\" to "."
    # - 'illegal' LaTeX that that places the accent on the space

    match = [
        (re.compile(r"^(.*)(\.\\)$"), r"\1."),
        (re.compile(r"(.*)(\")(\ )([a-zA-Z])(.*)", re.UNICODE), r"\1\2\4\5"),
        (re.compile(r"(.*)(\')(\ )([a-zA-Z])(.*)", re.UNICODE), r"\1\2\4\5"),
        (re.compile(r"(.*)(\^)(\ )([a-zA-Z])(.*)", re.UNICODE), r"\1\2\4\5"),
    ]

    for regex, sub in match:
        if re.match(regex, name):
            name = re.sub(regex, sub, name)

    # do replacement

    match = [
        (re.compile(r"(.*)(\(.*\))", re.UNICODE), r"\1"),
        (
            re.compile(r"([\w][\}]*)([\w0-9\{\}\`\'\"\\\.\^\{]*)", re.UNICODE),
            r"\1.",
        ),
        (re.compile(r"([\w\.][\-]?)([\ ]*)", re.UNICODE), r"\1"),
    ]

    last, first = name.split(",")
    first = latex_to_unicode(first)
    first = first.replace(".", ". ").replace("-", "- ").replace(r"\. ", r"\.") + " "
    names = [latex_to_unicode(i[0]) for i in re.findall(r"([^\s]*)(\s+)", first)][1:]

    for i in range(len(names)):
        for regex, sub in match:
            names[i] = re.sub(regex, sub, names[i])

    return last + ", " + sep.join([rm_unicode(i) for i in names]).upper()


def name2key(name: str) -> str:
    """
    Return last name as 'citation key'.

    This returns the last name:

    * Without accents.
    * Without spaces.
    * Starting with a capital letter.

    :param name: The name formatted as "Lastname, firstname secondname ...".
    :return: Formatted name.
    """

    assert len(name.split(",")) > 1

    last = name.split(",")[0]
    last = rm_accents(last)
    last = last.replace("{", "")
    last = last.replace("}", "")
    last = last[0].upper() + last[1:]

    return last


def protect_math(text: str) -> str:
    """
    Protect math mode.

    :param text: Some text.
    :return: Formatted text.
    """

    # skip text without any math
    if len(text.split(r"{\$}")) < 3:
        return text

    match = [
        (re.compile(r"(\{\\\$\})(.*)(\{\\\$\})", re.UNICODE), r"$\2$"),
        (re.compile(r"(\$\$)(.*)(\$\$)", re.UNICODE), r"$\2$"),
        (re.compile(r"(\$)(.*)(\{\\{\})(.*)(\$)", re.UNICODE), r"\1\2{\4\5"),
        (re.compile(r"(\$)(.*)(\{\\}\})(.*)(\$)", re.UNICODE), r"\1\2}\4\5"),
        (re.compile(r"(\$)(.*)(\{\\_\})(.*)(\$)", re.UNICODE), r"\1\2_\4\5"),
        (re.compile(r"(\$)(.*)(\{\\^\})(.*)(\$)", re.UNICODE), r"\1\2^\4\5"),
        (re.compile(r"(\$)(.*)(\\backslash)(.*)(\$)", re.UNICODE), r"\1\2\\\4\5"),
    ]

    for regex, sub in match:
        text = _subr(regex, sub, text)

    return text


def rm_unicode(text: str) -> str:
    """
    Remove unicode.

    :param text: Some text.
    :return: Formatted text.
    """

    # NB list not exhaustive, please extend!
    match = [
        ("ç", r"\c{c}"),
        ("è", r"\`{e}"),
        ("é", r"\'{e}"),
        ("É", r"\'{E}"),
        ("ë", r"\"{e}"),
        ("ô", r"\^{o}"),
        ("ö", r"\"{o}"),
        ("ü", r"\"{y}"),
        ("g̃", r"\~{g}"),
        ("ñ", r"\~{n}"),
        ("İ", r"\.{I}"),
        ("à", r"\'{a}"),
        ("ă", r"\v{a}"),
        ("ř", r"\v{r}"),
        ("–", "--"),
        ("—", "--"),
        ("“", "``"),
        ("”", "''"),
        ("×", r"$\times$"),
    ]

    for ex, sub in match:
        text = text.replace(ex, sub)

    return text


def rm_accents(text: str) -> str:
    """
    Remove accents.

    :param text: Some text.
    :return: Formatted text.
    """

    text = rm_unicode(text)

    match = [
        (r"\c{c}", "c"),
        (r"\`{e}", "e"),
        (r"\'{e}", "e"),
        (r"\'{E}", "E"),
        (r"\"{e}", "e"),
        (r"\^{o}", "o"),
        (r"\"{o}", "o"),
        (r"\"{y}", "y"),
        (r"\~{g}", "g"),
        (r"\~{n}", "n"),
        (r"\.{I}", "I"),
        (r"\'{a}", "a"),
        (r"\v{a}", "a"),
        (r"\v{r}", "r"),
        (r"{\"{a}}", "a"),
        (r"{\"{u}}", "u"),
        (r"{\'{c}}", "c"),
        (r"{\'{s}}", "s"),
        (r"{\^{i}}", "i"),
        (r"{\v{s}}", "s"),
        (r"{\v{z}}", "z"),
        (r"\aa", "a"),
        (r"{\o}", "o"),
        (r"'", ""),
        (r" ", ""),
    ]

    for ex, sub in match:
        text = text.replace(ex, sub)

    return text


if __name__ == "__main__":
    pass
