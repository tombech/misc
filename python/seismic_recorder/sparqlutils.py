""" Some useful utility methids for doing SPARQL queries """

import sys, httplib, urlparse, urllib2, traceback, urllib
import math, datetime, requests, json, csv
import types 
import sparqlutils


REPLS = [('"', '\\"'), ('\n', '\\n'), ('\r', '\\r'), ('\t', '\\t'),
         ('\\', '\\\\')]


# from <http://code.activestate.com/recipes/303668/>
def _xmlcharref_encode(unicode_data, encoding="ascii"):
        """Emulate Python 2.3's 'xmlcharrefreplace' encoding error handler."""
        res = ""

        # Step through the unicode_data string one character at a time in
        # order to catch unencodable characters:
        for char in unicode_data:
                try:
                        char.encode(encoding, 'strict')
                except UnicodeError:
                        if ord(char) <= 0xFFFF:
                                res += '\\u%04X' % ord(char)
                        else:
                                res += '\\U%08X' % ord(char)
                else:
                        res += char

        return res


def escape_literal(literal):
        literal = literal.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"').replace('\r', '\\r').replace('\v', '')
        literal = _xmlcharref_encode(literal, "ascii")
        return literal


def loadfile(filename, _header=False, _delimiter=";"):
        inf = open(filename,"rU")
        rows = [row for row in csv.reader(inf, delimiter = _delimiter)]
        i = 0
        if _header:
            header = [s for s in rows[0]]
            i = 1
        else:
            header = []


        data = []
        
        for row in rows[i:]:
            if len(row) == 0:
                import pdb;pdb.set_trace()
                continue

            datarow = {}
                
            i = 0
            for col in row:
                if _header:
                    key = header[i]
                else:
                    key = str(i)
                datarow[key] = col
                i = i + 1
            
            data.append(datarow)

        inf.close()
        
        return header, data


def getTriplesFromSparqlResultset(resultset, subjectvar='s', predicatevar='p', valuevar='v'):
    for record in resultset['results']['bindings']:
        subject = record.get(subjectvar,{'value':""})['value']
        predicate = record.get(predicatevar,{'value':""})['value']
        value = record.get(valuevar,{'value':""})['value']

        yield (subject, predicate, value)


def drop_graph(endpoint, graph, logger=None):
    query = """drop silent graph <%s>""" % graph    
    postquery(endpoint, query, logger)


def clear(endpoint, graph, logger=None):
    postquery(endpoint, "clear graph <%s>" % graph, logger)


def insert_string(endpoint, graph, triples_string, batch_size=1000, logger=None):
    triples = [line.strip() for line in triples_string.split('\n') if line]  
    insert(endpoint, graph, triples, batch_size=batch_size, logger=logger)

def insert(endpoint, graph, triples, batch_size=1000, logger=None):
    batch = []
    for line in triples:
        batch.append(line)
        if len(batch) == batch_size:
            print "Inserting batch of %s triples..." % len(batch)
            insert_string(endpoint, graph, "\n".join(batch), logger)
            batch = []

    if batch:
        print "Inserting batch of %s triples..." % len(batch)
        insert_string(endpoint, graph, "\n".join(batch), logger)


def insert_csv_file(endpoint, graph, filename, id_col = 0, subject_prefix="http://data.sesam.io/test", predicate_prefix="http://data.sesam.io/test/schema/", header=False, delimiter=";"):
    """Inserts the contents of the csv file into the given graph (clears it first)"""
    clear(endpoint, graph)
    
    header_row, data = loadfile(filename, _delimiter=delimiter, _header=header)
    
    triples = []
    for row in data:
        psi = subject_prefix + "/" + row.get(str(id_col))
        for key in row.keys():
            value = row[key]
        
            s = '<%s> <%s%s> "%s".' % (psi, predicate_prefix, key, escape_literal(value))
            triples.append(s)
    
    triples.append('<%s> <http://www.sdshare.org/2012/extension/lastmodified> "%s"^^<http://www.w3.org/2001/XMLSchema#dateTime>.' % (graph, datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')))   
    insert(endpoint, graph, triples)


def insert_string(endpoint, graph, ntriples, logger=None):
    query = "insert data into <%s> { %s }" % (graph, ntriples)
    postquery(endpoint, query, logger)


def postquery(endpoint, query, doprint=False, logger=None):   
    if type(query) == unicode:
        query = query.encode('utf-8')
    
    body = "query=" + urllib2.quote(query)

    parsedurl = urlparse.urlparse(endpoint)

    conn = httplib.HTTPConnection(parsedurl.netloc)
    headers = {"Content-type" : "application/x-www-form-urlencoded; charset=utf-8"}
    conn.request("POST", parsedurl.path, body, headers)

    resp = conn.getresponse()
    if logger and doprint:
        logger.info("%s, %s, (%s lines)" % (resp.status, resp.reason, count))
    if resp.status != 200:
        if logger:
            logger.error(resp.read())
        print "***** Failed to execute query! Response was: " + resp.read()        
        sys.exit(1)

    return resp.read()


def sparqlQueryJSON(endpoint, query, format="application/json"):
    params={
        "default-graph": "",
        "query": query,
        "debug": "on",
        "timeout": "",
        "format": format,
        "save": "display",
        "fname": ""
    }
    querypart=urllib.urlencode(params)
   
    req = requests.get(endpoint + "?" + querypart)
    if req.status_code != 200:
        req.raise_for_status()

    return json.loads(req.text)


###################################
## Methods using the sparql library
###################################


def query_for_value(endpoint, query, prefixes = ''):
    row = sparql.query(endpoint, prefixes + query).fetchone()
    try:
        (a, ) = row
        return a[0].value
    except ValueError: # means we got no results
        return None


def query_for_list(endpoint, query, prefixes = ''):
    return [row[0].value for row in sparql.query(endpoint, prefixes + query)]


def value(val):
    if val:
        return val.value
    else:
        return None


def query_for_rows(endpoint, query, prefixes = ''):
    return [[value(val) for val in row]
            for row in sparql.query(endpoint, prefixes + query)]


def escape(str):
    for (ch, repl) in REPLS:
        str = str.replace(ch, repl)
    return str


def trans(val):
    if type(val) not in types.StringTypes:
        return '"' + str(val) + '"'
    elif ((val.startswith('http://') or val.startswith('https://')) and
          ' ' not in val):
        return '<' + val.strip() + '>'
    else:
        return '"' + escape(val.strip()) + '"'


def acceptable_type(val):
    return type(val) in (bool, str, unicode, int, long, float)


def write_rdf(endpoint, url, props, graph):
    upd = 'insert into graph <%s> { %s %s . }'
    props = ['<%s> %s' % (prop, trans(val)) for (prop, val) in props
             if acceptable_type(val)]
    upd = upd % (graph, '<' + url + '>', "; ".join(props))
    postquery(endpoin, upd)
