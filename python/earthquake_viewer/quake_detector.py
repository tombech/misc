import requests
import time
import tempfile
from PIL import Image, ImageQt, ImageEnhance
import sys
from PyQt4 import QtGui, QtCore
from datetime import datetime, timedelta
from dateutil.parser import parse
import pytz
import json
import md5
import humanize
import pygame
import math
import utils
import mapwindow
import sparql
import sparqlutils


drumplot_url = "http://hraun.vedur.is/ja/drumplot/dyn.png" 
ex = None
map_window = None


class MyWindow(QtGui.QWidget):
    
    def __init__(self):
        super(MyWindow, self).__init__()
        self.label = QtGui.QLabel(self)
        self.list_widget = QtGui.QListWidget(self)
        
        font = QtGui.QFont()
        font.setFamily("Monospace")

        self.list_widget.setFont(font)        
        self.list_widget.setMinimumWidth(600)
        self.layout = QtGui.QHBoxLayout(self)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.list_widget)
        self.previous_date = datetime.utcnow()
       
        self.image = None
        self.pixmap = None

        self.eqs = {}
        self.sorted_eqs = []
        
        self.initUI()
        
        self.imagetimer = QtCore.QTimer()
        self.quaketimer = QtCore.QTimer()
        
        QtCore.QObject.connect(self.imagetimer, QtCore.SIGNAL("timeout()"), self.updateDrumPlot)
        QtCore.QObject.connect(self.quaketimer, QtCore.SIGNAL("timeout()"), self.downloadIMOQuakes)

        self.updateDrumPlot()
        self.downloadIMOQuakes()
  
        # Update drumplot every 5 minutes and IMO data every 1 minutes
        self.imagetimer.start(5*60*1000)
        self.quaketimer.start(60*1000)
        
        QtCore.pyqtRemoveInputHook()

    # Get quakes the last three days
    def downloadIMOQuakes(self):
        def getKey(item):
            return item['t']

        print "Downloading quakes..."

        query = """
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX imo: <http://psi.vedur.is/seismic/schema/>

select ?lat ?long ?depth ?magnitude ?quality ?time ?place ?direction ?distance
where {
  {
    ?s a imo:Earthquake.
    ?s geo:lat ?lat.
    ?s geo:long ?long.
    ?s imo:depth ?depth.
    ?s imo:magnitude ?magnitude.
    ?s imo:quality ?quality.
    ?s imo:time ?time.
    ?s imo:place ?place.
    ?s imo:direction ?direction.
    ?s imo:distance ?distance
  }
  FILTER(?time > "%s"^^xsd:dateTime)
} order by DESC(?time)
""" % (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")

        result = sparqlutils.query_for_rows("http://tombech.org:8890/sparql", query)

        if result:
            data = []           
            for row in result:
                
                data.append({
                      'lat':row[0], 'lon':row[1],
                      'dep':row[2], 's':row[3],
                      'q':row[4], 't':row[5],
                      'dR':row[6], 'dD':row[7],
                      'dL':row[8]
                    }
                )
                
                #import pdb;pdb.set_trace()
            
            # Look for new quakes
            unseen = []            
            for eq in data:
                # Convert some strings
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
                if hash not in self.eqs:
                    self.eqs[hash] = eq
                    unseen.append(eq)

            # Any new ones?
            if unseen:
                print "Found %s new quakes!" % len(unseen)
                
                # Notification for new large eqs
                for eq in unseen:
                    size = eq["s"]
                    if size >= 4.0:
                        pygame.mixer.music.play()
                        print "A size M4+ found!"
                    elif size >= 3.0:
                        print "A size M3+ found!"
                        pygame.mixer.music.play()
                
                self.sorted_eqs = unseen + self.sorted_eqs
                
                #now = datetime.utcnow()
                now = pytz.utc.localize(datetime.utcnow())

                # Sort stuff on date
                self.sorted_eqs = sorted(self.sorted_eqs, key=getKey)
                self.sorted_eqs.reverse()
                
                # Refresh entire list widget in any case so timing gets refreshed
                self.list_widget.clear()                
                for eq in self.sorted_eqs:
                    parsed_date = parse(eq["t"])
                    
                    s = "%15s %7s:%7s %5s %5s %6s   %s" % (humanize.naturaltime(now-parsed_date),
                        eq["lat"], eq["lon"], eq["dep"], eq["s"], eq["q"],
                        str(eq["dL"]) + " km " + eq["dD"] + " of " + eq["dR"])

                    item = QtGui.QListWidgetItem(self.list_widget)
                    item.setText(s)
                    
                    size = eq["s"]
                    if size >= 4.0:
                        item.setBackground(QtGui.QColor('red'))
                    elif size >= 3.0:
                        item.setBackground(QtGui.QColor('orange'))
                    elif size >= 2.0:
                        item.setBackground(QtGui.QColor('yellow'))
                    
                    self.list_widget.insertItem(-1,item)

                if map_window:
                    print "Updating map!"
                    map_window.plotEQs(self.sorted_eqs)

    # Download a new drumplot and check for new quakes
    def updateDrumPlot(self):
        print "Downloading image..."

        r = requests.get(drumplot_url, stream=True)
        if r.status_code == 200:
            fn = utils.getFreeFilename("outfile.png")
            
            with open("outfile.png", 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)

        self.previous_date = datetime.utcnow()       
        self.pixmap = QtGui.QPixmap("outfile.png")
        self.label.setPixmap(self.pixmap)

    def initUI(self):      
        self.setWindowTitle('Bardabunga')
        self.show()

def main():
    global map_window
    global ex
    
    pygame.init()
    pygame.mixer.music.load("thunder2.ogg")
    
    app = QtGui.QApplication(sys.argv)
    map_window = mapwindow.MapWindow()
    ex = MyWindow()

    map_window.plotEQs(ex.sorted_eqs)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
