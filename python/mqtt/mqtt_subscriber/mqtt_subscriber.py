import paho.mqtt.client as paho
import Queue, workerthreads

endpoint = "http://localhost:8890/sparql"
graph = "http://psi.sesam.no/mqtt_test"

fragment_queue = Queue.Queue()
snapshot_queue = Queue.Queue()

class Subscriber:

    def on_connect(self, mqttc, obj, rc):
        print "Connected to %s:%s" % (mqttc._host, mqttc._port)

    def on_message(self, mqttc, obj, msg):
        print msg.topic+" "+str(msg.qos)+" "+str(msg.payload)

        if msg.topic == "/sdshare/fragment":
            # Add message to fragment queue
            fragment_queue.put(msg.payload)
        elif msg.topic == "/sdshare/snapshot":
            # Add message to snapshot queue
            snapshot_queue.put(msg.payload)

    def on_publish(self, mqttc, obj, mid):
        print "mid: "+str(mid)

    def on_subscribe(self, mqttc, obj, mid, granted_qos):
        print "Subscribed: "+str(mid)+" "+str(granted_qos)

    def on_log(self, mqttc, obj, level, string):
        print string

    def run(self):
        return_code = 0
        try:
            while return_code == 0:
                return_code = self.client.loop()
        except KeyboardInterrupt:
            pass

        return return_code

    def __init__(self, server, channel, port=1883):
        self.client = paho.Client()
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        #self.client.on_log = on_log
        print "Starting subscriber at:", server + ":" + str(port)
        self.client.connect(server, port)
        self.client.subscribe(channel, 0)

# Create threads for handling fragment and snapshot queue
fragment_worker = workerthreads.FragmentWorker(fragment_queue, endpoint, graph)
snapshot_worker = workerthreads.SnapshotWorker(snapshot_queue, endpoint, graph)

# Start worker threads
fragment_worker.start()
snapshot_worker.start()

# Start MQTT subscriber
subscriber = Subscriber("0.0.0.0", "/sdshare/fragment")
result = subscriber.run()

# Stop worker threads
fragment_worker.join()
snapshot_worker.join()

print "Done:", result
