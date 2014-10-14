from lxml import etree

f = open("2014list.kml")

tree = etree.parse(f)

for element in tree.findall(".//{http://earth.google.com/kml/2.0}Placemark"):
    timestamp = element.find(".//{http://earth.google.com/kml/2.0}when").text
    description = element.find(".//{http://earth.google.com/kml/2.0}description").text
    coordinates = element.find(".//{http://earth.google.com/kml/2.0}coordinates").text
    
    lat,lon,foo = coordinates.split(",")
    
    data = description.split('<br>')
    depth = float(data[2].replace("Depth:","").replace("km","").strip())
    size = float(data[3].replace("Size:","").replace("Ml","").strip())
    
    if size > 4:
        print timestamp, lat,lon,size,depth

f.close()
