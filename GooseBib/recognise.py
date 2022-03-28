import re
from functools import singledispatch


@singledispatch
def doi():
    """
    Try to match a doi, return the first match.

    :param args: Arguments to check,
    :return: The first match (stripped for url etc.).
    """


@doi.register(str)
def _(*args):

    match = [
        (
            re.compile(r"(.*)(http)(s?)(://)([^\s]*)(doi.org/)([^\s]*)(.*)", re.IGNORECASE),
            7,
        ),
        (re.compile(r"(.*)(doi/abs/)([^\s]*)(.*)", re.IGNORECASE), 3),
        (re.compile(r"(.*)(doi)([^0-9]*)([^\s]*)(.*)", re.IGNORECASE), 4),
        (
            re.compile(
                r"(.*)(http)(s?)(://journals.aps.org/)(.*)(/abstract/)([^\s]*)(.*)", re.IGNORECASE
            ),
            7,
        ),
    ]

    for regex, index in match:
        for arg in args:
            if re.match(regex, arg):
                match = re.split(regex, arg)[index].strip()
                if not re.match(r"(.*)([\s])(.*)", match):
                    return match

    return None


@doi.register(dict)
def _(entry):

    for key in ["doi"]:
        if key in entry:
            return doi(entry[key])

    return doi(*[val for key, val in entry.items() if key not in ["arxivid", "eprint"]])


@singledispatch
def arxivid():
    """
    Try to match a arxiv-id, return the first match.

    :param args: Arguments to check.
    :return: The first match (stripped for url etc.).
    """


@arxivid.register(str)
def _(*args):

    match = [
        (
            re.compile(
                r"(.*)(http)(s?)(://)([^\s]*)(arxiv.org/abs/)([^\s]*)(.*)",
                re.IGNORECASE,
            ),
            7,
        ),
        (re.compile(r"(.*)(arxiv)([^:]*)([:]?)([\s]*)([^\s]*)(.*)", re.IGNORECASE), 6),
        (re.compile(r"([0-9]*\.[0-9]*[v]?[0-9]*)", re.IGNORECASE), 1),
        (
            re.compile(
                r"(.*)(http)(s?)(://doi.org/10.48550/arXiv.)([^\s]*)(.*)",
                re.IGNORECASE,
            ),
            5,
        ),
    ]

    for regex, index in match:
        for arg in args:
            if re.match(regex, arg):
                match = re.split(regex, arg)[index].strip()
                if not re.match(r"(.*)([\s])(.*)", match):
                    return match

    return None


@arxivid.register(dict)
def _(entry):

    for key in ["arxivid", "eprint"]:
        if key in entry:
            return arxivid(entry[key])

    return arxivid(*[val for key, val in entry.items()])


if __name__ == "__main__":
    pass
