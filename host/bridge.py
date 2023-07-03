#!/usr/bin/python
import paho.mqtt.client as mqtt
import time

class Bridge:
    def __init__(self, mqtt_topic, client_id="bridge", user_id="", password="", 
                 host="localhost", port=1883, keepalive=60, qos=0):
        """
        Constructor method for the bridge class
        :param mqtt_topic: The topic to publish/subscribe to
        :param client_id: The ID of the client
        :param user_id: The user ID for the broker
        :param password: The password for the broker
        :param host: The hostname or IP address of the broker
        :param port: The port number of the broker
        :param keepalive: The keepalive interval for the client
        :param qos: The Quality of Service that determines the level of guarantee 
        for message delivery between MQTT client and broker. 
        """
        self.mqtt_topic = mqtt_topic
        self.client_id = client_id
        self.user_id = user_id
        self.password = password
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.qos = qos

        self.disconnect_flag = False
        self.rc = 1
        self.timeout = 0

        # Create the MQTT client object, set the username and password, and register the callback functions
        self.client = mqtt.Client(self.client_id, clean_session=True)
        self.client.username_pw_set(self.user_id, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_unsubscribe = self.on_unsubscribe
        self.client.on_subscribe = self.on_subscribe

        # Connect to the broker
        self.connect()

    def connect(self):
        """
        Connect to the MQTT broker
        """
        while self.rc != 0:
            try:
                print(f":D trying to reconnect to the broker on {self.host}")
                self.rc = self.client.connect(self.host, self.port, self.keepalive)
            except:
                # If the connection fails, wait for 2 seconds before trying again
                print("---")
                print("Oops... Connection failed, and here list some potential issues FYI")
                print("1. Check the WIFI connection. Make sure the port num is an integer. ")
                print("2. Check the MQTT version in the cloud. You might encounter local loopback monitoring issue in mosquitto 2 and higher. (I encountered it in Aliyun). "
                      +"\n You can downgrade MQTT to 1.6 stable or configure mosquitto.conf as appropriate.")
                print(f"3. Check MQTT return code(rc), which currently is {self.rc} \n ---")
            time.sleep(1)
            self.timeout += 2

    def msg_process(self, msg):
        """
        Process incoming MQTT messages
        """
        pass

    def looping(self, loop_timeout=60):
        """
        Start the MQTT client's event loop
        :param loop_timeout: The maximum time to wait for incoming messages before returning
        """
        self.client.loop(loop_timeout)

    def on_connect(self, client, userdata, flags, rc):
        """
        Callback function called when the client successfully connects to the broker
        """
        print(f"Connected to MQTT broker with result code {str(rc)}")
        self.client.subscribe(self.mqtt_topic)
        
        self.timeout = 0
        
    def subscribe(self, topic):
        self.client.subscribe(topic)
        
    def on_disconnect(self, client, userdata, rc):
        """
        Callback function called when the client is unexpectedly disconnected from the broker
        """
        if rc != 0:
            if not self.disconnect_flag:
                print("Unexpected disconnection.")
                print("Trying reconnection")
                self.rc = rc
                self.connect()

    def on_message(self, client, userdata, msg):
        """
        Callback function called when an incoming message is received
        """
        self.msg_process(msg)



    def unsubscribe(self, topic=None):
        """
        Unsubscribe from the MQTT topic
        """
        if topic == None:
            topic = self.mqtt_topic
        print(f"Unsubscribing {topic}")
        self.client.unsubscribe(topic)
        
        
    def disconnect(self):
        """
        Disconnect from the MQTT broker
        """
        print("Disconnecting")
        self.disconnect_flag = True
        self.client.disconnect()

    def on_unsubscribe(self, client, userdata, mid):
        """
        Callback function called when the client successfully unsubscribes from a topic
        """
        # if self.mqtt_topic == "#":
        #     print("Unsubscribed from all topics")
        # else:
        #     print(f"Unsubscribed from {self.mqtt_topic}")
        print("Unsubscribed!")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """
        Callback function called when the client successfully subscribes to a topic
        """
        if self.mqtt_topic == "#":
            print("Subscribed to all topics")
        else:
            print(f"Subscribed to {self.mqtt_topic}")
    
    # def publish(self, message, qos=0):
    #     """
    #     Publish a message to the MQTT broker
    #     :param message: The message to publish
    #     """
    #     self.client.publish(self.mqtt_topic, message, qos)
    
    def publish(self, topic, message="testing", qos=0):
        """
        Publish a message to the MQTT broker
        :param message: The message to publish
        """
        if topic is None:
            topic = self.mqtt_topic
        print(f"Publishing the message ('{message}') to topic {topic}")
        self.client.publish(topic, message, qos)
        
    def hook(self):
        """
        Gracefully shut down the MQTT client
        """
        self.unsubscribe()
        self.disconnect()
        print("Shutting down")

    def get_timeout(self):
        """
        Get the amount of time elapsed since the connection attempt started
        """
        return self.timeout