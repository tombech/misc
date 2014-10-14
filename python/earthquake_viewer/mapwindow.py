import time
from PyQt4 import QtGui, QtCore
from dateutil.parser import parse
from datetime import datetime
import math
import utils
import pytz


class MapWindow(QtGui.QWidget):
    
    def __init__(self):
        super(MapWindow, self).__init__()
        self.label = QtGui.QLabel(self)
        
        self.layout = QtGui.QHBoxLayout(self)
        self.layout.addWidget(self.label)

        self.pixmap = QtGui.QPixmap("map2.png")
        self.label.setPixmap(self.pixmap)
        
        self.initUI()
        
    def plotEQs(self, eqs):
        self.pixmap = QtGui.QPixmap("map2.png")
        #print self.pixmap.width(), self.pixmap.height()
        painter = QtGui.QPainter(self)
        painter.begin(self.pixmap)
        
        #now = datetime.utcnow()
        now = pytz.utc.localize(datetime.utcnow())
        
        local_eqs = eqs[:]
        local_eqs.reverse()
        
        for eq in local_eqs:
            x, y = utils.convertGeoToPixel(eq['lat'],eq['lon'], self.pixmap.width(), self.pixmap.height())

            if x < 0 or y < 0:
                continue
            
            center = QtCore.QPoint(x, y)

            size = eq['s']
            
            if size > 5:
                radius = 40
            elif size > 4:
                radius = 30
            elif size > 3:
                radius = 20
            elif size > 2:
                radius = 10
            else:
                radius = 5

            parsed_date = parse(eq["t"])
            age = now-parsed_date
            
            if age.seconds < 60*60*1:
                painter.setPen(QtGui.QColor('green'))
                painter.setBrush(QtGui.QColor('green'))
            elif age.seconds < 60*60*8:
                painter.setPen(QtGui.QColor('red'))
                painter.setBrush(QtGui.QColor('red'))
            elif age.seconds < 60*60*16:
                painter.setPen(QtGui.QColor('orange'))
                painter.setBrush(QtGui.QColor('orange'))
            elif age.seconds < 60*60*24:
                painter.setPen(QtGui.QColor('yellow'))
                painter.setBrush(QtGui.QColor('yellow'))
            else:
                painter.setPen(QtGui.QColor('blue'))
                painter.setBrush(QtGui.QColor('blue'))

            painter.drawEllipse(center, radius, radius)
        
        painter.end()
        self.label.setPixmap(self.pixmap)
        
    def initUI(self):      
        self.setWindowTitle('Map')
        self.show()
