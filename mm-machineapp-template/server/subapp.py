#/usr/bin/python3

import sys
from machine_app import MachineAppEngine
import logging
from logging.handlers import RotatingFileHandler
import time
import json
from threading import Thread

# TODO: Hacky wait to ensure that all print statements are immediately flushed up to the super-process
import functools
print = functools.partial(print, flush=True)

def run():
    try:
        '''  Entry to the MachineApp    subprocess '''
        machineApp = MachineAppEngine()
    
        # First, gather the runtime parameters from the commandline arguments
        configuration = {}
        with open('./internal/configuration.json', 'r') as f:
            configuration = json.loads(f.read())
    
        inStateStepperMode = False
        for argIdx in range(len(sys.argv)):
            if sys.argv[argIdx] == '--inStateStepperMode':
                inStateStepperMode = True
    
        # Next, start the subprocess stdin listener. This will allow the Rest server to tell it to do things
        def stdinListener():
            while True:
                stdinResult = str(sys.stdin.readline()).strip()
    
                if len(stdinResult) == 0:
                    continue
    
                logging.info(stdinResult)
                try:
                    message = json.loads(stdinResult)
                    if not 'request' in message:
                        logging.warning('Malformed message from subprocess: {}'.format(stdinResult))
                        continue
    
                    if message['request'] == 'stop':
                        machineApp.stop()
                    elif message['request'] == 'pause':
                        machineApp.pause()
                    elif message['request'] == 'resume':
                        machineApp.resume()
                    else:
                        logging.warning('Unknown parent process request: {}'.format(message['request']))
                except:
                    continue
    
        stdinthread = Thread(target=stdinListener)
        stdinthread.daemon = True
        stdinthread.start()
    
        # Next, start the MachineAppEngine with the proper variables
        machineApp.loop(inStateStepperMode, configuration)
    except Exception as e:
        logging.exception('Uncaught exception:', exc_info=True)

    # If we've gotten here, we are done. We sys_exit so that the listener thread dies
    sys.exit()

if __name__ == "__main__":
    # Note: All logging here will be outputted to stdout, so that the parent process
    # (aka the Rest Server) can pick it up, and output it to the proper logs.
    logging.basicConfig(
        format='%(asctime)s {%(name)s:%(lineno)d} (%(levelname)s) - %(message)s',
        level=logging.INFO,
        handlers=[
            RotatingFileHandler('machine_app.log', mode='a', maxBytes=5*1024*1024,  backupCount=2, encoding=None, delay=0),
            logging.StreamHandler()
        ]
    )

    run()