import utils
import quake_counter
from datetime import datetime
from time import sleep

previous_date = None
url = "http://hraun.vedur.is/ja/drumplot/dyn.png"

def updateDrumPlot():
    global previous_date
    # Restart after midnight
    if utils.isNewDay(previous_date):
        print "Past midnight, reseting history!"
        qc.resetCount()           

    # No point in checking between 00:00 and 04:00 as the plot is full of noise
    if datetime.utcnow().hour in range(0, 4):
        print "Warming up, skipping plot check!"
        return

    filename, new_count = qc.countQuakes(url, debug=False)
    
    if new_count:
        utils.sendMailWithAttachment("tom.bech@gmail.com",
                                        "tom.bech@gmail.com",
                                        "Found a new earthquake!",
                                        "Found a new earthquake!",
                                        filename)

    previous_date = datetime.utcnow()       

previous_date = datetime.utcnow()
qc = quake_counter.QuakeCounter()

while True:
    updateDrumPlot()
    sleep(5*60)