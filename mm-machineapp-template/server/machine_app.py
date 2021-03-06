#/usr/bin/python3

from env import env
import logging
import time
from internal.base_machine_app import MachineAppState, BaseMachineAppEngine
#new from template needed in this program 
from internal.notifier import NotificationLevel, sendNotification, getNotifier
from internal.io_monitor import IOMonitor
from sensor import Sensor
from digital_out import Digital_Out
from pneumatic import Pneumatic
#from math import ceil, sqrt #we will not need math


'''
If we are in development mode (i.e. running locally), we Initialize a mocked instance of machine motion.
This fake MachineMotion interface is used ONLY when developing locally on your own machine motion, so
that you have a good idea of whether or not your application properly builds.
''' 
if env.IS_DEVELOPMENT:
    from internal.fake_machine_motion import MachineMotion
else:
    from internal.machine_motion import MachineMotion

class MachineAppEngine(BaseMachineAppEngine):
    ''' Manages and orchestrates your MachineAppStates '''

    def buildStateDictionary(self):
        '''
        Builds and returns a dictionary that maps state names to MachineAppState.
        The MachineAppState class wraps callbacks for stateful transitions in your MachineApp.

        Note that this dictionary is built when your application starts, not when you click the
        'Play' button.

        returns:
            dict<str, MachineAppState>
        '''
    
        stateDictionary = {
            'Initialize'            : InitializeState(self),
            'Start_State'           : StartState(self),
            'Prepare_New_Roll'      : PrepareNewRollState(self),
            'Replace_Tape'          : ReplaceTapeState(self),
            'Cut_Tape'              : CutTapeState(self),
            'Feed'                  : Feed(self),
            'Clamp'                 : Clamp(self),
            'Tape'                  : Tape(self),
            'Cut'                   : Cut(self),
            'OutFeed'               : Outfeed(self),
            'Home'                  : HomingState(self), #home state rollers need to be down
            'First_Roll'            : FirstRoll(self),
            'Manual_Cut'            : Manual_Cut(self)
        

        }

        return stateDictionary
     
    def getDefaultState(self):
        return 'Initialize'
            
    def onEstop(self):
        pass
    
    def onResume(self):
        pass
    
    def initialize(self):
        ''' 
        Called when you press play in the UI.
        
        In this method, you will Initialize your machine motion instances 
        and configure them. You may also define variables that you'd like to access 
        and manipulate over the course of your MachineApp here.
        '''
        self.logger.info('Running initialization')

        self.sim_enable = True
        # self.sim_enable = False

        if self.sim_enable == True:
            mm_IP= '127.0.0.1' #fake machine IP 
        else:
            mm_IP = '192.168.7.2' 

        
        # Create and configure your machine motion instances
        self.MachineMotion = MachineMotion(mm_IP)

        # Timing Belt
        self.timing_belt_axis = 1 #is this the actuator number? Yes
        self.MachineMotion.configAxis(self.timing_belt_axis, 8, 150) #150 is for mechanical gain for timing belt. If gearbox used then divide by 5
        self.MachineMotion.configAxisDirection(self.timing_belt_axis, 'positive')
        
        #Rollers
        self.roller_axis = 2
        self.MachineMotion.configAxis(self.roller_axis, 8, 319.186/5) 
        self.MachineMotion.configAxisDirection(self.roller_axis, 'positive')
        
        #pneumatics
        dio1 = mm_IP
        dio2 = mm_IP
        
        self.knife_pneumatic = Pneumatic("Knife Pneumatic", ipAddress=dio1, networkId=1, pushPin=0, pullPin=1)     
        self.roller_pneumatic = Pneumatic("Roller Pneumatic", ipAddress=dio2, networkId=2, pushPin=0, pullPin=1) 
        self.plate_pneumatic = Pneumatic("Plate Pneumatic", ipAddress=dio2, networkId=2, pushPin=2, pullPin=3)
        
        #outputs
        self.knife_output = Digital_Out("Knife Output", ipAddress=dio1, networkId=1, pin=0) 
        
        #inputs
        #how do I monitor my digital inputs? IO1 PIN 0 Value 0
        #self.roll_sensor_input = Digital_In("Roll Sensor Input", ipAddress=dio1, networkId=1,pin=0) 
        #use digital read if detecting it is at 0 

        #sensor
        # self.sensor_value = self.MachineMotion.digitalRead(1, 0) #(networkid,pin)
        # self.sensor_value_ui = Sensor("Roller Sensor", ipAddress=dio1, networkId=1, pin=0)
        #self.iomonitor = IOMonitor(self.MachineMotion)
        #fbk means feedback and cmd means command
        #self.iomonitor.startMonitoring("roll_sensor_fbk", True, 1, 0) #I want to monitor feedback from roll sensor
        #self.roll_sensor = Sensor("Roll Sensor", ipAddress=dio1, networkId=1, pin=0)

        #Setup your global variables
        self.Roller_speed = 500
        self.Roller_accel = 120
        self.TapeCut_speed = 850
        self.TapeCut_accel = 850
        self.Grip_speed = 850
        self.Grip_accel = 850
        self.scrap_distance = 20 #mm 
        self.sheet_count = 0
        self.material_length = 0
        self.type_material = 0
        self.sheets_cut = self.sheet_count 
        self.cut_length = 1000
        self.tape_start = 5             #positions tape under material
        self.tape_apply_length = 10     #distance applicator travels before buffer
        self.tape_buff_length = 800     #distance before cut
        self.tape_total_length = 1000   #cuts and leaves tape in final postion
        self.roller_feed_length = 100   #postions material in grip
        self.grip_tighten_length = 3    #clamped material pulled taught
        self.grip_offload_length = 100  #postion material is offloaded
        self.grip_drop_length = 50      #moves material out of grip
        self.reset_running_total_cuts = False
        self.running_total_cuts = 0
        
        #self.flag = 0 #this will note if a new roll is in place

        self.t0 = time.time()
        self.t1 = time.time()
        self.tf = time.time()

        # from UI

        if self.configuration != None:
            self.material_length                = self.configuration['material_length'] 
            self.sheet_count                    = self.configuration['sheet_count']
            self.reset_running_total_cuts = self.configuration['reset_running_total_cuts']
            
            if self.configuration['singleBubble']:
                 self.material_length_mm = self.material_length * 24.5 * 1.055 #tolerence
            
            elif self.configuration['doubleBubble']:
                self.material_length_mm = self.material_length * 24.5 * 1.06 #tolerence


    def onStop(self):
        '''
        Called when a stop is requested from the REST API. 99% of the time, you will
        simply call 'emitStop' on all of your machine motions in this methiod.

        Warning: This logic is happening in a separate thread. EmitStops are allowed in
        this method.
        '''
        self.MachineMotion.emitStop()
        self.knife_output.low() #knife goes down
        self.plate_pneumatic.pull() #plate up 
        #self.MachineMotion.emitHome(self.timing_belt_axis) #knife goes to home
        sendNotification(NotificationLevel.UI_INFO, 'Stop Event', { 'ui_state': 'Complete' })
       
    def onPause(self):
        '''
        Called when a pause is requested from the REST API. 99% of the time, you will
        simply call 'emitStop' on all of your machine motions in this methiod.
        
        Warning: This logic is happening in a separate thread. EmitStops are allowed in
        this method.
        '''
        self.MachineMotion.emitStop() 
    
    def beforeRun(self):
        '''
        Called before every run of your MachineApp. This is where you might want to reset to a default state.
        '''
        pass
    
    def afterRun(self):
        '''
        Executed when execution of your MachineApp ends (i.e., when self.isRunning goes from True to False).
        This could be due to an estop, stop event, or something else.

        In this method, you can clean up any resources that you'd like to clean up, or do nothing at all.
        '''
        pass

    def getMasterMachineMotion(self):
        '''
        Returns the primary machine motion that will be used for estop events.

        returns:
            MachineMotion
        '''
        return self.MachineMotion

## everything not in above class add '.engine' 
class InitializeState(MachineAppState):
    '''
    Called when you press play in the UI.
        
        In this method, you will Initialize your machine motion instances 
        and configure them. You may also define variables that you'd like to access 
        and manipulate over the course of your MachineApp here.

    Puts everything back to the initalizing position. ie knife in home, blade down, pneumatics up 
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):  
        
        if self.engine.reset_running_total_cuts == True:
            self.engine.running_total_cuts = 0
            f = open ("count_sum.txt","w")
            f.write("0")
            f.close
        else:
            f = open ("count_sum.txt","r")
            total_sum_count_string = f.read()
            self.engine.running_total_cuts = int(total_sum_count_string)
            
        sendNotification(NotificationLevel.UI_INFO,'',{ 'ui_running_total_cuts': self.engine.running_total_cuts})
        sendNotification(NotificationLevel.UI_INFO,'Initializing',{ 'ui_state': 'Initializing'})
        self.engine.tf = 0
        if self.configuration['home']:
            self.gotoState('Start_State')
        
        elif self.configuration['prepare_new_roll']:
            self.gotoState('Prepare_New_Roll')

        elif self.configuration['first_roll']:
            self.gotoState('First_Roll') 

        elif self.configuration['manual_cut']:
            self.gotoState('Manual_Cut')
    
    def update(self): 
        pass   

class Manual_Cut(MachineAppState):
    ''' Used any time a manual cut is needed, ie after roll empties, error '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        self.engine.knife_output.low()
        self.engine.MachineMotion.emitAbsoluteMove(self.engine.timing_belt_axis,0)
        self.engine.MachineMotion.waitForMotionCompletion()
      #  if self.engine.MachineMotion.isMotionCompleted() = False:
          #  self.engine.MachineMotion.waitForMotionCompletion() 
          

        sendNotification(NotificationLevel.UI_INFO,'Manual Cut', {'ui_state': 'Manual Cut'})
        self.engine.plate_pneumatic.push() #clamp
        time.sleep(0.2)
        
        self.engine.knife_output.high() #is this correct to bring knife up? yes
        time.sleep(0.2) 
        
        self.engine.MachineMotion.emitSpeed(self.engine.TimingBelt_speed)
        self.engine.MachineMotion.emitAcceleration(self.engine.TimingBelt_accel)
        sendNotification(NotificationLevel.INFO,'Cutting')
        
        self.engine.MachineMotion.emitRelativeMove(self.engine.timing_belt_axis, "positive",self.engine.cut_length) 
        self.engine.MachineMotion.waitForMotionCompletion()
        self.engine.knife_output.low()
        time.sleep(0.1)
        
        self.engine.MachineMotion.emitRelativeMove(self.engine.timing_belt_axis, "positive",-self.engine.cut_length)
        # Double Cut (optional)
        # self.engine.MachineMotion.emitRelativeMove(self.engine.timing_belt_axis, "positive",self.engine.cut_length) 
        # self.engine.MachineMotion.emitRelativeMove(self.engine.timing_belt_axis, "positive",-self.engine.cut_length)
        
        self.engine.MachineMotion.waitForMotionCompletion()
        # if self.engine.MachineMotion.isMotionCompleted() = False:
            # self.engine.MachineMotion.waitForMotionCompletion()
        
        
     
        self.engine.stop()
    
    def update(self): 
        pass 

class PrepareNewRollState(MachineAppState):
    ''' Starts with the clamps up to feed roll. This class is called after the sensor senses there is no more Roll'''
    
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        self.engine.knife_output.low()
        time.sleep(0.1) 
        sendNotification(NotificationLevel.UI_INFO, 'Feed New Roll and Select First Roll Sequence', {'ui_state': 'Prepare New Roll'})
        self.engine.MachineMotion.emitHome(self.engine.timing_belt_axis)
        self.engine.roller_pneumatic.pull()
        self.engine.plate_pneumatic.pull()
        self.engine.MachineMotion.waitForMotionCompletion()
       # if self.engine.MachineMotion.isMotionCompleted() = False:
        #    self.engine.MachineMotion.waitForMotionCompletion()
        self.engine.stop()

    def update(self): 
        pass    

class ReplaceTapeState(MachineAppState):
     ''' Lifts clamp and positions tape applicator where it can be refed. '''
    
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        self.engine.knife_output.low()
        time.sleep(0.1) 
        sendNotification(NotificationLevel.UI_INFO, 'Feed New Roll and Select First Roll Sequence', {'ui_state': 'Prepare New Roll'})
        self.engine.MachineMotion.emitHome(self.engine.timing_belt_axis)
        self.engine.roller_pneumatic.pull()
        self.engine.plate_pneumatic.pull()
        self.engine.MachineMotion.waitForMotionCompletion()
       # if self.engine.MachineMotion.isMotionCompleted() = False:
        #    self.engine.MachineMotion.waitForMotionCompletion()
        self.engine.stop()

    def update(self): 
        pass    

class CutTapeState(MachineAppState):
     ''' Engages tape knife and break so tape can be trimmed. '''
    
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        self.engine.knife_output.low()
        time.sleep(0.1) 
        sendNotification(NotificationLevel.UI_INFO, 'Feed New Roll and Select First Roll Sequence', {'ui_state': 'Prepare New Roll'})
        self.engine.MachineMotion.emitHome(self.engine.timing_belt_axis)
        self.engine.roller_pneumatic.pull()
        self.engine.plate_pneumatic.pull()
        self.engine.MachineMotion.waitForMotionCompletion()
       # if self.engine.MachineMotion.isMotionCompleted() = False:
        #    self.engine.MachineMotion.waitForMotionCompletion()
        self.engine.stop()

    def update(self): 
        pass    
    
class FirstRoll(MachineAppState):
    ''' Rolls material enought to cut first roll and scrap that first piece'''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        
        self.engine.knife_output.low()
        time.sleep(0.1) #seconds
        self.engine.MachineMotion.emitSpeed(self.engine.TimingBelt_speed)
        self.engine.MachineMotion.emitAcceleration(self.engine.TimingBelt_accel)
        self.engine.MachineMotion.emitHome(self.engine.timing_belt_axis) #moves timing belt to Home position (0)
        sendNotification(NotificationLevel.INFO, 'Knife moving to home')
        self.engine.MachineMotion.waitForMotionCompletion()
        self.engine.roller_pneumatic.release()
        time.sleep(0.5)
        sendNotification(NotificationLevel.INFO, 'Rollers Released')
        self.engine.plate_pneumatic.pull()
        sendNotification(NotificationLevel.INFO, 'Plate is up')
        sendNotification(NotificationLevel.UI_INFO,'',{ 'ui_sheets_cut': self.engine.sheet_count})
        
        self.engine.MachineMotion.emitSpeed(self.engine.Roller_speed)
        self.engine.MachineMotion.emitAcceleration(self.engine.Roller_accel)
        self.engine.MachineMotion.emitRelativeMove(self.engine.roller_axis, "positive", self.engine.scrap_distance)
        self.engine.MachineMotion.waitForMotionCompletion()
        self.engine.sheet_count = self.engine.sheet_count + 1 #this makes sure we remove this cut from our count
        self.engine.running_total_cuts = self.engine.running_total_cuts - 1
            
        self.gotoState('Clamp')

    def update(self): 
        pass
    
class StartState(MachineAppState): 
    '''
    Homes our primary machine motion, and sends a message when complete.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        self.engine.cut_length = 1500
        self.engine.knife_output.low()
        time.sleep(0.1) #seconds
        self.engine.MachineMotion.emitSpeed(self.engine.TimingBelt_speed)
        self.engine.MachineMotion.emitAcceleration(self.engine.TimingBelt_accel)
        #TODO: home the first time
        self.engine.MachineMotion.emitHome(self.engine.timing_belt_axis) #moves timing belt to Home position (0)
        sendNotification(NotificationLevel.INFO, 'Knife moving to home')
        self.engine.MachineMotion.waitForMotionCompletion()
        self.engine.roller_pneumatic.release()
        time.sleep(0.5)
        sendNotification(NotificationLevel.INFO, 'Rollers Released')
        self.engine.plate_pneumatic.pull()
        sendNotification(NotificationLevel.INFO, 'Plate is up')
        sendNotification(NotificationLevel.UI_INFO,'',{ 'ui_sheets_cut': self.engine.sheet_count})
        
        self.gotoState('Roll')
       
        # self.engine.sensor_value = self.engine.MachineMotion.digitalRead(1, 0) #(networkid,pin)
        # sendNotification(NotificationLevel.INFO, 'roll detected  =  '+ str(self.engine.sensor_value))
        # if self.engine.sensor_value != 0:
        #     sendNotification(NotificationLevel.INFO, 'No roll detected')
        #     self.gotoState('Prepare_New_Roll')
        # else:
        #     self.gotoState('Roll')
        
        
    #def onResume(self):
    #    self.gotoState('Initialize')    #how is onResume used?
    
    def update(self): 
        pass    

class HomingState(MachineAppState): 
    '''
    Homes our primary machine motion, and sends a message when complete.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        
        self.engine.t0 = time.time()
        
        self.engine.knife_output.low()
        time.sleep(0.1) #seconds
        self.engine.MachineMotion.emitSpeed(self.engine.TimingBelt_speed)
        self.engine.MachineMotion.emitAcceleration(self.engine.TimingBelt_accel)
        #TODO: home the first time
        # 
        # self.engine.MachineMotion.emitAbsoluteMove(self.engine.timing_belt_axis,0) #moves timing belt to Home position (0)
        self.engine.MachineMotion.waitForMotionCompletion()
        sendNotification(NotificationLevel.INFO, 'Knife moving to home')
        
        self.engine.roller_pneumatic.release()
        time.sleep(0.5)
        sendNotification(NotificationLevel.INFO, 'Rollers Released')
        self.engine.plate_pneumatic.pull()
        sendNotification(NotificationLevel.INFO, 'Plate is up')
        
        self.gotoState('Roll')
        
        #to remove 
        # time.sleep(3)
       
        #ToCheck
        # self.engine.sensor_value = self.engine.MachineMotion.digitalRead(1, 0) #(networkid,pin)
        # sendNotification(NotificationLevel.INFO, 'roll detected  =  '+ str(self.engine.sensor_value))
        # if self.engine.sensor_value != 0: #is there a roll? No (1 = no roll)
        #     sendNotification(NotificationLevel.INFO, 'No roll detected')
        #     self.gotoState('Prepare_New_Roll')
        # else:
        #   self.gotoState('Roll')
        
    #def onResume(self):
    #    self.gotoState('Initialize')    #how is onResume used?
    
    def update(self): 
        pass    
    
            
class Feed(MachineAppState):
    '''
    Activate rollers to roll material
    '''
    def __init__(self, engine):
        super().__init__(engine) 

    def onEnter(self):
        #ToCheck
        # self.engine.sensor_value = self.engine.MachineMotion.digitalRead(1, 0) #(networkid,pin)
        # sendNotification(NotificationLevel.INFO, ' roll detected  =  '+ str(self.engine.sensor_value))
        # if self.engine.sensor_value != 0: #is there a roll? No
        #     sendNotification(NotificationLevel.INFO, 'No roll detected')
        #     self.gotoState('Prepare_New_Roll') #is this repetative? no
        # else:
        #     sendNotification(NotificationLevel.UI_INFO,'Rolling State',{'ui_state': 'Roll'})   
        #     self.engine.knife_output.low()
        #     self.engine.MachineMotion.emitAbsoluteMove(self.engine.timing_belt_axis,0)
        #     self.engine.MachineMotion.emitSpeed(self.engine.Roller_speed)
        #     self.engine.MachineMotion.emitAcceleration(self.engine.Roller_accel)
        #     self.engine.MachineMotion.emitRelativeMove(self.engine.roller_axis, "positive", self.engine.material_length_mm)#Distance will be pulled from Global Variable Length input
        #     self.engine.MachineMotion.waitForMotionCompletion()
        #   # if self.engine.MachineMotion.isMotionCompleted() == False:
        #     #    self.engine.MachineMotion.waitForMotionCompletion()
        
        sendNotification(NotificationLevel.UI_INFO,'Rolling State',{'ui_state': 'Roll'})   
        self.engine.knife_output.low()
        # self.engine.MachineMotion.emitAbsoluteMove(self.engine.timing_belt_axis,0)
        self.engine.MachineMotion.emitSpeed(self.engine.Roller_speed)
        self.engine.MachineMotion.emitAcceleration(self.engine.Roller_accel)
        self.engine.MachineMotion.emitRelativeMove(self.engine.roller_axis, "positive", self.engine.material_length_mm)#Distance will be pulled from Global Variable Length input
        self.engine.MachineMotion.waitForMotionCompletion()
       
        self.gotoState('Clamp')
       
        # self.engine.sensor_value = self.engine.MachineMotion.digitalRead(1, 0) #(networkid,pin)
        # sendNotification(NotificationLevel.INFO, 'roll detected  =  '+ str(self.engine.sensor_value))
        # if self.engine.sensor_value != 0: #is there a roll? No
        #     sendNotification(NotificationLevel.INFO, 'Cannot sense roll. Is there enough material to finish last cut? Yes --> Go to Manual Cut sequence. No --> Go to Prepare New Roll Sequence')
        #     self.engine.stop()
        # else:
        #     self.gotoState('Clamp')
       

    def update(self):
        pass
        
        
class Clamp(MachineAppState):
    def __init__(self, engine):
        super().__init__(engine) 

    def onEnter(self):
        self.engine.knife_output.high()
        time.sleep(0.2)
        self.engine.plate_pneumatic.push()   
        time.sleep(0.2)
        sendNotification(NotificationLevel.UI_INFO,'Clamping Down',{ 'ui_state': 'Clamp' })
        # self.engine.MachineMotion.emitAbsoluteMove(self.engine.timing_belt_axis,0)
        # self.engine.MachineMotion.waitForMotionCompletion()
        #if self.engine.MachineMotion.isMotionCompleted() == False:
         #   self.engine.MachineMotion.waitForMotionCompletion() #is this correct? yes
        self.gotoState('Cut')

    def update(self):
        pass


class Cut(MachineAppState):
    def __init__(self, engine):
        super().__init__(engine) 
        
    def onEnter(self):
        # self.engine.MachineMotion.emitAbsoluteMove(self.engine.timing_belt_axis,0)
        # self.engine.MachineMotion.waitForMotionCompletion()
        # if self.engine.MachineMotion.isMotionCompleted() == False:
        #    self.engine.MachineMotion.waitForMotionCompletion() #is this correct? yes
        sendNotification(NotificationLevel.UI_INFO,'Blade Up',{ 'ui_state': 'Cut' })
        self.engine.knife_output.high() #is this correct to bring knife up? yes
        time.sleep(0.2) 
        
        self.engine.MachineMotion.emitSpeed(self.engine.TimingBelt_speed)
        self.engine.MachineMotion.emitAcceleration(self.engine.TimingBelt_accel)
        sendNotification(NotificationLevel.INFO,'Cutting')
        
        
        self.engine.MachineMotion.emitRelativeMove(self.engine.timing_belt_axis, "positive",self.engine.cut_length) 
        self.engine.cut_length = - self.engine.cut_length
        
        self.engine.MachineMotion.waitForMotionCompletion()
        self.engine.knife_output.low()
        time.sleep(0.1)
        
        # self.engine.MachineMotion.emitRelativeMove(self.engine.timing_belt_axis, "positive",-self.engine.cut_length)
        # self.engine.MachineMotion.waitForMotionCompletion()
        
        # Double Cut (optional)
        # self.engine.MachineMotion.emitRelativeMove(self.engine.timing_belt_axis, "positive",self.engine.cut_length) 
        # self.engine.MachineMotion.emitRelativeMove(self.engine.timing_belt_axis, "positive",-self.engine.cut_length)
        
        # self.engine.MachineMotion.waitForMotionCompletion()
      #  if self.engine.MachineMotion.isMotionCompleted() = False:
            # self.engine.MachineMotion.waitForMotionCompletion()
        
        
        self.engine.sheet_count = self.engine.sheet_count - 1
        self.engine.sheets_cut = self.engine.sheets_cut -1 #do I need this
        sendNotification(NotificationLevel.UI_INFO,'',{ 'ui_sheets_cut': self.engine.sheet_count})
        
        # f = open ("count_sum.txt","r")
        # total_sum_count_string = f.read()
        # self.engine.running_total_cuts = int(total_sum_count_string)
        # f.close
        
        self.engine.running_total_cuts = self.engine.running_total_cuts + 1 
        f = open ("count_sum.txt","w")
        f.write(str(self.engine.running_total_cuts))
        f.close
            
        sendNotification(NotificationLevel.UI_INFO,'',{ 'ui_running_total_cuts': self.engine.running_total_cuts})
        
        if self.engine.sheet_count > 0:
            self.engine.t1 = time.time() - self.engine.t0
            self.engine.tf = self.engine.tf + self.engine.t1
            sendNotification(NotificationLevel.INFO,'Cut time = ' + str(self.engine.t1))
            self.gotoState('Home')
        
        else:
            sendNotification(NotificationLevel.INFO,'Final time = ' + str(self.engine.tf))
            self.engine.stop()
    

    def update(self):
        pass

    
