#!/usr/bin/env python

import paho.mqtt.client as mqtt
import threading
import json
import requests
import time
import rospy
import numpy as np
from bridge import Bridge
from point_cloud_forwarder import PointCloudForwarder
from image_forwarder import ImageForwarder
import logging

class Vibot(Bridge):
    # Define class constant 
    DEFAULT_MQTT_TOPIC = "/iot_device/command"
    
    def __init__(
        self, 
        mqtt_topic=DEFAULT_MQTT_TOPIC,
        client_id="vibot_device", 
        user_id="", 
        password="", 
        host="43.133.159.102", 
        port=1883, 
        keepalive=60, 
        qos=0
    ):
       
        self.status_check_topic = "/iot_device/status_check"
        self.command_topic = mqtt_topic
        self.response_topic = "/iot_device/command_response"
        
        self.enable_vio_algorithm_url = 'http://localhost:8000/Smart/algorithmEnable'
        
        # instantiate two bridges for point clouds and images
        self.pc_bridge = PointCloudForwarder(mqtt_topic="/data/point_cloud", host="43.133.159.102", port=1883, qos=2)
        self.img_bridge = ImageForwarder(mqtt_topic="/data/img", host="43.133.159.102", port=1883, qos=2)

        # Initialize the ROS forwarder node, which can
        # 1. Subscribe to a topic in ROS. 
        # 2. Immediately publish the message received to the MQTT topic in the cloud. 
        # Currently it can merely forward two types of message, 
        # as seen in point_cloud_forwarder.py and image_forwarder.py
        rospy.init_node("forwarder", anonymous=True)
        

        # Configure logging to both console and file
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Add file handler
        file_handler = logging.FileHandler("vibot_device.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # We take the command topic as default mqtt topic. 
        super().__init__(mqtt_topic, client_id, user_id, password, host, port, keepalive, qos)
                
    def msg_process(self, msg):
        """
        Process incoming MQTT messages from topic "/iot_device/command"
        """
        msg_topic = msg.topic
        msg = str(msg.payload.decode())
        self.logger.debug(f"Processing message {msg} from topic {msg_topic}")
        
        if msg == "status_check":
            # This message is used to verify the status of the IoT device. 
            # The current implementation involves the following steps:
            # 1. The host sends a string "status_check" to the IoT device via the MQTT broker.
            # 2. The device sends a string "status_ok" to the host via the broker to indicate that it is online and responsive.
            # 
            # TODO: To enhance the security of this verification process, additional authentication and authorization mechanisms 
            # could be implemented to ensure that only authorized hosts can send the "status_check" message, 
            # and only authorized devices can respond with the "status_ok" message.
            self.publish("/iot_device/status_response", "status_ok")
            self.logger.debug("Sent status_ok to /iot_device/status_response")
        
        elif msg == "enable_vio_service":

            # Make the HTTP PUT request
            http_response = requests.put(self.enable_vio_algorithm_url)

            # Check the response status code
            if http_response.status_code == 200: 
                self.logger.info('Vio algorithm enabled\n')
            else:
                self.logger.warning('Failed to enable vio algorithm, please enable it manually\n')
            
            message = {'type': 'enable_vio', 'code': http_response.status_code}
            json_message = json.dumps(message)
            self.publish(self.response_topic, json_message)
        
        elif msg == "disable_vio_service":
            
            url = 'http://localhost:8000/Smart/algorithmDisable'
            response = requests.put(url)

            if response.status_code == 200:
                self.logger.info('Vio algorithm disabled\n')
            else:
                self.logger.info('Failed to enable vio algorithm, please disable it manually\n')
            
            message = {'type': 'disable_vio', 'code': response.status_code}
            json_message = json.dumps(message)
            self.publish(self.response_topic, json_message)
                        
        elif msg == "start_point_cloud_transfer":
            self.start_point_cloud_transfer()
            
        elif msg == "end_point_cloud_transfer":
            self.end_point_cloud_transfer()
            
        elif msg == "start_image_transfer":
            self.start_image_transfer()
            
        elif msg == "end_image_transfer":
            self.end_image_transfer()
            
        else:
            self.logger.warning(f"Vibot received unknown message: {msg}")
            pass
    

    def start_point_cloud_transfer(self):
        
        message = {'type': 'start_point_cloud_transfer', 'code': 200}
        json_message = json.dumps(message)
        self.publish("/iot_device/command_response", message=json_message)
        self.logger.debug("sent to iot_device/command_response indicating we are starting the point cloud transfer")
        
        try:
            self.pc_bridge.start_forwarding()

            rospy.spin()
        except rospy.ROSInterruptException:
            pass
        except Exception as e:
            # message = {'type': 'start_point_cloud_transfer', 'code': 400}
            # json_message = json.dumps(message)
            # self.publish("/iot_device/command_response", message=json_message)
            self.logger.error(e)
        
    def end_point_cloud_transfer(self):
        
        message = {'type': 'end_point_cloud_transfer', 'code': 200}
        json_message = json.dumps(message)
        self.publish("/iot_device/command_response", message=json_message)
        self.logger.debug("sent to iot_device/command_response indicating we are ending the point cloud transfer")
        
        try:
            self.pc_bridge.stop_forwarding()
            
            rospy.signal_shutdown('Stopped forwarding point clouds.')
        except rospy.ROSInterruptException:
            pass
        except Exception as e:
            # message = {'type': 'end_point_cloud_transfer', 'code': 400}
            # json_message = json.dumps(message)
            # self.publish("/iot_device/command_response", message=json_message)
            self.logger.error(e)
        
    def start_image_transfer(self):
        message = {'type': 'start_image_transfer', 'code': 200}
        json_message = json.dumps(message)
        self.publish("iot_device/command_response", message=json_message)
        print("--log--: sent to iot_device/image indicating we are starting the image transfer")
        
        try:
            self.img_bridge.start_forwarding()
            rospy.spin()
        except rospy.ROSInterruptException:
            pass
        except Exception as e:
            self.logger.error(e)
        
    def end_image_transfer(self):
        message = {'type': 'end_image_transfer', 'code': 200}
        json_message = json.dumps(message)
        self.publish("iot_device/command_response", message=json_message)
        print("--log--: sent to iot_device/image indicating we are starting the image transfer")
        
        try:
            self.img_bridge.stop_forwarding()
            rospy.signal_shutdown('Stopped forwarding images.')
        except rospy.ROSInterruptException:
            pass
        except Exception as e:
            self.logger.error(e)
            
    def on_connect(self, client, userdata, flags, rc):
        """
        Callback function called when the client successfully connects to the broker
        """
        print(f"Connected to MQTT broker with result code {str(rc)}")
        self.client.subscribe(self.status_check_topic)
        self.client.subscribe(self.command_topic)
        self.timeout = 0
        
        # Continuously publish device heartbeat 
        # daemon thread is running in the background and does not prevent the
        # main program from existing. when the main program exists, any 
        # remaining daemon threads are terminated automatically. 
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        heartbeat_thread.start()
        
    
    def send_heartbeat(self):
        """
        Publish device heartbeat 
        """
        while True:
            self.publish("/iot_device/heartbeat", "heartbeat")            
            time.sleep(2)
        
if __name__ == "__main__":
    
    # Set up MQTT client and callbacks
    sn = Vibot()
    sn.client.loop_forever()
    

    

