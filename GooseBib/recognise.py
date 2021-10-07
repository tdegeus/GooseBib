import re


def doi(*args):
    """
    Loop over input arguments and try to match a doi, return the first match.

    :param args: Arguments to check.
    :return: The first match (stripped for url etc.).
    """

    match = [
        (re.compile(r"(.*)(https://doi.org/)([^\s]*)(.*)", re.IGNORECASE), 3),
        (re.compile(r"(.*)(http://doi.org/)([^\s]*)(.*)", re.IGNORECASE), 3),
        (re.compile(r"(.*)(doi/abs/)([^\s]*)(.*)", re.IGNORECASE), 3),
        (re.compile(r"(.*)(doi)([^\s]*)(.*)", re.IGNORECASE), 3),
    ]

    for regex, index in match:
        for arg in args:
            if re.match(regex, arg):
                match = re.split(regex, arg)[index].strip()
                if not re.match(r"(.*)([\s])(.*)", match):
                    return match

    return None


def arxivid(*args):
    """
    Loop over input arguments and try to match a arxiv-id, return the first match.

    :param args: Arguments to check.
    :return: The first match (stripped for url etc.).
    """

    match = [
        (re.compile(r"(.*)(https://arxiv.org/abs/)([^\s]*)(.*)", re.IGNORECASE), 3),
        (re.compile(r"(.*)(http://arxiv.org/abs/)([^\s]*)(.*)", re.IGNORECASE), 3),
        (re.compile(r"(.*)(arxiv)([^:]*)([:]?)(.*)", re.IGNORECASE), 5),
        (re.compile(r"([0-9]*\.[0-9]*[v]?[0-9]*)", re.IGNORECASE), 1),
    ]

    for regex, index in match:
        for arg in args:
            if re.match(regex, arg):
                match = re.split(regex, arg)[index].strip()
                if not re.match(r"(.*)([\s])(.*)", match):
                    return match

    return None


if __name__ == "__main__":
    pass
