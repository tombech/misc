import paho.mqtt.client as paho
import os

client_id = "sdhshare_client_" + str(os.getpid())

client = paho.Client(client_id, False)
client.connect("localhost", 1883, 60)

message = "<http://foo/1> <http://bar/2> <http://zoo/3> ."

client.publish("/sdshare/fragment", message)
