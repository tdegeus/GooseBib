"""GbibClean
  Clean a BibTeX database, stripping it from unnecessary fields, unifying the formatting of authors,
  and ensuring the proper special characters and math mode settings.

Usage:
  GbibClean [options] <input> <output>

Arguments:
  input                   Input BibTeX-file.
  output                  Output file, or path (the "input" file-name is copied).

Options:
      --author-sep=<str>  Character to separate authors' initials. [default: ]
      --ignore-case       Do not protect case of title.
      --ignore-math       Do not apply math-mode fix.
      --ignore-unicode    Do not apply unicode fix.
      --dot-space=<str>   Character separating abbreviation dots. [default: ]
      --no-title          Remove title from BibTeX file.
      --verbose-doi       Print entries from which the doi was automatically extracted.
      --verbose-arxivid   Print entries from which the arxivid was automatically extracted.
      --version           Show version.
  -h, --help              Show help.

(c - MIT) T.W.J. de Geus | tom@geus.me | www.geus.me | github.com/tdegeus/GooseBib
"""

# ==================================================================================================

import os
import re
import sys
import bibtexparser
import docopt

from .. import __version__

# ==================================== RAISE COMMAND LINE ERROR ====================================

def Error(msg,exit_code=1):

  print(msg)

  sys.exit(exit_code)

# ===================================== RECURSIVE REPLACEMENT ======================================

def subr(regex, sub, text):

  # make substitutions, get the number of substitutions "n"
  text, n = re.subn(regex, sub, text)

  # continue substituting
  if n:
    return subr(regex, sub, text)

  return text

# ========================================== EXTRACT DOI ===========================================

def getDoi(*args):

  # define find/replace criteria
  match = [
    (re.compile(r'(.*)(https://doi.org/)([^\s]*)(.*)', re.IGNORECASE), r'\3'),
    (re.compile(r'(.*)(http://doi.org/)([^\s]*)(.*)' , re.IGNORECASE), r'\3'),
    (re.compile(r'(.*)(doi/abs/)([^\s]*)(.*)'        , re.IGNORECASE), r'\3'),
    (re.compile(r'(.*)(doi)([^\s]*)(.*)'             , re.IGNORECASE), r'\3'),
  ]

  # try to find matching entries (and strip them)
  for regex, sub in match:
    for arg in args:
      if re.match(regex, arg):
        num = re.sub(regex, sub, arg)
        if not re.match(r'(.*)([\s])(.*)',num): return num

  # quit function without a positive match
  return None

# ======================================== EXTRACT ARXIVID =========================================

def getArxiv(*args):

  # define find/replace criteria
  match = [
    (re.compile(r'(.*)(https://arxiv.org/abs/)([^\s]*)(.*)', re.IGNORECASE), r'\3'),
    (re.compile(r'(.*)(http://arxiv.org/abs/)([^\s]*)(.*)' , re.IGNORECASE), r'\3'),
    (re.compile(r'(.*)(arxiv)([^:]*)([:]?)(.*)'            , re.IGNORECASE), r'\5'),
    (re.compile(r'([0-9]*\.[0-9]*[v]?[0-9]*)'              , re.IGNORECASE), r'\1'),
  ]

  # try to find matching entries (and strip them)
  for regex, sub in match:
    for arg in args:
      if re.match(regex, arg):
        num = re.sub(regex, sub, arg)
        if not re.match(r'(.*)([\s])(.*)',num): return num

  # quit function without a positive match
  return None

# ======================================== REFORMAT AUTHORS ========================================

def reformatAuthor(text,sep=' '):

  # skip authors that cannot be split in first and last name
  if len(text.split(',')) <= 1:
    return text

  # define find/replace criteria
  match = [
    (re.compile(r'(.*)(\(.*\))'                               , re.UNICODE) ,r'\1'          ),
    (re.compile(r'([A-Za-z][\}]*)([\w0-9\{\}\`\'\"\\\.\^\{]*)', re.UNICODE) ,r'\1.'         ),
    (re.compile(r'([A-Za-z\.][\-]?)([\ ]*)'                   , re.UNICODE) ,r'\1'          ),
    (re.compile(r'([A-Za-z\.][\-]?)([A-Za-z])'                , re.UNICODE) ,r'\1'+sep+r'\2'),
  ]

  # extract first and last name
  last, first = text.split(',')

  # update extend all "." with a space, to distinguish initials
  first = first.replace('.', '. ')

  # loop over over find/replace criteria
  for regex, sub in match:
    first = re.sub(regex, sub, first)

  # remove spaces from the beginning and end
  first = first.strip()

  # rejoin first and last name
  return last + ', ' + first.upper()

# ========================================== PROTECT MATH ==========================================

def protectMath(text):

  # skip text without any math
  if len(text.split('{\$}')) < 3:
    return text

  # define find/replace criteria
  match = [
    (re.compile(r'(\{\\\$\})(.*)(\{\\\$\})'     ,re.UNICODE), r'$\2$'       ),
    (re.compile(r'(\$\$)(.*)(\$\$)'             ,re.UNICODE), r'$\2$'       ),
    (re.compile(r'(\$)(.*)(\{\\{\})(.*)(\$)'    ,re.UNICODE), r'\1\2{\4\5'  ),
    (re.compile(r'(\$)(.*)(\{\\}\})(.*)(\$)'    ,re.UNICODE), r'\1\2}\4\5'  ),
    (re.compile(r'(\$)(.*)(\{\\_\})(.*)(\$)'    ,re.UNICODE), r'\1\2_\4\5'  ),
    (re.compile(r'(\$)(.*)(\{\\^\})(.*)(\$)'    ,re.UNICODE), r'\1\2^\4\5'  ),
    (re.compile(r'(\$)(.*)(\\backslash)(.*)(\$)',re.UNICODE), r'\1\2\\\4\5' ),
  ]

  # loop over over find/replace criteria
  for regex, sub in match:
    text = subr(regex, sub, text)

  return text

# ================================ CONVERT UNICODE SYMBOLS TO LATEX ================================

def replaceUnicode(text):

  # NB list not exhaustive, please extend!
  match = [
    ( u'ç', r'\c{c}'    ),
    ( u'è', r'\`{e}'    ),
    ( u'é', r'\'{e}'    ),
    ( u'ë', r'\"{e}'    ),
    ( u'ô', r'\^{o}'    ),
    ( u'ö', r'\"{o}'    ),
    ( u'ü', r'\"{y}'    ),
    ( u'g̃', r'\~{g}'    ),
    ( u'ñ', r'\~{n}'    ),
    ( u'İ', r'\.{I}'    ),
    ( u'à', r'\'{a}'    ),
    ( u'ă', r'\v{a}'    ),
    ( u'ř', r'\v{r}'    ),
    ( u'–',  '--'       ),
    ( u'—',  '--'       ),
    ( u'“',  '``'       ),
    ( u'”',  "''"       ),
    ( u'×', r'$\times$' ),
  ]

  # loop over over find/replace criteria
  for ex, sub in match:
    text = text.replace(ex, sub)

  return text

# ========================================== MAIN PROGRAM ==========================================

def main():

  # --------------------------------- parse command line arguments ---------------------------------

  # parse command-line options/arguments
  args = docopt.docopt(__doc__, version=__version__)

  # change keys to simplify implementation:
  # - remove leading "-" and "--" from options
  args = {re.sub(r'([\-]{1,2})(.*)',r'\2',key): args[key] for key in args}
  # - change "-" to "_" to facilitate direct use in print format
  args = {key.replace('-','_'): args[key] for key in args}
  # - remove "<...>"
  args = {re.sub(r'(<)(.*)(>)',r'\2',key): args[key] for key in args}

  # --------------------------------------- check arguments ----------------------------------------

  # check that the BibTeX file exists
  if not os.path.isfile(args['input']):
    Error('"{input:s}" does not exist'.format(**args))

  # if "output" is an existing directory; convert to file with same name as the input file
  if os.path.isdir(args['output']):
    args['output'] = os.path.join(args['output'], os.path.split(args['input'])[-1])

  # ---------------------------------------- parse bib-file ----------------------------------------

  # read
  # ----

  bib = bibtexparser.load(open(args['input'],'r'), parser=bibtexparser.bparser.BibTexParser())

  # fix entries
  # -----------

  for entry in bib.entries:

    # fix known Mendeley bugs
    if 'journal' in entry:
      if entry['journal'] == 'EPL (Europhysics Lett.': entry['journal'] = 'EPL (Europhys. Lett.)'
      if entry['journal'] == 'Science (80-. ).'      : entry['journal'] = 'Science'

    # find doi
    if 'doi' not in entry:
      doi = getDoi(*[val for key,val in entry.items() if key not in ['arxivid', 'eprint']])
      if doi:
        entry['doi'] = doi
        if args['verbose_doi']: print(entry['ID'])

    # find arXiv-id
    if 'arxivid' not in entry:
      arxivid = getArxiv(*[val for key,val in entry.items() if key not in ['doi']])
      if arxivid:
        entry['arxivid'] = arxivid
        if args['verbose_arxivid']: print(entry['ID'])

    # get author separations
    sep = args['author_sep']

    # fix author abbreviations
    for key in ['author','editor']:
      if key in entry:
        entry[key] = ' and '.join([reformatAuthor(i,sep) for i in entry[key].split(' and ')])

    # remove title
    if args['no_title']:
      entry.pop('title',None)

    # protect math-mode
    if not args['ignore_math']:
      for key in ['title']:
        if key in entry:
          entry[key] = protectMath(entry[key])

    # convert unicode to LaTeX
    if not args['ignore_unicode']:
      for key in ['author','editor','title']:
        if key in entry:
          entry[key] = replaceUnicode(entry[key])

    # abbreviations: change symbol after "."
    for key in ['journal','author']:
      if key in entry:
        entry[key] = entry[key].replace('. ','.{dot_space:s} '.format(**args))

    # fix underscore problems
    # -
    if 'doi' in entry:
      entry['doi'] = entry['doi'].replace('_','\_')
      entry['doi'] = entry['doi'].replace('{\\\\_}','\_')
      entry['doi'] = entry['doi'].replace('{\\_}','\_')
      entry['doi'] = entry['doi'].replace('{\_}','\_')
    # -
    if 'url' in entry:
      entry['url'] = entry['url'].replace('{\_}','\_')
      entry['url'] = entry['url'].replace('{\\_}','\_')
      entry['url'] = entry['url'].replace('{~}','~')
      entry['url'] = entry['url'].replace(r'\&','&')
    # -
    if 'url' in entry:
      entry['url'] = subr(re.compile(r'({)([^}])(})',re.UNICODE), r'\2', entry['url'])

  # select entries
  # --------------

  for entry in bib.entries:

    # get entry type
    e = entry['ENTRYTYPE']

    # basic fields (common for all)
    fields = ['ID','ENTRYTYPE','author','title','year','doi','arxivid']

    # set fields to select (if present)
    if   e=='article'      : fields += ['journal','volume','number','pages']
    elif e=='unpublished'  : fields += []
    elif e=='inproceedings': fields += ['booktitle','editor','publisher','volume','number','pages']
    elif e=='book'         : fields += ['edition','editor','publisher','isbn']
    elif e=='inbook'       : fields += ['edition','editor','publisher','isbn']
    elif e=='incollection' : fields += ['booktitle','edition','publisher','isbn']
    elif e=='phdthesis'    : fields += ['school','isbn','url']
    elif e=='techreport'   : fields += ['institution','isbn','url']
    elif e=='misc'         : fields += ['pages','url']
    else: Error('Undefined entry '+entry)

    # ensure at least one digital reference
    if 'url' not in fields:
      if 'doi' not in entry and 'arxivid' not in entry:
        fields.append('url')

    # remove all fields that are not specified above
    rm = [key for key in entry if key not in fields]
    for key in rm:
      del entry[key]

    # remove link if doi or arxivid is available
    if 'url' in entry and ('doi' in entry or 'arxivid' in entry):
      del entry['url']

  # store
  # -----

  open(args['output'],'w').write(bibtexparser.dumps(bib))
