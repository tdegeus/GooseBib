import re

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


def remove_wrapping_braces(string: str):
    """
    Remove wrapping "{...}".
    :param string: A string.
    :return: The reformatted string.
    """
    return _subr(r"(\{)(.*)(\})", r"\2", string)


def abbreviate_firstname(name: str, sep: str = " "):
    """
    Reformat a name such that first names are abbreviated to initials, for example::

        de Geus, Thomas Willem Jan ->
        de Geus, T. W. J.

    :param name: The name formatted as "Lastname, firstname otherfirstname"
    :param sep: Separator to place between initials.
    :return: Formatted name.
    """

    if len(name.split(",")) == 1:
        return name

    if len(name.split(",")) > 2:
        raise OSError(f'Unable to interpret name "{name}"')

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


def name2key(name: str):
    """
    Extract last name:
    - Without accents.
    - Without spaces.
    - Starting with a capital letter.
    """

    assert len(name.split(",")) > 1

    last = name.split(",")[0]
    last = rm_accents(last)
    last = last.replace("{", "")
    last = last.replace("}", "")
    last = last[0].upper() + last[1:]

    return last


def protect_math(text: str):
    """
    Protect math mode.

    :param name: The name formatted as "Lastname, firstname otherfirstname"
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


def rm_unicode(text: str):
    """
    Remove unicode.
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


def rm_accents(text: str):
    """
    Remove accents.
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
