from threading import RLock
import logging

class MqttTopicSubscriber:
    ''' Manages callbacks for a particular machine motion and propagates them up to the client '''

    def __init__(self, machineMotion: 'MachineMotion'):
        self.__lock = RLock()
        self.__queue = []
        self.__callbacks = {}
        self.__machineMotion = machineMotion
        self.__machineMotion.addMqttCallback(self.__mqttEventCallback)
        self.__logger = logging.getLogger(__name__)
        self.__logger.info('Registered new MQTT callback')

    def getMachineMotion(self):
        return self.__machineMotion

    def delete(self):
        '''
        Must be called when your Mqtt subscriber is no longer in use
        '''
        self.__machineMotion.removeMqttCallback(self.__mqttEventCallback)
        self.__logger.info('Removed MQTT callback')

    def __mqttEventCallback(self, topic, msg):
        with self.__lock:
            self.__queue.append((topic, msg))

    def registerCallback(self, topic, callback):
        ''' 
        Register a callback for a particular topic. Note that you should call removeCallback
        when you are finished.

        params:
            topic: str
                MQTT topic that you'd like to subscribe to

            callback: func(topic: str, msg: str) -> void
                Callback that gets called when we receive data on that topic
        '''
        self.__machineMotion.myMqttClient.subscribe(topic)

        if not topic in self.__callbacks:
            self.__callbacks[topic] = []

        self.__callbacks[topic].append(callback)
        return True

    def removeCallback(self, topic, callback):
        '''
        Deregisters a callback for a particular topic. Please be sure to do this when you are done
        using a callback.

        params:
            topic: str
                MQTT topic that you'd like to subscribe to

            callback: func(topic: str, msg: str) -> void
                Callback that gets called when we receive data on that topic
        '''
        if not topic in self.__callbacks:
            return

        self.__callbacks[topic].remove(callback)

    def update(self):
        '''
        If using the MQTT topic susbcriber, this must be called in the 'update'
        method of your MachineAppState node to get the callback properly.
        '''
        with self.__lock:
            processQueue = self.__queue.copy()
            self.__queue.clear()

        for item in processQueue:
            topic = item[0]
            msg = item[1]
            if topic in self.__callbacks:
                callbackList = self.__callbacks[topic]
                for callback in callbackList:
                    callback(topic, msg)