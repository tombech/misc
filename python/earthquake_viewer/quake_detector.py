import requests
import time
import tempfile
from PIL import Image, ImageQt, ImageEnhance
import sys
from PyQt4 import QtGui, QtCore
from datetime import datetime
from dateutil.parser import parse
import pytz
import json
import md5
import humanize
import pygame
import quake_counter
import math
import utils
import mapwindow


url = "http://hraun.vedur.is/ja/drumplot/dyn.png"

ex = None
map_window = None
qc = None


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
        #self.downloadQuakes()
        self.downloadIMOQuakes()
  
        # Update drumplot every 5 minutes and IMO data every 1 minutes
        self.imagetimer.start(5*60*1000)
        self.quaketimer.start(60*1000)
        
        QtCore.pyqtRemoveInputHook()

    # Screen scrape quake info from IMO site (from embedded static javascript)
    def downloadIMOQuakes(self):
        def getKey(item):
            return item['t']

        print "Downloading IMO quakes..."


        
        r = requests.get("http://en.vedur.is/earthquakes-and-volcanism/earthquakes/vatnajokull/#view=table")
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
                if hash not in self.eqs:
                    self.eqs[hash] = eq
                    unseen.append(eq)

            # Any new ones?
            if unseen:
                print "Found %s new quakes! Saving new dump..." % len(unseen)
                
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
                self.saveQuakes()
                
                now = datetime.utcnow()
                #now = pytz.utc.localize(datetime.utcnow())

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

    # Download quake data from public API (json)
    def downloadQuakes(self):
        print "Downloading quakes from public API..."

        r = requests.get("http://apis.is/earthquake/is")
        if r.status_code == 200:
            data = r.text
            
            unseen = []
            if data:
                eqs = json.loads(data)
                for eq in eqs["results"]:
                    # Compute hash of quake info to skip duplicates
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
                print "Found %s new quakes! Saving new dump..." % len(unseen)
                self.sorted_eqs = unseen + self.sorted_eqs
                self.saveQuakes()
                
            # Refresh entire list widget in any case so timing gets refreshed
            now = pytz.utc.localize(datetime.utcnow())
            self.list_widget.clear()                
            for eq in self.sorted_eqs:
                parsed_date = parse(eq["timestamp"])
                
                s = "%15s %7s:%7s %5s %5s %6s   %s" % (humanize.naturaltime(now-parsed_date),
                    eq["latitude"], eq["longitude"], eq["depth"], eq["size"],
                    eq["quality"], eq["humanReadableLocation"])

                item = QtGui.QListWidgetItem(self.list_widget)
                item.setText(s)
                
                # Mark major magnitudes with colours
                size = eq["size"]
                if size >= 3.0:
                    item.setBackground(QtGui.QColor('red'))
                elif size >= 2.0:
                    item.setBackground(QtGui.QColor('yellow'))
                
                self.list_widget.insertItem(-1,item)


    # Download a new drumplot and check for new quakes
    def updateDrumPlot(self):
        # Restart after midnight
        if utils.isNewDay(self.previous_date):
            print "Past midnight, reseting history!"
            qc.resetCount()           

        # No point in checking between 00:00 and 04:00 as the plot is full of noise
        if datetime.utcnow().hour in range(0, 4):
            print "Warming up, skipping plot check!"
            return

        filename, new_count = qc.countQuakes(url, debug=False)
        
        if new_count:
            print "*** Significant earthquake detected! ***"
            pygame.mixer.music.play()
            utils.sendMailWithAttachment("tom.bech@gmail.com",
                                         "tom.bech@gmail.com",
                                         "Found a new earthquake!",
                                         "Found a new earthquake!",
                                         filename)

        self.previous_date = datetime.utcnow()       
        self.pixmap = QtGui.QPixmap(filename)
        self.label.setPixmap(self.pixmap)
        
    def initUI(self):      
        self.setWindowTitle('Bardabunga')
        self.show()

def main():
    global qc
    global map_window
    global ex
    
    qc = quake_counter.QuakeCounter()

    pygame.init()
    pygame.mixer.music.load("thunder2.ogg")
    
    app = QtGui.QApplication(sys.argv)
    map_window = mapwindow.MapWindow()
    ex = MyWindow()

    map_window.plotEQs(ex.sorted_eqs)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
