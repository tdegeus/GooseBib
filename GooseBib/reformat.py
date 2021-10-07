import re


def initials(name: str, sep: str = " "):
    """
    Reformat a name such that first names are abbreviated to initials, for example::

        de Geus, Thomas Willem Jan ->
        de Geus, T. W. J.

    :param name: The name formatted as "Lastname, firstname otherfirstname"
    :param sep: Separator to place between initials.
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


if __name__ == "__main__":
    pass
