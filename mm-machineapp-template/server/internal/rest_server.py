import logging
from bottle import Bottle, request, response, abort, static_file
import os
import time
import threading
from threading import Thread
from pathlib import Path
import json
import subprocess
import io
import sys
import signal
from internal.notifier import getNotifier, NotificationLevel
from internal.interprocess_message import SubprocessToParentMessage
from machine_app import MachineAppEngine
import paho.mqtt.subscribe as MQTTsubscribe
import paho.mqtt.client as mqtt
import traceback

class RestServer(Bottle):
    '''
    RESTful server that handles control of the MachineApp and configuration IO
    '''
    def __init__(self):
        super(RestServer, self).__init__()
    
        self.__clientDirectory = os.path.join('..', 'client')
        self.__serverDirectory = os.path.join('.')
        self.__logger = logging.getLogger(__name__)
        self.__subprocess = MachineAppSubprocessManager()
        self.__estopManager = EstopManager(self.onEstopEntered)
        self.isPaused = False                   # TODO: It would be better to no track isPaused here

        # Set up callbacks
        self.route('/', callback=self.index)
        self.route('/ping', callback=self.ping)
        self.route('/<filepath:path>', callback=self.serveStatic)
        self.route('/run/start', method='POST', callback=self.start)
        self.route('/run/stop', method='POST', callback=self.stop)
        self.route('/run/pause', method='POST', callback=self.pause)
        self.route('/run/resume', method='POST', callback=self.resume)
        self.route('/run/estop', method='POST', callback=self.estop)
        self.route('/run/estop', method='GET', callback=self.getEstop)
        self.route('/run/releaseEstop', method='POST', callback=self.releaseEstop)
        self.route('/run/resetSystem', method='POST', callback=self.resetSystem)
        self.route('/run/state', method='GET', callback=self.getState)

        self.route('/kill', method='GET', callback=self.kill)
        self.route('/logs', method='GET', callback=self.getLog)
        
    def ping(self):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
        return 'pong'

    def index(self):
        self.__logger.info('Handling index file request')
        return static_file('index.html', root=self.__clientDirectory)
        
    def serveStatic(self, filepath):
        self.__logger.info('Serving static file: {}'.format(filepath))
        return static_file(filepath, root=self.__clientDirectory)

    def getLog(self):
        return static_file('machine_app.log', root=self.__serverDirectory)

    def start(self):
        inStateStepperMode = (request.params['stateStepperMode'] == 'true') if 'stateStepperMode' in request.params else False
        configuration = request.json
        
        if self.__subprocess.start(inStateStepperMode, configuration):
            return 'OK'
        else:
            abort(400, 'Failed to start the MachineApp')

    def stop(self):
        if self.__subprocess.sendMsgToSubprocess({ 'request': 'stop' }):
            self.isPaused = False
            return 'OK'
        else:
            abort(400, 'Failed to stop the MachineApp')

    def pause(self):
        if self.__subprocess.sendMsgToSubprocess({ 'request': 'pause' }):
            self.isPaused = True
            return 'OK'
        else:
            abort(400, 'Failed to pause the MachineApp')

    def resume(self):
        if self.__subprocess.sendMsgToSubprocess({ 'request': 'resume' }):
            self.isPaused = False
            return 'OK'
        else:
            abort(400, 'Failed to resume the MachineApp')

    def estop(self):
        if self.__estopManager.estop():
            self.onEstopEntered()
            self.isPaused = False
            return 'OK'
        else:
            abort(400, 'Failed to estop the MachineApp')

    def getEstop(self):
        return self.__estopManager.getEstop()

    def releaseEstop(self):
        if self.__estopManager.release():
            return 'OK'
        else:
            abort(400, 'Failed to release estop')

    def resetSystem(self):
        if self.__estopManager.reset():
            return 'OK'
        else:
           abort(400, 'Failed to reset the system')

    def getState(self):
        return {
            "isRunning": self.__subprocess.isRunning(),
            "isPaused": self.isPaused
        }

    def kill(self):
        self.__subprocess.terminate()
        os.kill(os.getpid(), signal.SIGTERM)
        return 'OK'
        
    def onEstopEntered(self):
        try:
            if self.__subprocess.isRunning():
                self.__subprocess.terminate()
                self.isPaused = False
                
                # Create a temporary MachineAppEngine and call onEstop
                temporaryApp = MachineAppEngine()
                temporaryApp.initialize()
                temporaryApp.onEstop()
        except Exception as e:
            logging.warning("Failed to call onEstop: %s" % (traceback.format_exc()))
            self.__notifier.sendMessage(NotificationLevel.ERROR, 'Failed to call onEstop for the MachineApp. Check the internal logs for more info.')

class MQTTPATHS :
    ESTOP = "estop"
    ESTOP_STATUS = ESTOP + "/status"
    ESTOP_TRIGGER_REQUEST = ESTOP + "/trigger/request"
    ESTOP_TRIGGER_RESPONSE = ESTOP + "/trigger/response"
    ESTOP_RELEASE_REQUEST = ESTOP + "/release/request"
    ESTOP_RELEASE_RESPONSE = ESTOP + "/release/response"
    ESTOP_SYSTEMRESET_REQUEST = ESTOP + "/systemreset/request"
    ESTOP_SYSTEMRESET_RESPONSE = ESTOP + "/systemreset/response"

class EstopManager:
    TIMEOUT = 10.0

    '''
    Small class that subscribes/publishes to MQTT eStop events 
    to control the current state of the estop.
    '''
    def __init__(self, onEstopEntered):
        self.__onEstopEntered = onEstopEntered
        self.__isEstopped = False
        self.__notifier = getNotifier()
        self.__mqttClient = mqtt.Client()
        self.__logger = logging.getLogger(__name__)
        self.__mqttClient.on_connect = self.__onConnect
        self.__mqttClient.on_message = self.__onMessage
        self.__mqttClient.on_disconnect = self.__onDisconnect
        self.IP = '127.0.0.1'
        self.__mqttClient.connect(self.IP)
        self.__mqttClient.loop_start()

    def __onConnect(self, client, userData, flags, rc):
        if rc == 0:
            self.__mqttClient.subscribe(MQTTPATHS.ESTOP_STATUS)

    def __onMessage(self, client, userData, msg):
        topicParts = msg.topic.split('/')
        deviceType = topicParts[1]

        if (topicParts[0] == MQTTPATHS.ESTOP) :
            if (topicParts[1] == "status") :
                self.__isEstopped = json.loads(msg.payload.decode('utf-8'))

                if self.__isEstopped:
                    self.__notifier.sendMessage(NotificationLevel.APP_ESTOP, 'Machine is in estop')
                    self.__onEstopEntered()
                else:
                    self.__notifier.sendMessage(NotificationLevel.APP_ESTOP_RELEASE, 'Estop Released')


    def __onDisconnect(self, client, userData, rc):
        logging.info("Disconnected with rtn code [%d]"% (rc))
        return

    def estop(self):
        return_value = { 'value': False }

        def mqttResponse() :
            # Wait for response
            return_value['value'] = json.loads(MQTTsubscribe.simple(MQTTPATHS.ESTOP_TRIGGER_RESPONSE, retained = False, hostname = self.IP).payload.decode('utf-8'))
        
            return

        mqttResponseThread = threading.Thread(target = mqttResponse)
        mqttResponseThread.daemon = True
        mqttResponseThread.start()

        # Adding a delay to make sure MQTT simple function is launched before publish is made. Quick fix from bug on App. Launcher.
        time.sleep(0.2)

        # Publish trigger request on MQTT
        self.__mqttClient.publish(MQTTPATHS.ESTOP_TRIGGER_REQUEST, "message is not important")

        mqttResponseThread.join(EstopManager.TIMEOUT)

        if mqttResponseThread.isAlive() :
            self.__logger.error('MQTT response timeout.')
            return False
        else :
            return return_value['value']

        return return_value['value']

    def release(self):
        return_value = { 'value': False }

        def mqttResponse() :
            # Wait for response
            return_value['value'] = json.loads(MQTTsubscribe.simple(MQTTPATHS.ESTOP_RELEASE_RESPONSE, retained = False, hostname = self.IP).payload.decode('utf-8'))

            return

        mqttResponseThread = threading.Thread(target = mqttResponse)
        mqttResponseThread.daemon = True
        mqttResponseThread.start()

        # Adding a delay to make sure MQTT simple function is launched before publish is made. Quick fix from bug on App. Launcher.
        time.sleep(0.2)

        # Publish release request on MQTT
        self.__mqttClient.publish(MQTTPATHS.ESTOP_RELEASE_REQUEST, "message is not important")

        mqttResponseThread.join(EstopManager.TIMEOUT)

        if mqttResponseThread.isAlive() :
            self.__logger.error('MQTT response timeout.')
            return False
        else :
            return return_value['value']

        return return_value['value']

    def reset(self):
        return_value = { 'value': False }

        def mqttResponse() :
            # Wait for response
            return_value['value'] = json.loads(MQTTsubscribe.simple(MQTTPATHS.ESTOP_SYSTEMRESET_RESPONSE, retained = False, hostname = self.IP).payload.decode('utf-8'))

            return

        mqttResponseThread = threading.Thread(target = mqttResponse)
        mqttResponseThread.daemon = True
        mqttResponseThread.start()

        # Adding a delay to make sure MQTT simple function is launched before publish is made. Quick fix from bug on App. Launcher.
        time.sleep(0.2)

        # Publish reset system request on MQTT
        self.__mqttClient.publish(MQTTPATHS.ESTOP_SYSTEMRESET_REQUEST, "message is not important")

        mqttResponseThread.join(EstopManager.TIMEOUT)

        if mqttResponseThread.isAlive() :
            self.__logger.error('MQTT response timeout.')
            return False
        else :
            return return_value['value']

        return return_value['value']

    def getEstop(self):
        return 'true' if self.__isEstopped else 'false'

class MachineAppSubprocessManager:
    '''
    Manages the lifetime of the MachineApp subprocess, forwards stdin commands and stdout information.
    '''

    def __init__(self):
        self.__isRunning = False
        self.__subprocess = None
        self.__stdout = None
        self.__stderr = None
        self.__logger = logging.getLogger(__name__)
        self.__notifier = getNotifier()

        self.__stdthread = Thread(name='subprocess_stdout', target=self.__update)
        self.__stdthread.daemon = True
        self.__stdthread.start() 

    def start(self, inStateStepperMode, configuration):
        '''
        Starts running the MachineApp in a new process
        '''
        if self.__isRunning == True:
            return False

        with open('./internal/configuration.json', 'w') as f:
            f.write(json.dumps(configuration, indent=4))

        command = [ sys.executable, 'subapp.py' ]
        if inStateStepperMode:
            command.append('--inStateStepperMode')

        self.__logger.info('Attempting to run subprocess: {}'.format(' '.join(command)))
        self.__subprocess = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        self.__isRunning = True

        return True

    def sendMsgToSubprocess(self, data):
        '''
        Write a JSON payload to stdin  of the child process
        '''
        if self.__subprocess == None:
            return False

        self.__subprocess.stdin.write(str(json.dumps(data) + '\r\n').encode('utf-8'))
        self.__subprocess.stdin.flush()
        return True

    def __update(self):
        '''
        Used to forward notifier messages from the child process to the client. This enables us to not
        have to constantly disconnect/reconnect to the child process' websocket whenever the user pressed
        start or stop.

        We also catch standard 'print' outputs here too, and print them out to the parent process' console.
        '''
        while True:          # Waiting to receive the start command, will sleep in the meantime
            while self.__isRunning:  # Received start and waiting on the subprocess stdout
                if self.__subprocess == None or self.__subprocess.poll() != None or self.__subprocess.stdout.closed:
                    self.__isRunning = False
                    self.__logger.info('Subprocess is no longer active')
                    continue

                while self.__subprocess != None and self.__subprocess.stdout != None and self.__subprocess.stdout.readable():
                    line = self.__subprocess.stdout.readline().decode('utf-8').strip()

                    if len(line) == 0:
                        break

                    line = line.strip()
                    try:
                        content = json.loads(line)

                        if not "type" in content:
                            continue

                        msgType = content["type"]
                        if msgType == SubprocessToParentMessage.NOTIFICATION:
                            notification = content["data"]
                            self.__notifier.sendMessage(notification['level'], notification['message'], notification['customPayload'])
                    except:
                        print(line)

            time.sleep(1.0)


    def terminate(self):
        '''
        Terminates the subprocess immediately

        returns:
            bool
                Successfully terminated a running application or not
        '''
        if self.__subprocess == None:
            return False

        self.__subprocess.kill()
        self.__subprocess = None
        return True

    def isRunning(self):
        return self.__isRunning

def runServer():
    restServer = RestServer()
    restServer.run(host='0.0.0.0', port=3011, server='paste')