import re


def list_cite(tex):
    r"""
    List all citation keys in::

        \cite{...}
        \citet{...}
        \citep{...}
    """

    # extract keys from "cite"
    def extract(s):
        try:
            return list(
                re.split(r"([pt])?(\[.*\]\[.*\])?(\{[a-zA-Z0-9\,\-\ ]*\})", s)[3][1:-1].split(",")
            )
        except:
            print("Error in interpreting\n {0} ...").format(s[:100])

    # read all keys in "cite", "citet", "citep" commands
    cite = [extract(i) for i in tex.split(r"\cite")[1:]]
    cite = list({item for sublist in cite for item in sublist})
    cite = [i.replace(" ", "") for i in cite]

    return cite
