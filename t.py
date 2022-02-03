import crossref_commons.retrieval
# print(crossref_commons.retrieval.get_publication_as_json('10.5621/sciefictstud.40.2.0382'))
# print(crossref_commons.retrieval.get_publication_as_json('10.1103/PhysRevLett.121.234302'))


from habanero import Crossref
cr = Crossref()
x = cr.works(ids = '10.1103/PhysRevLett.121.234302')
print(x["message"]["author"])
