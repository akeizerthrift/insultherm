import json
import sys

class SubprocessToParentMessage:
    ''' Messages sent from the Subprocess to the parent process '''
    NONE            = 0
    NOTIFICATION    = 1

def sendSubprocessToParentMsg(type, data = None):
    '''
    Sends a message to the parent process
    '''
    msg = json.dumps({ 'type': type, 'data': data })
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()
