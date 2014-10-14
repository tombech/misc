import requests
import time
import sys
from datetime import datetime
from dateutil.parser import parse
import pytz
import json
import md5
import humanize
import utils
import sparqlutils

# RDF structure for a eq:
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://psi.vedur.is/seismic/schema/Earthquake>.
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://www.w3.org/2000/01/rdf-schema#label> "Sunday 12.10.2014, 14:56:58, 64.669, -17.420, 1.1 km, 1.5, 90.06, 6.0 km ENE of Kistufell".
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://psi.vedur.is/seismic/schema/depth> "7.5"^^<http://www.w3.org/2001/XMLSchema#float>.
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://psi.vedur.is/seismic/schema/depth> "7.5"^^<http://www.w3.org/2001/XMLSchema#float>.
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://psi.vedur.is/seismic/schema/magnitude> "1.5"^^<http://www.w3.org/2001/XMLSchema#float>.
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://psi.vedur.is/seismic/schema/time> "2014-09-23T06:20:43"^^<http://www.w3.org/2001/XMLSchema#dateTime>.
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://psi.vedur.is/seismic/schema/place> "Kistufell".
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://psi.vedur.is/seismic/schema/direction> "N".
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://psi.vedur.is/seismic/schema/distance> "4.5"^^<http://www.w3.org/2001/XMLSchema#float>.
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://psi.vedur.is/seismic/schema/quality> "99.0"^^<http://www.w3.org/2001/XMLSchema#float>.
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://www.w3.org/2003/01/geo/wgs84_pos#lat> "64.681"^^<http://www.w3.org/2001/XMLSchema#float>.
# <http://psi.vedur.is/seismic/eq/d88c9ea734d17e5c9c70a4b7051be4ba> <http://www.w3.org/2003/01/geo/wgs84_pos#long> "-17.534"^^<http://www.w3.org/2001/XMLSchema#float>.
# <http://psi.vedur.is/seismic/eq/%s> <http://purl.org/dc/elements/1.1/rights> "Icelandic Met Office (IMO)".'
# <http://psi.vedur.is/seismic/eq/%s> <http://purl.org/dc/elements/1.1/source> "http://en.vedur.is/earthquakes-and-volcanism/earthquakes".'

sorted_eqs = []
eqs = {}

# Dump quake info to JSON files
def saveQuakes():
    global sorted_eqs
    global eqs

    now = utils.getISODateAsString()
    # Save to disk
    s = json.dumps(eqs)
    f = open("data/quakes-%s.json" % now, "w")
    f.write(s)
    f.close()
    s = json.dumps(sorted_eqs)
    f = open("data/quakes_sorted-%s.json" % now, "w")
    f.write(s)
    f.close()
    
    for key in eqs.keys():
        eq = eqs[key]
        
        triples = []

        label = "%15s %7s:%7s %5s %5s %6s   %s" % (eq["t"],
                        eq["lat"], eq["lon"], eq["dep"], eq["s"], eq["q"],
                        str(eq["dL"]) + " km " + eq["dD"] + " of " + eq["dR"])
        
        print "Inserting quake in triplestore:", label

        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://psi.vedur.is/seismic/schema/Earthquake>.' % key)
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://www.w3.org/2000/01/rdf-schema#label> "%s".' % (key, sparqlutils.escape_literal(label)))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://psi.vedur.is/seismic/schema/depth> "%s"^^<http://www.w3.org/2001/XMLSchema#float>.' % (key, eq["dep"]))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://psi.vedur.is/seismic/schema/magnitude> "%s"^^<http://www.w3.org/2001/XMLSchema#float>.' % (key, eq["s"]))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://psi.vedur.is/seismic/schema/time> "%sZ"^^<http://www.w3.org/2001/XMLSchema#dateTime>.' % (key, eq["t"]))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://psi.vedur.is/seismic/schema/place> "%s".' % (key, eq["dR"]))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://psi.vedur.is/seismic/schema/direction> "%s".' % (key, eq["dD"]))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://psi.vedur.is/seismic/schema/distance> "%s"^^<http://www.w3.org/2001/XMLSchema#float>.' % (key, eq["dL"]))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://psi.vedur.is/seismic/schema/quality> "%s"^^<http://www.w3.org/2001/XMLSchema#float>.' % (key, eq["q"]))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://www.w3.org/2003/01/geo/wgs84_pos#lat> "%s"^^<http://www.w3.org/2001/XMLSchema#float>.' % (key, eq["lat"]))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://www.w3.org/2003/01/geo/wgs84_pos#long> "%s"^^<http://www.w3.org/2001/XMLSchema#float>.' % (key, eq["lon"]))
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://purl.org/dc/elements/1.1/rights> "Icelandic Met Office (IMO)".' % key)
        triples.append('<http://psi.vedur.is/seismic/eq/%s> <http://purl.org/dc/elements/1.1/source> "http://en.vedur.is/earthquakes-and-volcanism/earthquakes".' % key)

        # Delete stuff first
        query = "WITH <http://data.tombech.org/iceland/imo/seismic> DELETE { <http://psi.vedur.is/seismic/eq/%s> ?p ?o } WHERE { <http://psi.vedur.is/seismic/eq/%s> ?p ?o }" % (key, key)
        
        sparqlutils.postquery("http://tombech.org:8890/sparql", query)
        
        sparqlutils.insert("http://tombech.org:8890/sparql", "http://data.tombech.org/iceland/imo/seismic", triples)


def downloadIMOQuakes():
    global sorted_eqs
    global eqs
    
    def getKey(item):
        return item['t']

    print "Downloading IMO quakes..."
    
    r = requests.get("http://en.vedur.is/earthquakes-and-volcanism/earthquakes#view=table")
    if r.status_code == 200:
        page = r.text
        
        # Find embedded javascript and munge it to Python form
        token = "VI.quakeInfo = "
        i = page.find(token) + len(token)
        
        page = page[i:]
        i = page.find("}];")
        
        data = page[:i+2]
        
        data = data.replace("new Date", "datetime")
        data = data.replace("-1,",",")
        data = data.replace(":'",":u'")
        
        # Now it should be evaluable Python!
        data = eval(data)
        
        # Look for new quakes
        unseen = []            
        for eq in data:
            # Dunno what this one is, but it keeps changing for each request
            del eq['a']
            
            # Convert some strings
            eq["t"] = eq["t"].isoformat()
            eq["lat"] = float(eq["lat"])
            eq["lon"] = float(eq["lon"])
            eq["s"] = float(eq["s"])
            eq["dep"] = float(eq["dep"])
            eq["dL"] = float(eq["dL"])
            
            # Compute hashes to avoid duplicates
            m = md5.new()
            for key in eq.keys():
                value = eq[key]
                if type(value) == type(u''):
                    try:
                        value = value.encode("utf-8")
                    except:
                        pass
                else:
                    value = str(value)
                m.update(value)

            hash = m.hexdigest()
            if hash not in eqs:
                eqs[hash] = eq
                unseen.append(eq)

        # Any new ones?
        if unseen:
            print "Found %s new quakes! Saving new dump..." % len(unseen)
            sorted_eqs = unseen + sorted_eqs
            saveQuakes()
            
            now = datetime.utcnow()
            #now = pytz.utc.localize(datetime.utcnow())

            # Sort stuff on date
            sorted_eqs = sorted(sorted_eqs, key=getKey)
            sorted_eqs.reverse()


while True:
    downloadIMOQuakes()
    time.sleep(5*60)
