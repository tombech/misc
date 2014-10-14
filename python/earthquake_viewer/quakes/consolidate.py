import glob
import json
import md5
import sparqlutils

def getHash(eq):
    m = md5.new()
    for key in eq.keys():
        value = eq[key]
        if type(value) == type(u''):
            try:
                value = value.encode("utf-8")
            except:
                import pdb;pdb.set_trace()
        else:
            value = str(value)
        m.update(value)

    return m.hexdigest()    

def sortQuakes(a, b):
    return a.get('q',0.0) > b.get('q',0.0)

all_quakes = []

for filename in glob.glob('quakes_sorted*.json'):
    f = open(filename)
    data = f.read()
    quakes = json.loads(data)
    all_quakes.extend(quakes)
    f.close()

quakes_per_datestamp = {}

# Order quakes by timestamp

for quake in all_quakes:
    timestamp = quake['t']
    if not timestamp in quakes_per_datestamp:
        quakes_per_datestamp[timestamp] = {}

    # Within a timestamp, only record unique values        
    hashvalue = getHash(quake)
    if not hashvalue in quakes_per_datestamp[timestamp]:
        quakes_per_datestamp[timestamp][hashvalue] = quake

timestamps = quakes_per_datestamp.keys()[:]
timestamps.sort()

i = 0

for timestamp in timestamps:
    if len(quakes_per_datestamp[timestamp].keys()) > 1:
        # If any %99s then skip the rest, sort on size and keep biggest
        
#        print "Found %s quakes with same timestamp: %s" % (len(quakes_per_datestamp[timestamp].keys()), timestamp)
#        for key in quakes_per_datestamp[timestamp].keys():
#            print quakes_per_datestamp[timestamp][key]
#        print
        
        verified = [key for key in quakes_per_datestamp[timestamp].keys() if quakes_per_datestamp[timestamp][key]['q'] == u'99.0']

        # If no verified, keep all_quakes
        if not verified:
            i = i + len(quakes_per_datestamp[timestamp].keys())
            continue
        
        verified_quakes = [quakes_per_datestamp[timestamp][key] for key in verified]
        verified_quakes.sort(sortQuakes)
        key = verified[0]
        quakes_per_datestamp[timestamp] = {key : verified_quakes[0]}
        i = i + 1

# Save the whole shebang
print "Saving %s quakes..." % i

s = json.dumps(quakes_per_datestamp)
f = open("all_quakes_sorted_timestamp.json", "w")
f.write(s)
f.close()

# Upload it all to virtuoso

for timestamp in quakes_per_datestamp.keys():
    for key in quakes_per_datestamp[timestamp].keys():
        eq = quakes_per_datestamp[timestamp][key]
        
        triples = []

        label = "%15s %7s:%7s %5s %5s %6s   %s" % (eq["t"],
                        eq["lat"], eq["lon"], eq["dep"], eq["s"], eq["q"],
                        str(eq["dL"]) + " km " + eq["dD"] + " of " + eq["dR"])
        
        print "Inserting quake:", label

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
        