import re


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


def initials(name: str, sep: str = " "):
    """
    Reformat a name such that first names are abbreviated to initials, for example::

        de Geus, Thomas Willem Jan ->
        de Geus, T. W. J.

    :param name: The name formatted as "Lastname, firstname otherfirstname"
    :param sep: Separator to place between initials.
    :return: Formatted name.
    """

    assert len(name.split(",")) > 1

    match = [
        (re.compile(r"(.*)(\(.*\))", re.UNICODE), r"\1"),
        (
            re.compile(r"([A-Za-z][\}]*)([\w0-9\{\}\`\'\"\\\.\^\{]*)", re.UNICODE),
            r"\1.",
        ),
        (re.compile(r"([A-Za-z\.][\-]?)([\ ]*)", re.UNICODE), r"\1"),
        (
            re.compile(r"([A-Za-z\.][\-]?)([A-Za-z])", re.UNICODE),
            r"\1" + sep + r"\2",
        ),
    ]

    last, first = name.split(",")

    # extend all "." with a space, to distinguish initials
    first = first.replace(".", ". ")

    for regex, sub in match:
        first = re.sub(regex, sub, first)

    first = first.strip()

    return last + ", " + first.upper()


def protect_math(text):
    """
    Protect math mode.
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


if __name__ == "__main__":
    pass
