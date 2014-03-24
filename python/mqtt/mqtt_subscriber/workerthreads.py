from threading import Thread, Event
import sparqlutils, datetime
from urlgrabber.grabber import URLGrabber
from datetime import datetime

url_grabber = URLGrabber()

class WorkerThread(Thread):
    def __init__(self, queue, endpoint, graph):
        Thread.__init__(self)
        self.queue = queue
        self.endpoint = endpoint
        self.graph = graph
        self._stopevent = Event()
        # Sleep a bit between queue runs
        self._sleep_period = 1.0

    def run(self):
        print "Starting worker thread.."
        while not self._stopevent.isSet():
            while not self.queue.empty():
                self.process()
            # Wait a few secs
            self._stopevent.wait(self._sleep_period)

    def join(self,timeout=None):
        print "Stopping worker thread.."
        self._stopevent.set()
        Thread.join(self, timeout)

class FragmentWorker(WorkerThread):

    def process(self):
        triples = self.queue.get().split("\n")
        triples.append("<%s> <http://www.sdshare.org/2012/extension/lastmodified> '%s'^^xsd:dateTime" % (self.graph, datetime.now()))
        print "FragmentWorker thread: inserting %s triples into graph <%s> using endpoint '%s'" % (len(triples), self.graph, self.endpoint)
        sparqlutils.insert(self.endpoint, self.graph, triples)
        self.queue.task_done()

class SnapshotWorker(WorkerThread):

    def process(self):
        snapshot_url = self.queue.get()
        filename = url_grabber.urlgrab(snapshot_url)

        # Clear the graph first
        sparqlutils.clear(self.endpoint, self.graph)

        i = 0
        triples = []
        for line in open(filename, "r"):
            lines.append(line)
            if i == 10000:
                # Batch per 10k triples
                sparqlutils.insert(self.endpoint, self.graph, triples)
                i = 0
                lines = []

        # Add the last updated line in the graph
        triples.append("<%s> <http://www.sdshare.org/2012/extension/lastmodified> '%s'^^xsd:dateTime" % (graph, datetime.now()))

        # Insert the remainder
        sparqlutils.insert(self.endpoint, self.graph, triples)

        # Done
        self.queue.task_done()
