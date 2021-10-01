import logging
log = logging.getLogger(__name__)
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as MQTTsubscribe
import time


class Digital_Out ():
        
    def __onConnect(self, client, userData, flags, rc):
        # print("{} with return code {}".format(self.name, rc))
        if rc == 0:
            self.connected = True
            # topic = 'devices/io-expander/'+ str(self.networkID) +'/digital-input/'+ str(self.pin)
            # self.doutClient.subscribe(topic)
            # log.info(self.name + " connected to pin " + str(self.pin))
        return

    
    def _turn_pin_on(self,pin):
        topic = "devices/io-expander/{id}/digital-output/{pin}".format(id=self.networkId, pin=pin)
        msg='1'
        return self.doutClient.publish(topic, msg)
    
    def _turn_pin_off(self,pin):
        topic = "devices/io-expander/{id}/digital-output/{pin}".format(id=self.networkId, pin=pin)
        msg='0'
        return self.doutClient.publish(topic, msg)
    

    #TODO: Add functionality for home pin and end pin
    def __init__(self, name, ipAddress, networkId, pin):
        self.connected=False
        self.networkId = networkId
        self.pin = pin
        self.name = name
        self.doutClient = None
        self.doutClient = mqtt.Client()
        self.doutClient.on_connect = self.__onConnect
        self.doutClient.connect(ipAddress)
        self.doutClient.loop_start()
        # Block initialization until mqtt client has established connection
        t0 = time.time()
        while self.connected==False:
            if time.time()-t0 > 15:
                raise Exception("System timeout during connection to to {}".format(self.name))
                
            time.sleep(0.2)
    
    def high(self):
        self._turn_pin_on(self.pin)
        time.sleep(1)
        return True
        
    def low(self):
        self._turn_pin_off(self.pin)
        time.sleep(1)
        return True

    def highF(self):
        self._turn_pin_on(self.pin)
        return True
        
    def lowF(self):
        self._turn_pin_off(self.pin)
        return True
