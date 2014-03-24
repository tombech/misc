# Some useful methods for doing SPARQL queries

import sys, httplib, urlparse, urllib2, traceback, urlgrabber
import urllib, json
import math, datetime

# HTTP URL is constructed accordingly with JSON query results format in mind.
def sparqlQuery(query, baseURL, format="application/json", logger=None):
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
    
    #response = urllib.urlopen(baseURL,querypart).read()
    #return json.loads(response)
    
    response = urlgrabber.urlread(baseURL + "?" + querypart)
    return json.loads(response)

def clear(endpoint, graph, logger=None):
    runquery(endpoint, "clear graph <%s>" % graph, logger)

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

def insert_string(endpoint, graph, ntriples, logger=None):
    query = "insert data into <%s> { %s }" % (graph, ntriples)
    runquery(endpoint, query, logger)

def runquery(endpoint, query, doprint=False, logger=None):
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
        sys.exit(1)
    return resp.read()
