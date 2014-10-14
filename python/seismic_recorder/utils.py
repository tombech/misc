import os
import glob
import time
import shutil
import fileinput
import errno
import yaml
from datetime import datetime
import math
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart


start = (63.902265, -19.436268)
end = (65.332819, -14.365851)


def convertGeoToPixel(lat, lon, mapWidth, mapHeight):
    if lat < start[0] or lat > end[0]:
        return -1,-1
    
    if lon < start[1] or lon > end[1]:
        return -1,-1

    mapLonLeft = start[1]
    mapLonRight = end[1]
    mapLonDelta = mapLonRight - mapLonLeft

    mapLatBottom = start[0]
    mapLatBottomDegree = mapLatBottom * math.pi / 180.0

    x = (lon - mapLonLeft) * (mapWidth / mapLonDelta)

    lat = lat * math.pi / 180.0
    worldMapWidth = ((mapWidth / mapLonDelta) * 360.0) / (2.0 * math.pi)
    mapOffsetY = (worldMapWidth / 2.0 * math.log((1.0 + math.sin(mapLatBottomDegree)) / (1.0 - math.sin(mapLatBottomDegree))))
    y = mapHeight - ((worldMapWidth / 2.0 * math.log((1.0 + math.sin(lat)) / (1.0 - math.sin(lat)))) - mapOffsetY)

#    import pdb;pdb.set_trace()

    return x, y

def rad2deg(radians):
    degrees = 180.0 * radians / math.pi
    return degrees

def deg2rad(degrees):
    radians = math.pi * degrees / 180.0
    return radians

# Formula for mercator projection y coordinate:
def mercY(lat):
    return math.log(math.tan(lat/2.0 + math.pi/4.0))


# both in radians, use deg2rad if neccessary
def mapProject(lat, lon, width, height):
    if lat < deg2rad(start[0]) or lat > deg2rad(end[0]):
        return -1,-1
    
    if lon < deg2rad(start[1]) or lon > deg2rad(end[1]):
        return -1,-1

    south = deg2rad(start[0])
    north = deg2rad(end[0])
    west = deg2rad(start[1])
    east = deg2rad(end[1])
    
    ymin = mercY(south)
    ymax = mercY(north)
    xFactor = width/(east - west)
    yFactor = height/(ymax - ymin)
    
    x = lon
    y = mercY(lat)
    x = (x - west) * xFactor
    y = (ymax - y) * yFactor # y points south

    return x, y

# Naive
def getMapCoord(lat, lon, width, height):   
    if lat < start[0] or lat > end[0]:
        return -1,-1
    
    if lon < start[1] or lon > end[1]:
        return -1,-1
    
    lat_w = end[0]-start[0]
    lon_w = abs(start[1])-abs(end[1])
    
    x = float(width) * ((abs(start[1]) - abs(lon)) / lon_w)
    y = float(height) * ((end[0] - lat) / lat_w)
    
    return x, y

def _read_properties(configfile):
    result = {}
    with open(configfile) as f:
        for line in f.readlines():
            if not '=' in line:
                continue

            name, value = [x for x in line.split("=")]
            result[name.strip()] = value.strip()
        return result


def getISODateAsString(utc=True):
    if utc:
        return datetime.utcnow().strftime("%Y-%m-%d")
    return datetime.now().strftime("%Y-%m-%d")


def loadConfig(configfile):
    """ Loads a YAML or .properties config file, returns a dictionary """
    
    if configfile.endswith(".properties"):
        return _read_properties(configfile)
    elif configfile.endswith(".yaml"):
        with open(configfile) as f:
            return yaml.load(f)
        
    raise Exception("Unknown config format: '%s'" % configfile)


def getFreeFilename(filename):
    if not os.path.isfile(filename):
        return filename

    fn, ext = os.path.splitext(filename)
    i = 0

    f = "%s-%s%s" % (fn, str(i), ext)        
    while os.path.isfile(f):
        i = i + 1
        f = "%s-%s%s" % (fn, str(i), ext)
    
    return f


def _is_sequence(arg):
    return (not hasattr(arg, "strip") and
        hasattr(arg, "__getitem__") or
        hasattr(arg, "__iter__"))


def assertDir(path, rootdir=None):
    """ Make sure the given directory/ies exists in the given or current path """
    
    if _is_sequence(path):
        for p in path:
            assertDir(p, rootdir=rootdir)
    else:
        if not rootdir:
            rootdir = os.path.realpath(os.path.curdir)
    
        # python 2.x is stupid.
        try:
            os.makedirs(rootdir + os.sep + path)
        except OSError as exc: # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(rootdir + os.sep + path):
                pass
            else:
                raise


def copyAndExpandVariables(infilename, outfilename, rootdir=None, **kwargs):
    if not rootdir:
        rootdir = os.path.realpath(os.path.curdir)

    shutil.copyfile(rootdir + os.sep + infilename, rootdir + os.sep + outfilename)

    for arg in kwargs:
        for line in fileinput.input(rootdir + os.sep + outfilename, inplace = 1):
            print line.replace("${%s}" % arg, kwargs[arg]),


def copy(infilename, outfilename, rootdir=None):
    copyAndExpandVariables(infilename, outfilename, rootdir=rootdir)


def removeFiles(pattern, rootdir=None):
    if not rootdir:
        rootdir = os.path.realpath(os.path.curdir)

    for f in glob.glob(rootdir + os.sep + pattern):
        os.remove(f)

# Test for passing midnight
def isNewDay(previous_date):
    now = datetime.utcnow()
        
    return now.year != previous_date.year or \
           now.month != previous_date.month or \
           now.day != previous_date.day

def sendMailWithAttachment(fromaddr, toaddr, subject, body, filename):
    img_data = open(filename, 'rb').read()
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = fromaddr
    msg['To'] = toaddr

    text = MIMEText(body)
    msg.attach(text)
    image = MIMEImage(img_data, name=os.path.basename(filename))
    msg.attach(image)
    
    # Credentials (if needed)
    username = 'tom.bech@gmail.com'
    password = 'iyqhyygdsgbygnxw'

    # The actual mail send
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    server.login(username,password)
    server.sendmail(fromaddr, toaddr, msg.as_string())
    server.quit()
