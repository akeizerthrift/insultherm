import logging
log = logging.getLogger(__name__)
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as MQTTsubscribe
import time


class Pneumatic ():
        
    def __onConnect(self, client, userData, flags, rc):
        # print("{} with return code {}".format(self.name, rc))
        if rc == 0:
            self.connected = True
            # topic = 'devices/io-expander/'+ str(self.networkID) +'/digital-input/'+ str(self.pin)
            # self.pneuClient.subscribe(topic)
            # log.info(self.name + " connected to pin " + str(self.pin))
        return

    
    def _turn_pin_on(self,pin):
        topic = "devices/io-expander/{id}/digital-output/{pin}".format(id=self.networkId, pin=pin)
        msg='1'
        return self.pneuClient.publish(topic, msg)
    
    def _turn_pin_off(self,pin):
        topic = "devices/io-expander/{id}/digital-output/{pin}".format(id=self.networkId, pin=pin)
        msg='0'
        return self.pneuClient.publish(topic, msg)
    

    #TODO: Add functionality for home pin and end pin
    def __init__(self, name, ipAddress, networkId, pushPin, pullPin):
        self.connected=False
        self.networkId = networkId
        self.pushPin = pushPin
        self.pullPin = pullPin
        self.name = name
        self.pneuClient = None
        self.pneuClient = mqtt.Client()
        self.pneuClient.on_connect = self.__onConnect
        self.pneuClient.connect(ipAddress)
        self.pneuClient.loop_start()
        # Block initialization until mqtt client has established connection
        t0 = time.time()
        while self.connected==False:
            if time.time()-t0 > 15:
                raise Exception("System timeout during connection to to {}".format(self.name))
                
            time.sleep(0.2)
    
    def push(self):
        self._turn_pin_off(self.pullPin)
        self._turn_pin_on(self.pushPin)
        time.sleep(2)
        return True

    def pushF(self):
        self._turn_pin_off(self.pullPin)
        self._turn_pin_on(self.pushPin)
        return True
        
    def pull(self):
        self._turn_pin_off(self.pushPin)
        self._turn_pin_on(self.pullPin)
        return True
        
    def release(self):
        self._turn_pin_off(self.pullPin)
        self._turn_pin_off(self.pushPin)
        return True
        
