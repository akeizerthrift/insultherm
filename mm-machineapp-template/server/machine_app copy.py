#/usr/bin/python3

from env import env
import logging
import time
from internal.base_machine_app import MachineAppState, BaseMachineAppEngine
from internal.notifier import NotificationLevel, sendNotification, getNotifier
from internal.io_monitor import IOMonitor
from sensor import Sensor
from digital_out import Digital_Out
from pneumatic import Pneumatic
from math import ceil, sqrt

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
            'Move_Ballscrew'        : BallScrewState(self),
            'Initial_Stretch'       : InitialStretchState(self),
            'Regrip1'               : Regrip1State(self),
            'Droop_Stretch'         : DroopStretchState(self),
            'Pre_Vehicle_Arrives'   : PreVehicleArrivesState(self),            
            'Vehicle_Arrives'       : VehicleArrivesState(self),
            'Feed_New_Roll'         : FeedNewRollState(self),
            'Remove_Material'       : RemoveMaterialState(self),
            'Home'                  : HomingState(self)
        }

        return stateDictionary

    def getDefaultState(self):
        '''
        Returns the state that your Application begins in when a run begins. This string MUST
        map to a key in your state dictionary.

        returns:
            str
        '''
        return 'Initialize'
    
    def findSpeed(self, total_dist, total_time, accel, decel):

        a = 1
        b = -(2.0*accel*decel*total_time)/(accel+decel)
        c = (2.0*decel*accel*total_dist)/(accel+decel)

        discriminant = b**2 - 4*a*c

        if discriminant < 0:
            print ("Cannot solve for speed. Increase acceleration, deceleration or cycle time")
            return None
        else:
            speed = (-1*b - sqrt(discriminant)) / (2.0*a)  

            motion_profile = {
                "speed"      : speed,                                                      # calculated speed
                "accel"      : accel,                                                      # given acceleration
                "decel"      : decel,                                                      # given deceleration
                "total_dist" : total_dist,                                                 # given distance 
                "total_time" : total_time,                                                 # given total time of movement
                "accel_time" : speed/accel,                                                # amount of time in acceleration
                "decel_time" : speed/decel,                                                # amount of time in deceleration
                "speed_time" : total_time - ((speed/accel) + (speed/decel)),               # amount of time at calculated speed
                "accel_dist" : ((speed/accel)**2)*0.5*accel,                               # distance covered during acceleration
                "decel_dist" : ((speed/decel)**2)*0.5*decel,                               # distance covered during deceleration
                "speed_dist" : speed * (total_time - ((speed/accel) + (speed/decel))),     # distance covered while at calculated speed
                "stop_time"  : total_time - (speed/decel)                                  # time from start of motion till beginning of deceleration (when to send StopContinuosMove command)
            }

            return (motion_profile)

    def findTime(self, total_dist, speed, accel, decel):
    
        accel_dist_check = ((speed/accel)**2)*0.5*accel
        decel_dist_check = ((speed/decel)**2)*0.5*decel
        
        if(accel_dist_check + decel_dist_check < total_dist): 
            accel_dist = accel_dist_check
            decel_dist = decel_dist_check
            speed_time = (total_dist - accel_dist - decel_dist)/speed
            final_speed = speed
            
        else:
            speed_time = 0.0
            final_speed  = sqrt((8.0*total_dist*accel*decel)/(accel+decel))/2

        accel_time  = final_speed/accel
        decel_time = final_speed/decel
        accel_dist = ((accel_time)**2)*0.5*accel
        decel_dist = ((decel_time)**2)*0.5*decel
        total_time = accel_time + speed_time + decel_time
        accel_dist = ((accel_time)**2)*0.5*accel
        decel_dist = ((decel_time)**2)*0.5*decel
        speed_dist = final_speed * speed_time
        stop_time = accel_time + speed_time

        motion_profile = {
            "speed"      : final_speed,                                                # given speed
            "accel"      : accel,                                                      # given acceleration
            "decel"      : decel,                                                      # given deceleration
            "total_dist" : total_dist,                                                 # given distance 
            "total_time" : total_time,                                                 # calculated total time of movement
            "accel_time" : accel_time,                                                 # amount of time in acceleration
            "decel_time" : decel_time,                                                 # amount of time in deceleration
            "speed_time" : speed_time,                                                 # amount of time at calculated speed
            "accel_dist" : accel_dist,                                                 # distance covered during acceleration
            "decel_dist" : decel_dist,                                                 # distance covered during deceleration
            "speed_dist" : speed_dist,                                                 # distance covered while at calculated speed
            "stop_time"  : stop_time                                                   # time from start of motion till beginning of deceleration (when to send StopContinuosMove command)
        }

        return (motion_profile)
    
    def initialize(self):
        ''' 
        Called when you press play in the UI.
        
        In this method, you will Initialize your machine motion instances 
        and configure them. You may also define variables that you'd like to access 
        and manipulate over the course of your MachineApp here.
        '''
        self.logger.info('Running initialization')
        
        # self.sim_enable = True
        self.sim_enable = False

        if self.sim_enable == True:
            mm1_IP = mm2_IP = mm3_IP = "127.0.0.1"
        else:
            mm1_IP = "192.168.0.11"
            mm2_IP = "192.168.0.12"
            mm3_IP = "192.168.0.13"

        # Create and configure your machine motion instances
        self.mm1 = MachineMotion(mm1_IP)
        self.mm2 = MachineMotion(mm2_IP)
        self.mm3 = MachineMotion(mm3_IP)

        # Timing Belts 
        self.timing_belt_axis = 1
        self.mm1.configAxis(self.timing_belt_axis, 8, 150/5)
        self.mm1.configAxisDirection(self.timing_belt_axis, 'positive')

        # Nozzle Linear
        self.nozzle_linear_axis = 3
        self.mm1.configAxis(self.nozzle_linear_axis, 8, 6)
        self.mm1.configAxisDirection(self.nozzle_linear_axis, 'positive')

        # Ball Screws 
        self.ball_screw_axis = 1
        self.mm2.configAxis(self.ball_screw_axis, 8, 10)
        self.mm2.configAxisDirection(self.ball_screw_axis, 'positive')

        # Nozzle Rotation
        self.nozzle_rotation_axis = 1
        self.mm3.configAxis(self.nozzle_rotation_axis, 8, 36)
        self.mm3.configAxisDirection(self.nozzle_rotation_axis, 'positive')

        self.mm3.configHomingSpeed([self.nozzle_rotation_axis], [5])

        # Hot Wire Cylinders
        self.hot_wire_axis = 2
        self.mm3.configAxis(self.hot_wire_axis, 8, 6)
        self.mm3.configAxisDirection(self.hot_wire_axis, 'negative')
    
        dio1_mm = mm1_IP
        dio2_mm = mm1_IP
        dio3_mm = mm1_IP

        self.mobile_clamped = Sensor("Mobile Clamped", ipAddress=dio1_mm, networkId=1, pin=3)
        self.mobile_released = Sensor("Mobile Released", ipAddress=dio1_mm, networkId=1, pin=2)

        self.mobile_pneumatic = Pneumatic("Mobile Pneumatic", ipAddress=dio1_mm, networkId=1, pushPin=2, pullPin=3)

        self.return_roller_up = Sensor("Return Roller Up", ipAddress=dio2_mm, networkId=2, pin=3)
        self.return_roller_down = Sensor("Return Roller Down", ipAddress=dio2_mm, networkId=2, pin=2)
        self.fixed_clamped = Sensor("Fixed Clamped", ipAddress=dio2_mm, networkId=2, pin=0)
        self.fixed_released = Sensor("Fixed Released", ipAddress=dio2_mm, networkId=2, pin=1)

        self.roller_pneumatic = Pneumatic("Roller Pneumatic", ipAddress=dio2_mm, networkId=2, pushPin=2, pullPin=3)
        self.fixed_pneumatic = Pneumatic("Fixed Pneumatic", ipAddress=dio2_mm, networkId=2, pushPin=0, pullPin=1)
        
        self.vehicle_start = Sensor("Vehicle Sensor", ipAddress=dio3_mm, networkId=3, pin=3)

        self.air_master = Digital_Out("Air Master", ipAddress=dio3_mm, networkId=3, pin=0)
        self.air_nozzle = Digital_Out("Air Nozzle", ipAddress=dio3_mm, networkId=3, pin=1)
        self.hot_wire = Digital_Out("Hot Wire", ipAddress=dio3_mm, networkId=3, pin=2)
        
        # for now all IO are on the same MM, but in the future may need to have iomonitor on each mm with an IO
        self.iomonitor = IOMonitor(self.mm1)
        self.iomonitor.startMonitoring("return_roller_down_cmd", False, 1, 1)
        self.iomonitor.startMonitoring("return_roller_down_fbk", True, 1, 0)
        self.iomonitor.startMonitoring("return_roller_up_cmd", False, 1, 0)
        self.iomonitor.startMonitoring("return_roller_up_fbk", True, 1, 1)
        self.iomonitor.startMonitoring("mobile_release_cmd", False, 1, 3)
        self.iomonitor.startMonitoring("mobile_released_fbk", True, 1, 2)
        self.iomonitor.startMonitoring("mobile_clamp_cmd", False, 1, 2)
        self.iomonitor.startMonitoring("mobile_clamped_fbk", True, 1, 3)
        self.iomonitor.startMonitoring("fixed_clamp_cmd", False, 2, 1)
        self.iomonitor.startMonitoring("fixed_clamped_fbk", True, 2, 0)
        self.iomonitor.startMonitoring("fixed_release_cmd", False, 2, 0)
        self.iomonitor.startMonitoring("fixed_released_fbk", True, 2, 1)
        self.iomonitor.startMonitoring("hot_wire_cmd", False, 2, 3)
        self.iomonitor.startMonitoring("air_nozzle_cmd", False, 3, 1)
        self.iomonitor.startMonitoring("air_master_cmd", False, 3, 0)

        # from UI

        if self.configuration != None:
            self.nozzle_linear_pos1             = self.configuration['nozzle_linear_pos1']
            self.nozzle_linear_pos2             = self.configuration['nozzle_linear_pos2']
            self.nozzle_linear_pos3             = self.configuration['nozzle_linear_pos3']
            self.nozzle_rotation_pos1           = self.configuration['nozzle_rotation_pos1']
            self.nozzle_rotation_pos2           = self.configuration['nozzle_rotation_pos2']
            self.nozzle_rotation_pos3           = self.configuration['nozzle_rotation_pos3']
            self.nozzle_cycle_time_1_2          = self.configuration['nozzle_cycle_time_1_2']
            self.nozzle_cycle_time_2_3          = self.configuration['nozzle_cycle_time_2_3']
            self.droop_length                   = self.configuration['droop_length']
            self.regrip1_distance               = self.configuration['regrip1_distance']
            self.regrip2_distance               = self.configuration['regrip2_distance']
            self.regrip2_speed                  = self.configuration['regrip2_speed']
            self.regrip2_accel                  = self.configuration['regrip2_accel']
            self.vehicle_speed                  = self.configuration['vehicle_speed']
            self.vehicle_accel                  = self.configuration['vehicle_accel']

            self.ball_screw_pos                 = self.configuration['ball_screw_pos']
            self.timing_belt_speed              = self.configuration['timing_belt_speed']
            self.timing_belt_accel              = self.configuration['timing_belt_accel']
            self.nozzle_P2_delay                = self.configuration['nozzle_P2_delay']
            self.nozzle_P3_delay                = self.configuration['nozzle_P3_delay']
            self.mobile_gripper_open_delay      = self.configuration['mobile_gripper_open_delay']
            self.hot_wire_on_delay              = self.configuration['hot_wire_on_delay']
            self.hot_wire_hold_delay            = self.configuration['hot_wire_hold_delay']
            self.fix_gripper_open_delay         = self.configuration['fix_gripper_open_delay']

            # Internal
    
            self.brake1_aux = 1
            self.brake2_aux = 2
    
            self.timing_belt_end = 1540
            self.timing_belt_avoid_nozzle = 1000
            self.hot_wire_distance = 66
    
            self.ball_screw_speed = 50
            self.ball_screw_accel = 50
    
            self.hot_wire_speed = 100
            self.hot_wire_accel = 150
    
            self.nozzle_rotation_accel = 200
            self.nozzle_linear_accel = 1000
    
            self.pneumatic_timeout = 5
    
            self.regrip2_cycle_count = 0
    
            # Calculated

            self.nozzle_linear_1_2_profile = self.findSpeed((float(self.nozzle_linear_pos2)-self.nozzle_linear_pos1), self.nozzle_cycle_time_1_2, self.nozzle_linear_accel, self.nozzle_linear_accel)
            if self.nozzle_linear_1_2_profile == None:
                sendNotification(NotificationLevel.INFO, 'Cannot calculate Nozzle Linear 1-2 speed. Increase acceleration or cycle time, or decrease distance')
                self.stop()
            
            self.nozzle_rotation_1_2_profile = self.findSpeed((float(self.nozzle_rotation_pos2)-self.nozzle_rotation_pos1), self.nozzle_cycle_time_1_2, self.nozzle_rotation_accel, self.nozzle_rotation_accel)
            if  self.nozzle_rotation_1_2_profile == None:
                sendNotification(NotificationLevel.INFO, 'Cannot calculate Nozzle Rotation 1-2 speed. Increase acceleration or cycle time, or decrease distance')
                self.stop()

            self.nozzle_linear_2_3_profile = self.findSpeed((float(self.nozzle_linear_pos3)-self.nozzle_linear_pos2), self.nozzle_cycle_time_2_3, self.nozzle_linear_accel, self.nozzle_linear_accel)
            if self.nozzle_linear_2_3_profile == None:
                sendNotification(NotificationLevel.INFO, 'Cannot calculate Nozzle Linear 2-3 speed. Increase acceleration or cycle time, or decrease distance')
                self.stop()

            self.nozzle_rotation_2_3_profile = self.findSpeed((float(self.nozzle_rotation_pos3)-self.nozzle_rotation_pos2), self.nozzle_cycle_time_2_3, self.nozzle_rotation_accel, self.nozzle_rotation_accel)
            if self.nozzle_rotation_2_3_profile == None:
                sendNotification(NotificationLevel.INFO, 'Cannot calculate Nozzle Rotation 2-3 speed. Increase acceleration or cycle time, or decrease distance')
                self.stop()

            self.nozzle_speed_linear_1_2 = self.nozzle_linear_1_2_profile ["speed"]
            self.nozzle_speed_rotational_1_2 = self.nozzle_rotation_1_2_profile ["speed"]
            self.nozzle_linear_1_2_stop_time = self.nozzle_linear_1_2_profile ["stop_time"]
            self.nozzle_rotation_1_2_stop_time = self.nozzle_rotation_1_2_profile ["stop_time"]
            self.nozzle_linear_1_2_decel_time = self.nozzle_linear_1_2_profile ["decel_time"]
            self.nozzle_rotation_1_2_decel_time = self.nozzle_rotation_1_2_profile ["decel_time"]
            
            self.nozzle_speed_linear_2_3 = self.nozzle_linear_2_3_profile ["speed"]
            self.nozzle_speed_rotational_2_3 = self.nozzle_rotation_2_3_profile ["speed"]
            self.nozzle_linear_2_3_stop_time = self.nozzle_linear_2_3_profile ["stop_time"]
            self.nozzle_rotation_2_3_stop_time = self.nozzle_rotation_2_3_profile ["stop_time"]
            self.nozzle_linear_2_3_decel_time = self.nozzle_linear_2_3_profile ["decel_time"]
            self.nozzle_rotation_2_3_decel_time = self.nozzle_rotation_2_3_profile ["decel_time"]

            self.max_droop_move = self.timing_belt_avoid_nozzle - self.timing_belt_end + self.regrip1_distance
    
            self.droop_move = self.droop_length
            if self.droop_move > self.max_droop_move:
                sendNotification(NotificationLevel.INFO, 'Droop Length is too large, overwritten with max droop length for given regrip1: ' +str(self.max_droop_move))
                self.droop_move = self.max_droop_move

            self.regrip1_abs = self.timing_belt_end - self.regrip1_distance
    
            self.max_regrip2_move = self.timing_belt_end - self.regrip1_distance + self.droop_move
    
            self.regrip2_cycles_req = ceil(float(self.regrip2_distance)/self.max_regrip2_move)
            self.regrip2_move = self.regrip2_distance/self.regrip2_cycles_req
    
            self.regrip2_profile = self.findTime(self.regrip2_move, self.regrip2_speed, self.regrip2_accel, self.regrip2_accel)
            
            self.regrip2_stop_time = self.regrip2_profile["stop_time"]
            
            # self.logger.info("regrip2_accel_time " + str(self.__regrip2_accel_time))
            # self.logger.info("regrip2_accel_dist " + str(self.__regrip2_accel_dist))
            # self.logger.info("regrip2_at_speed_dist " + str(self.__regrip2_at_speed_dist))
            # self.logger.info("regrip2_stop_time " + str(self.regrip2_stop_time))
    
            self.track_vehicle_start_pos = (self.timing_belt_end - self.regrip1_distance + self.droop_move - self.regrip2_move)
            self.__regrip2_to_nozzles_dist = self.timing_belt_avoid_nozzle - self.track_vehicle_start_pos
            
            self.track_vehicle_profile = self.findTime(self.__regrip2_to_nozzles_dist, self.vehicle_speed, self.vehicle_accel, self.vehicle_accel)
            
            self.track_vehicle_stop_time = self.track_vehicle_profile["stop_time"]

            self.vehicle_accel_time = self.track_vehicle_profile["accel_time"]
            self.vehicle_accel_dist = self.track_vehicle_profile["accel_dist"]      

            self.hot_wire_profile = self.findTime(self.hot_wire_distance, self.hot_wire_speed, self.hot_wire_accel, self.hot_wire_accel)
            
            self.hot_wire_stop_time = self.hot_wire_profile["stop_time"] 


    def onStop(self):
        '''
        Called when a stop is requested from the REST API. 99% of the time, you will
        simply call 'emitStop' on all of your machine motions in this methiod.
        '''
        sendNotification(NotificationLevel.UI_INFO, 'Stop Event', { 'ui_state': 'Stopped' })
        
        self.mm1.stopContinuousMove(self.nozzle_linear_axis,1000)
        self.mm1.stopContinuousMove(self.timing_belt_axis,1000)
        self.mm3.stopContinuousMove(self.nozzle_rotation_axis,1000)

        self.mm1.emitStop()
        sendNotification(NotificationLevel.UI_INFO, 'Ball Screw Standby', { 'ui_ballscrew_state': 'Standby' })

        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Standby', { 'ui_timingbelt_state': 'Standby' })
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Standby', { 'ui_nozzle_linear_state': 'Standby' })

        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Standby', { 'ui_nozzle_rotation_state': 'Standby' })
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Standby', { 'ui_hotwire_actuator_state': 'Standby' })

        self.hot_wire.low()
        self.air_nozzle.low()

    def onPause(self):
        '''
        Called when a pause is requested from the REST API. 99% of the time, you will
        simply call 'emitStop' on all of your machine motions in this methiod.
        '''
        pass

    def onEstop(self):
        '''
        Called AFTER the MachineMotion has been estopped. Please note that any state
        that you were using will no longer be available at this point. You should
        most likely reset all IOs to the OFF position in this method.
        '''
        notifier = getNotifier()
        notifier.sendMessage(NotificationLevel.UI_INFO, 'EStop Event', { 'ui_state': 'EStopped' })
        
        self.mm1.stopContinuousMove(self.nozzle_linear_axis,1000)
        self.mm1.stopContinuousMove(self.timing_belt_axis,1000)
        self.mm3.stopContinuousMove(self.nozzle_rotation_axis,1000)

        self.mm2.emitStop()
        notifier.sendMessage(NotificationLevel.UI_INFO, 'Ball Screw EStop', { 'ui_ballscrew_state': 'EStop' })
        self.mm1.emitStop()
        notifier.sendMessage(NotificationLevel.UI_INFO, 'Timing Belt EStop', { 'ui_timingbelt_state': 'EStop' })
        notifier.sendMessage(NotificationLevel.UI_INFO, 'Nozzle Linear EStop', { 'ui_nozzle_linear_state': 'EStop' })
        self.mm3.emitStop()
        notifier.sendMessage(NotificationLevel.UI_INFO, 'Nozzle Rotation EStop', { 'ui_nozzle_rotation_state': 'EStop' })
        notifier.sendMessage(NotificationLevel.UI_INFO, 'Hot Wire Actuator EStop', { 'ui_hotwire_actuator_state': 'EStop' })

        self.hot_wire.low()
        self.air_nozzle.low()
        self.air_master.low()

    def onResume(self):
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
        return self.mm1

    def pullWithSensor(self, actuator, sensor, timeout):
        
        actuator.pull()
        
        time.sleep(1)
        
        if not self.sim_enable:
            try:
                if sensor.getState() == 1:
                    return True
                else:
                    sensor.wait_for_rising_edge(timeout) 
                return True
            except (Sensor.timeoutException):
                sendNotification(NotificationLevel.INFO, 'Stopped on sensor timeout', { 'ui_state': 'Error' })
                self.stop()
                return False
        else:
            return True

    def pushWithSensor(self, actuator, sensor, timeout):
        
        actuator.push()
        
        time.sleep(1)
        
        if not self.sim_enable:
            try:
                if sensor.getState() == 1:
                    return True
                else:
                    sensor.wait_for_rising_edge(timeout)
                return True
            except (Sensor.timeoutException):
                sendNotification(NotificationLevel.INFO, 'Stopped on sensor timeout', { 'ui_state': 'Error' })
                self.stop()
                return False
        else:
            return True

class InitializeState(MachineAppState):
    '''
    Check if its first time through, also resets variables for new run.
    '''
    def __init__(self, engine):

        super().__init__(engine)

    def onEnter(self):
        sendNotification(NotificationLevel.UI_INFO, 'Initializing State', { 'ui_state': 'Initialize' })

        sendNotification(NotificationLevel.UI_INFO, 'Ball Screw Standby', { 'ui_ballscrew_state': 'Standby' })
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Standby', { 'ui_timingbelt_state': 'Standby' })
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Standby', { 'ui_nozzle_linear_state': 'Standby' })
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Standby', { 'ui_nozzle_rotation_state': 'Standby' })
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Standby', { 'ui_hotwire_actuator_state': 'Standby' })

        if self.configuration['home']:
            self.gotoState('Home')
        
        elif self.configuration['feed_new_roll']:
            self.gotoState('Feed_New_Roll')
        
        elif self.configuration['remove_material']:
            self.gotoState('Remove_Material')

        else:
            self.engine.regrip2_cycle_count = 0
            # self.gotoState('Move_Ballscrew')
            self.gotoState('Pre_Vehicle_Arrives')

    def update(self):
        pass

class BallScrewState(MachineAppState):
    '''
    Moves Ballscrews into correct position.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        sendNotification(NotificationLevel.UI_INFO, 'Ball Screw State', { 'ui_state': 'Ball Screw' })
        
        self.engine.air_master.high()
        
        # close mobile gripper
        if not self.engine.pushWithSensor(self.engine.mobile_pneumatic, self.engine.mobile_clamped,self.engine.pneumatic_timeout):
            return

        positions = self.engine.mm2.getCurrentPositions()

        if positions[self.engine.ball_screw_axis] != self.engine.ball_screw_pos:

            self.engine.mm2.emitSpeed(self.engine.ball_screw_speed)
            self.engine.mm2.emitAcceleration(self.engine.ball_screw_accel)
            self.engine.mm2.unlockBrake(self.engine.brake1_aux, safety_adapter_presence=True)
            self.engine.mm2.unlockBrake(self.engine.brake2_aux, safety_adapter_presence=True)
            sendNotification(NotificationLevel.UI_INFO, 'Ball Screw Running', { 'ui_ballscrew_state': 'Running' })
            self.engine.mm2.emitAbsoluteMove(self.engine.ball_screw_axis,self.engine.ball_screw_pos)
            self.engine.mm2.waitForMotionCompletion()
            sendNotification(NotificationLevel.UI_INFO, 'Ball Screw Standby', { 'ui_ballscrew_state': 'Standby' })
            self.engine.mm2.lockBrake(self.engine.brake1_aux, safety_adapter_presence=True)
            self.engine.mm2.lockBrake(self.engine.brake2_aux, safety_adapter_presence=True)

        self.gotoState('Initial_Stretch')

    def update(self):
        pass

class InitialStretchState(MachineAppState):
    '''
    Moves plastic across for first time.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        sendNotification(NotificationLevel.UI_INFO, 'Initial Stretch State', { 'ui_state': 'Initial Stretch' })

        # open fixed gripper
        if not self.engine.pushWithSensor(self.engine.fixed_pneumatic, self.engine.fixed_released, self.engine.pneumatic_timeout):
            return

        self.engine.mm3.emitHome(self.engine.nozzle_rotation_axis)
        self.engine.mm3.waitForMotionCompletion()
        self.engine.mm1.emitHome(self.engine.nozzle_linear_axis)

        # drive mobile gripper toward fixed clamp
        self.engine.mm1.emitSpeed(self.engine.timing_belt_speed)
        self.engine.mm1.emitAcceleration(self.engine.timing_belt_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Running', { 'ui_timingbelt_state': 'Running' })
        self.engine.mm1.emitAbsoluteMove(self.engine.timing_belt_axis,self.engine.timing_belt_end)
        self.engine.mm1.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Standby', { 'ui_timingbelt_state': 'Standby' })

        # clamp fixed gripper
        if not self.engine.pullWithSensor(self.engine.fixed_pneumatic, self.engine.fixed_clamped, self.engine.pneumatic_timeout):
            return

        self.gotoState('Regrip1')

    def update(self):
        pass

class Regrip1State(MachineAppState):
    '''
    Moves from fixed pneumatic end to roll end.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):

        sendNotification(NotificationLevel.UI_INFO, 'Return to Roll State', { 'ui_state': 'Return to Roll' })

        # sendNotification(NotificationLevel.UI_INFO, 'Droop Count: ' + str(self.__regrip2_cycle_count) + ' Droop Cycles Req: ' + str(self.__droop_cycles_req), { 'ui_state': 'Return to Roll' })

        # release mobile gripper
        if not self.engine.pullWithSensor(self.engine.mobile_pneumatic, self.engine.mobile_released, self.engine.pneumatic_timeout):
            return

        if not self.engine.pullWithSensor(self.engine.roller_pneumatic, self.engine.return_roller_up, self.engine.pneumatic_timeout):
            return

        # drive mobile gripper toward brake
        # self.engine.mm1.emitSpeed(self.engine.timing_belt_speed)
        # self.engine.mm1.emitAcceleration(self.engine.timing_belt_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Running', { 'ui_timingbelt_state': 'Running' })
        self.engine.mm1.emitAbsoluteMove(self.engine.timing_belt_axis,self.engine.regrip1_abs)
        self.engine.mm1.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Standby', { 'ui_timingbelt_state': 'Standby' })


        # clamp mobile gripper
        if not self.engine.pushWithSensor(self.engine.mobile_pneumatic, self.engine.mobile_clamped, self.engine.pneumatic_timeout):
            return

        if not self.engine.pushWithSensor(self.engine.roller_pneumatic, self.engine.return_roller_down, self.engine.pneumatic_timeout):
            return

        self.gotoState('Droop_Stretch')

    def update(self):
        pass

class DroopStretchState(MachineAppState):
    '''
    Moves material to make droop.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        
        sendNotification(NotificationLevel.UI_INFO, 'Droop Stretch', { 'ui_state': 'Droop Stretch' })

        # drive mobile gripper for droop_move
        # self.engine.mm1.emitSpeed(self.engine.timing_belt_speed)
        # self.engine.mm1.emitAcceleration(self.engine.timing_belt_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Running', { 'ui_timingbelt_state': 'Running' })
        self.engine.mm1.emitRelativeMove(self.engine.timing_belt_axis, "positive", self.engine.droop_move)
        self.engine.mm1.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Standby', { 'ui_timingbelt_state': 'Standby' })

        self.engine.mm3.emitSpeed(15)
        self.engine.mm3.emitAcceleration(self.engine.nozzle_rotation_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Running', { 'ui_nozzle_rotation_state': 'Running' })
        self.engine.mm3.emitAbsoluteMove(self.engine.nozzle_rotation_axis,self.engine.nozzle_rotation_pos1)
        self.engine.mm1.emitSpeed(100)
        self.engine.mm1.emitAcceleration(self.engine.nozzle_linear_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Running', { 'ui_nozzle_linear_state': 'Running' })
        self.engine.mm1.emitAbsoluteMove(self.engine.nozzle_linear_axis,self.engine.nozzle_linear_pos1)
        self.engine.mm3.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Standby', { 'ui_nozzle_rotation_state': 'Standby' })
        self.engine.mm1.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Standby', { 'ui_nozzle_linear_state': 'Standby' })

        self.engine.air_nozzle.high()

        self.gotoState('Vehicle_Arrives')

    def update(self):
        pass
    

class PreVehicleArrivesState(MachineAppState):
    '''
    Dummy state to get timing belt and nozzles into position for Vehicle Arrives State
    Only use when debugging without material
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        sendNotification(NotificationLevel.UI_INFO, 'Pre-Vehicle Arrives State', { 'ui_state': 'Pre-Vehicle Arrives' })

        self.engine.mm1.emitSpeed(self.engine.timing_belt_speed)
        self.engine.mm1.emitAcceleration(self.engine.timing_belt_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Running', { 'ui_timingbelt_state': 'Running' })
        self.engine.mm1.emitAbsoluteMove(self.engine.timing_belt_axis, (self.engine.timing_belt_end - self.engine.regrip1_distance + self.engine.droop_move))
        self.engine.mm1.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Standby', { 'ui_timingbelt_state': 'Standby' })

        self.engine.mm3.emitSpeed(15)
        self.engine.mm3.emitAcceleration(self.engine.nozzle_rotation_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Running', { 'ui_nozzle_rotation_state': 'Running' })
        self.engine.mm3.emitAbsoluteMove(self.engine.nozzle_rotation_axis,self.engine.nozzle_rotation_pos1)
        self.engine.mm1.emitSpeed(100)
        self.engine.mm1.emitAcceleration(self.engine.nozzle_linear_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Running', { 'ui_nozzle_linear_state': 'Running' })
        self.engine.mm1.emitAbsoluteMove(self.engine.nozzle_linear_axis,self.engine.nozzle_linear_pos1)
        self.engine.mm3.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Standby', { 'ui_nozzle_rotation_state': 'Standby' })
        self.engine.mm1.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Standby', { 'ui_nozzle_linear_state': 'Standby' })

        self.gotoState('Vehicle_Arrives')
    
    
    def update(self):
        pass

class VehicleArrivesState(MachineAppState):
    '''
    Do all the things when the vehicle arrives.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        sendNotification(NotificationLevel.UI_INFO, 'Vehicle Arrives State', { 'ui_state': 'Vehicle Arrives' })

        self.T_0 = 0
        self.regrip2_start_time = 0
        self.track_vehicle_start_time = 0
        self.nozzle_to_P2_start_time = 0
        self.nozzle_P2_done_time = 0
        self.nozzle_to_P3_start_time = 0
        self.nozzle_P3_delay_start_time = 0
        self.nozzle_linear_1_2_decel_start_time = 0
        self.nozzle_rotation_1_2_decel_start_time = 0
        self.nozzle_linear_2_3_decel_start_time = 0
        self.nozzle_rotation_2_3_decel_start_time = 0
        self.hot_wire_up_start_time = 0
        self.hot_wire_hold_delay_start_time = 0
        self.hot_wire_down_start_time = 0
        self.mobile_opened_done = False
        self.regrip2_done = False
        self.vehicle_speed_done = False
        self.fixed_opened_done = False
        self.nozzle_P2_started = False
        self.nozzle_P2_done = False
        self.nozzle_P3_started = False
        self.nozzle_P3_done = False
        self.hot_wire_up_done = False
        self.hot_wire_down_started = False
        self.hot_wire_down_done = False
        self.hot_wire_up_started = False
        self.regrip2_cycle_done = False
        self.vehicle_speed_cycle_done = False
        self.nozzle_P3_linear_decel = False
        self.nozzle_P3_rotation_decel = False
        self.nozzle_P2_linear_decel = False
        self.nozzle_P2_rotation_decel = False

        self.timing_belt_check_home = False
        self.timing_belt_check_end = False
        self.nozzle_linear_check_home = False
        self.nozzle_linear_check_end = False
        self.nozzle_rotation_check_home = False
        self.nozzle_rotation_check_end = False
        self.hot_wire_check_home = False
        self.hot_wire_check_end = False


        # wait for vehicle sensor

        if not self.engine.sim_enable:
            try:
                self.engine.vehicle_start.wait_for_rising_edge(1200) 
            except (Sensor.timeoutException):
                sendNotification(NotificationLevel.INFO, 'Stopped on vehicle sensor timeout', { 'ui_state': 'Error' })
                self.engine.stop()

        # Record the time that we entered this state
        self.T_0 = time.time()

        while self.mobile_opened_done == False or self.regrip2_done == False or self.fixed_opened_done == False or self.nozzle_P3_done == False or self.hot_wire_down_done == False:
            
            # self.engine.logger.info("inside while")

            #open mobile gripper after mobile gripper open delay
            if time.time() - self.T_0 >= self.engine.mobile_gripper_open_delay and self.mobile_opened_done == False:

                if not self.engine.pullWithSensor(self.engine.mobile_pneumatic, self.engine.mobile_released, self.engine.pneumatic_timeout):
                    return
                
                if not self.engine.pullWithSensor(self.engine.roller_pneumatic, self.engine.return_roller_up, self.engine.pneumatic_timeout):
                    return

                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_timingbelt_state': 'Running' })
                self.engine.mm1.setContinuousMove(self.engine.timing_belt_axis,-1*self.engine.regrip2_speed,self.engine.regrip2_accel)
                self.timing_belt_check_home = True
                self.regrip2_start_time = time.time()
                self.mobile_opened_done = True
                self.engine.logger.info("mobile_opened_done")

            if time.time() - self.regrip2_start_time >= self.engine.regrip2_stop_time and self.mobile_opened_done == True and self.regrip2_cycle_done == False:
                self.engine.mm1.stopContinuousMove(self.engine.timing_belt_axis,self.engine.regrip2_accel)
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_timingbelt_state': 'Standby' })
                self.timing_belt_check_home = False

                if not self.engine.pushWithSensor(self.engine.mobile_pneumatic, self.engine.mobile_clamped, self.engine.pneumatic_timeout):
                    return

                if not self.engine.pushWithSensor(self.engine.roller_pneumatic, self.engine.return_roller_down, self.engine.pneumatic_timeout):
                    return

                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_timingbelt_state': 'Running' })
                self.engine.mm1.setContinuousMove(self.engine.timing_belt_axis,self.engine.vehicle_speed,self.engine.vehicle_accel)
                self.timing_belt_check_end = True
                self.track_vehicle_start_time = time.time()

                self.regrip2_cycle_done = True
                self.engine.logger.info("regrip2_cycle_done")

            if (((time.time() - self.track_vehicle_start_time >= self.engine.track_vehicle_stop_time and self.regrip2_cycle_done == True) or self.hot_wire_down_started == True) and self.vehicle_speed_cycle_done == False):

                self.engine.mm1.stopContinuousMove(self.engine.timing_belt_axis,1000)
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_timingbelt_state': 'Standby' })
                self.timing_belt_check_end = False
                self.travel_time_with_Vehicle = time.time() - self.track_vehicle_start_time
                if self.travel_time_with_Vehicle >= self.engine.track_vehicle_stop_time:
                    self.vehicle_end_pos = self.engine.timing_belt_avoid_nozzle
                else:
                    self.vehicle_end_pos = self.engine.track_vehicle_start_pos + ((self.engine.vehicle_speed * (self.track_vehicle_start_time - self.engine.vehicle_accel_time)) + self.engine.vehicle_accel_dist)

                self.engine.mm1.setPosition(self.engine.timing_belt_axis, self.vehicle_end_pos)
                self.vehicle_speed_cycle_done = True
                self.engine.logger.info("vehicle_speed_cycle_done")
                self.engine.regrip2_cycle_count += 1
                if self.engine.regrip2_cycle_count >= self.engine.regrip2_cycles_req:
                    self.vehicle_speed_done = True
                    self.regrip2_done = True
                else:
                    self.mobile_opened_done = False
                    self.regrip2_cycle_done = False
                    self.vehicle_speed_cycle_done = False
                    


            #open fixed gripper after fix gripper open delay
            if time.time() - self.T_0 >= self.engine.fix_gripper_open_delay and self.fixed_opened_done == False:

                if not self.engine.pushWithSensor(self.engine.fixed_pneumatic, self.engine.fixed_released, self.engine.pneumatic_timeout):
                    return

                self.fixed_opened_done = True
                self.engine.logger.info("fixed_opened_done")

            # wait for P2 delay, then start moving nozzles to P2
            if time.time() - self.T_0 >= self.engine.nozzle_P2_delay and self.nozzle_P2_started == False:
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_linear_state': 'Running' })
                self.engine.mm1.setContinuousMove(self.engine.nozzle_linear_axis,self.engine.nozzle_speed_linear_1_2,self.engine.nozzle_linear_accel)
                if self.engine.nozzle_speed_linear_1_2 > 0:
                    self.nozzle_linear_check_end = True
                else:
                    self.nozzle_linear_check_home = True

                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_rotation_state': 'Running' })
                self.engine.mm3.setContinuousMove(self.engine.nozzle_rotation_axis,self.engine.nozzle_speed_rotational_1_2,self.engine.nozzle_rotation_accel)
                if self.engine.nozzle_speed_rotational_1_2 > 0:
                    self.nozzle_rotation_check_end = True
                else:
                    self.nozzle_rotation_check_home = True

                self.nozzle_to_P2_start_time = time.time()
                
                self.nozzle_P2_started = True
                self.engine.logger.info("nozzle_P2_started")

            # once nozzles at P2, stop nozzle motion
            if time.time() - self.nozzle_to_P2_start_time >= self.engine.nozzle_linear_1_2_stop_time and self.nozzle_P2_started == True and self.nozzle_P2_linear_decel == False:
                self.engine.mm1.stopContinuousMove(self.engine.nozzle_linear_axis,self.engine.nozzle_linear_accel)
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_linear_state': 'Standby' })
                if self.engine.nozzle_speed_linear_1_2 > 0:
                    self.nozzle_linear_check_end = False
                else:
                    self.nozzle_linear_check_home = False
                self.nozzle_linear_1_2_decel_start_time = time.time()
                self.nozzle_P2_linear_decel = True
                self.engine.logger.info("nozzle_P2_linear_decel")

             # once nozzles at P2, stop nozzle motion
            if time.time() - self.nozzle_to_P2_start_time >= self.engine.nozzle_rotation_1_2_stop_time and self.nozzle_P2_started == True and self.nozzle_P2_rotation_decel == False:
                self.engine.mm3.stopContinuousMove(self.engine.nozzle_rotation_axis,self.engine.nozzle_rotation_accel)
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_rotation_state': 'Standby' })
                if self.engine.nozzle_speed_rotational_1_2 > 0:
                    self.nozzle_rotation_check_end = False
                else:
                    self.nozzle_rotation_check_home = False
                self.nozzle_rotation_1_2_decel_start_time = time.time()
                self.nozzle_P2_rotation_decel = True
                self.engine.logger.info("nozzle_P2_rotation_decel")

            if (time.time() - self.nozzle_linear_1_2_decel_start_time >= self.engine.nozzle_linear_1_2_decel_time and self.nozzle_P2_linear_decel == True) and (time.time() - self.nozzle_rotation_1_2_decel_start_time >= self.engine.nozzle_rotation_1_2_decel_time and self.nozzle_P2_rotation_decel == True) and self.nozzle_P2_done == False:
                self.nozzle_P3_delay_start_time = time.time()
                self.nozzle_P2_done = True
                self.engine.logger.info("nozzle_P2_done")

            # wait for P3 delay, then start moving nozzles to P3
            if time.time() - self.nozzle_P3_delay_start_time >= self.engine.nozzle_P3_delay and self.nozzle_P2_done == True and self.nozzle_P3_started == False:
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_linear_state': 'Running' })
                self.engine.mm1.setContinuousMove(self.engine.nozzle_linear_axis,self.engine.nozzle_speed_linear_2_3,self.engine.nozzle_linear_accel)
                if self.engine.nozzle_speed_linear_2_3 > 0:
                    self.nozzle_linear_check_end = True
                else:
                    self.nozzle_linear_check_home = True

                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_rotation_state': 'Running' })
                self.engine.mm3.setContinuousMove(self.engine.nozzle_rotation_axis,self.engine.nozzle_speed_rotational_2_3,self.engine.nozzle_rotation_accel)
                if self.engine.nozzle_speed_rotational_2_3 > 0:
                    self.nozzle_rotation_check_end = True
                else:
                    self.nozzle_rotation_check_home = True
                
                self.nozzle_to_P3_start_time = time.time()
                self.nozzle_P3_started = True
                self.engine.logger.info("nozzle_P3_started")

            # once nozzles at P3, stop nozzle motion
            if time.time() - self.nozzle_to_P3_start_time >= self.engine.nozzle_linear_2_3_stop_time and self.nozzle_P3_started == True and self.nozzle_P3_linear_decel == False:
                self.engine.mm1.stopContinuousMove(self.engine.nozzle_linear_axis,self.engine.nozzle_linear_accel)
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_linear_state': 'Standby' })
                
                if self.engine.nozzle_speed_linear_2_3 > 0:
                    self.nozzle_linear_check_end = False
                else:
                    self.nozzle_linear_check_home = False
                
                self.engine.mm1.setPosition(self.engine.nozzle_linear_axis,self.engine.nozzle_linear_pos3)
                self.nozzle_linear_2_3_decel_start_time = time.time()
                self.nozzle_P3_linear_decel = True
                self.engine.logger.info("nozzle_P3_linear_decel")

            if time.time() - self.nozzle_to_P3_start_time >= self.engine.nozzle_rotation_2_3_stop_time and self.nozzle_P3_started == True and self.nozzle_P3_rotation_decel == False:
                self.engine.mm3.stopContinuousMove(self.engine.nozzle_rotation_axis,self.engine.nozzle_rotation_accel)
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_rotation_state': 'Standby' })
                
                if self.engine.nozzle_speed_rotational_2_3 > 0:
                    self.nozzle_rotation_check_end = False
                else:
                    self.nozzle_rotation_check_home = False
                
                self.engine.mm3.setPosition(self.engine.nozzle_rotation_axis,self.engine.nozzle_rotation_pos3)
                self.nozzle_rotation_2_3_decel_start_time = time.time()
                self.nozzle_P3_rotation_decel = True
                self.engine.logger.info("nozzle_P3_rotation_decel")

            if (time.time() - self.nozzle_linear_2_3_decel_start_time >= self.engine.nozzle_linear_2_3_decel_time and self.nozzle_P3_linear_decel == True) and (time.time() - self.nozzle_rotation_2_3_decel_start_time >= self.engine.nozzle_rotation_2_3_decel_time and self.nozzle_P3_rotation_decel == True) and self.nozzle_P3_done == False:
                self.nozzle_P3_done = True
                self.engine.logger.info("nozzle_P3_done")

            # hot wire logic
            if time.time() - self.nozzle_to_P3_start_time >= self.engine.hot_wire_on_delay and self.nozzle_P3_started == True and self.hot_wire_up_started == False:
                # hot wire on
                self.engine.hot_wire.high()

                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_hotwire_actuator_state': 'Running' })
                self.engine.mm3.setContinuousMove(self.engine.hot_wire_axis,self.engine.hot_wire_speed,self.engine.hot_wire_accel)
                self.hot_wire_check_end = True


                self.hot_wire_up_start_time = time.time()
                self.hot_wire_up_started = True
                self.engine.logger.info("hot_wire_up_started")

            if time.time() - self.hot_wire_up_start_time >= self.engine.hot_wire_stop_time and self.hot_wire_up_started == True and self.hot_wire_up_done == False:

                self.engine.mm3.stopContinuousMove(self.engine.hot_wire_axis,self.engine.hot_wire_accel)
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_hotwire_actuator_state': 'Standby' })
                self.hot_wire_check_end = False

                self.hot_wire_hold_delay_start_time = time.time()
                self.hot_wire_up_done = True 
                self.engine.logger.info("hot_wire_up_done")

            if time.time() - self.hot_wire_hold_delay_start_time >= self.engine.hot_wire_hold_delay and self.hot_wire_up_done == True and self.hot_wire_down_started == False:

                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_hotwire_actuator_state': 'Running' })
                self.engine.mm3.setContinuousMove(self.engine.hot_wire_axis,-1*self.engine.hot_wire_speed,self.engine.hot_wire_accel)
                self.hot_wire_check_home = True

                self.engine.hot_wire.low()
                self.hot_wire_down_start_time = time.time()
                self.hot_wire_down_started = True 
                self.engine.logger.info("hot_wire_down_started")  

            if time.time() - self.hot_wire_down_start_time >= self.engine.hot_wire_stop_time and self.hot_wire_down_started == True and self.hot_wire_down_done == False:

                self.engine.mm3.stopContinuousMove(self.engine.hot_wire_axis,self.engine.hot_wire_accel)
                sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_hotwire_actuator_state': 'Standby' })
                self.hot_wire_check_home = False

                self.hot_wire_down_done = True 
                self.engine.logger.info("hot_wire_down_done")

            # manually check end sensors for continuos move
            if self.engine.sim_enable == False:
            
                self.mm1_endstops = self.engine.mm1.getEndStopState()
                self.timing_belt_home_sensor = self.mm1_endstops.get('x_min')
                self.timing_belt_end_sensor = self.mm1_endstops.get('x_max')

                if (self.timing_belt_home_sensor.find("TRIGGERED") == 0 and self.timing_belt_check_home == True) or (self.timing_belt_end_sensor.find("TRIGGERED") == 0 and self.timing_belt_check_end == True):
                    self.engine.mm1.stopContinuousMove(self.engine.timing_belt_axis,1000)
                    sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_timingbelt_state': 'Standby' })
                    sendNotification(NotificationLevel.INFO, 'Timing Belt At Sensor')
                    self.engine.logger.info("Timing Belt Sensor")
                
                self.nozzle_linear_home_sensor = self.mm1_endstops.get('z_min')
                self.nozzle_linear_end_sensor = self.mm1_endstops.get('z_max')
            
                if (self.nozzle_linear_home_sensor.find("TRIGGERED") == 0 and self.nozzle_linear_check_home == True) or (self.nozzle_linear_end_sensor.find("TRIGGERED") == 0 and self.nozzle_linear_check_end == True):
                    self.engine.mm1.stopContinuousMove(self.engine.nozzle_linear_axis,1000)
                    sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_linear_state': 'Standby' })
                    sendNotification(NotificationLevel.INFO, 'Nozzle Linear At Sensor')
                    self.engine.logger.info("Nozzle Linear Sensor")

                self.mm3_endstops = self.engine.mm3.getEndStopState()
                self.nozzle_rotation_home_sensor = self.mm3_endstops.get('x_min')
                self.nozzle_rotation_end_sensor = self.mm3_endstops.get('x_max')

                if (self.nozzle_rotation_home_sensor.find("TRIGGERED") == 0 and self.nozzle_rotation_check_home == True) or (self.nozzle_rotation_end_sensor.find("TRIGGERED") == 0 and self.nozzle_rotation_check_end == True):
                    self.engine.mm3.stopContinuousMove(self.engine.nozzle_linear_axis,1000)
                    sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_nozzle_rotation_state': 'Standby' })
                    sendNotification(NotificationLevel.INFO, 'Nozzle Rotation At Sensor')
                    self.engine.logger.info("Nozzle Rotation Sensor")

                self.hot_wire_home_sensor = self.mm3_endstops.get('y_min')
                self.hot_wire_end_sensor = self.mm3_endstops.get('y_max')

                if (self.hot_wire_home_sensor.find("TRIGGERED") == 0 and self.hot_wire_check_home == True) or (self.hot_wire_end_sensor.find("TRIGGERED") == 0 and self.hot_wire_check_end == True):
                    self.engine.mm3.stopContinuousMove(self.engine.hot_wire_axis,1000)
                    sendNotification(NotificationLevel.UI_INFO, ' ', { 'ui_hotwire_actuator_state': 'Standby' })
                    sendNotification(NotificationLevel.INFO, 'Hot Wire At Sensor')
                    self.engine.logger.info("Hot Wire Sensor")

        self.engine.logger.info("out of while")

        self.engine.air_nozzle.low()

        self.engine.mm3.emitSpeed(15)
        self.engine.mm3.emitAbsoluteMove(self.engine.nozzle_rotation_axis,0)
        self.engine.mm3.waitForMotionCompletion()
        self.engine.mm1.emitSpeed(100)
        self.engine.mm1.emitAbsoluteMove(self.engine.nozzle_linear_axis,0)
        self.engine.mm1.waitForMotionCompletion()
        
        self.engine.stop()

    def update(self):
        pass

class FeedNewRollState(MachineAppState):
    '''
    Allow for new roll.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        
        sendNotification(NotificationLevel.UI_INFO, 'Feed New Roll State', { 'ui_state': 'Feed New Roll' })

        # turn off outputs
        self.engine.hot_wire.low()
        self.engine.air_nozzle.low()
        self.engine.air_master.high()

        # open all grippers

        if not self.engine.pullWithSensor(self.engine.mobile_pneumatic, self.engine.mobile_released, self.engine.pneumatic_timeout):
            return
        if not self.engine.pushWithSensor(self.engine.fixed_pneumatic, self.engine.fixed_released, self.engine.pneumatic_timeout):
            return

        # turn air off
        self.engine.air_master.low()

        # Mobile gripper at brake side
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Homing', { 'ui_timingbelt_state': 'Homing' })
        self.engine.mm1.emitHome(self.engine.timing_belt_axis)

        # ball screw all the way up
        self.engine.mm2.unlockBrake(self.engine.brake1_aux, True)
        self.engine.mm2.unlockBrake(self.engine.brake2_aux, True)
        sendNotification(NotificationLevel.UI_INFO, 'Ball Screw Homing', { 'ui_ballscrew_state': 'Homing' })
        self.engine.mm2.emitHome(self.engine.ball_screw_axis)
        self.engine.mm2.waitForMotionCompletion()
        self.engine.mm2.lockBrake(self.engine.brake1_aux, True)
        self.engine.mm2.lockBrake(self.engine.brake2_aux, True)


        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Homing', { 'ui_nozzle_rotation_state': 'Homing' })
        self.engine.mm3.emitHome(self.engine.nozzle_rotation_axis)


        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Homing', { 'ui_nozzle_linear_state': 'Homing' })
        self.engine.mm1.emitHome(self.engine.nozzle_linear_axis)
  
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Homing', { 'ui_hotwire_actuator_state': 'Homing' })
        self.engine.mm3.emitHome(self.engine.hot_wire_axis)
        
        self.engine.mm1.waitForMotionCompletion()
        self.engine.mm3.waitForMotionCompletion()

        self.engine.mm1.triggerEstop()
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Estop', { 'ui_timingbelt_state': 'Estop' })
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Estop', { 'ui_nozzle_linear_state': 'Estop' })
        
        sendNotification(NotificationLevel.UI_INFO, 'Ball Screw Estop', { 'ui_ballscrew_state': 'Estop' })
       
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Estop', { 'ui_nozzle_rotation_state': 'Estop' })
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Estop', { 'ui_hotwire_actuator_state': 'Estop' })

        sendNotification(NotificationLevel.INFO, 'MachineMotions in Estop, ready to install new roll')
        self.engine.stop()

class RemoveMaterialState(MachineAppState):
    '''
    Cuts material and opens fixed gripper.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        
        sendNotification(NotificationLevel.UI_INFO, 'Remove Material State', { 'ui_state': 'Remove Material' })

        # turn on hot wire
        self.engine.hot_wire.high()

        #hot wire axis up
        self.engine.mm3.emitSpeed(self.engine.hot_wire_speed)
        self.engine.mm3.emitAcceleration(self.engine.hot_wire_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Running', { 'ui_hotwire_actuator_state': 'Running' })
        self.engine.mm3.emitAbsoluteMove(self.engine.hot_wire_axis,self.engine.hot_wire_distance)
        self.engine.mm3.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Standby', { 'ui_hotwire_actuator_state': 'Standby' })

        time.sleep(self.engine.hot_wire_hold_delay)

        #hot wire axis down
        self.engine.mm3.emitSpeed(self.engine.hot_wire_speed)
        self.engine.mm3.emitAcceleration(self.engine.hot_wire_accel)
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Running', { 'ui_hotwire_actuator_state': 'Running' })
        self.engine.mm3.emitAbsoluteMove(self.engine.hot_wire_axis,0)
        self.engine.mm3.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Standby', { 'ui_hotwire_actuator_state': 'Standby' })

        self.engine.hot_wire.low()

          # open mobile gripper
        if not self.engine.pullWithSensor(self.engine.mobile_pneumatic, self.engine.mobile_released, self.engine.pneumatic_timeout):
            return

        # open fixed gripper
        if not self.engine.pushWithSensor(self.engine.fixed_pneumatic, self.engine.fixed_released, self.engine.pneumatic_timeout):
            return


        self.engine.mm1.triggerEstop()
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Estop', { 'ui_timingbelt_state': 'Estop' })
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Estop', { 'ui_nozzle_linear_state': 'Estop' })
        
        sendNotification(NotificationLevel.UI_INFO, 'Ball Screw Estop', { 'ui_ballscrew_state': 'Estop' })
        
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Estop', { 'ui_nozzle_rotation_state': 'Estop' })
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Estop', { 'ui_hotwire_actuator_state': 'Estop' })

        sendNotification(NotificationLevel.INFO, 'MachineMotions in Estop, ready to remove material')
        self.engine.stop()

class HomingState(MachineAppState):
    '''
    Takes all axis home.
    '''
    def __init__(self, engine):
        super().__init__(engine)

    def onEnter(self):
        
        sendNotification(NotificationLevel.UI_INFO, 'Homing State', { 'ui_state': 'Homing' })

        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Homing', { 'ui_timingbelt_state': 'Homing' })
        self.engine.mm1.emitHome(self.engine.timing_belt_axis)
        self.engine.mm1.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Timing Belt Home', { 'ui_timingbelt_state': 'Home' })

        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Homing', { 'ui_nozzle_rotation_state': 'Homing' })
        self.engine.mm3.emitHome(self.engine.nozzle_rotation_axis)
        self.engine.mm3.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Rotation Home', { 'ui_nozzle_rotation_state': 'Home' })

        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Homing', { 'ui_nozzle_linear_state': 'Homing' })
        self.engine.mm1.emitHome(self.engine.nozzle_linear_axis)
        self.engine.mm1.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Nozzle Linear Home', { 'ui_nozzle_linear_state': 'Home' })

        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Homing', { 'ui_hotwire_actuator_state': 'Homing' })
        self.engine.mm3.emitHome(self.engine.hot_wire_axis)
        self.engine.mm3.waitForMotionCompletion()
        sendNotification(NotificationLevel.UI_INFO, 'Hot Wire Actuator Home', { 'ui_hotwire_actuator_state': 'Home' })

        self.engine.mm2.unlockBrake(self.engine.brake1_aux, True)
        self.engine.mm2.unlockBrake(self.engine.brake2_aux, True)
        sendNotification(NotificationLevel.UI_INFO, 'Ball Screw Homing', { 'ui_ballscrew_state': 'Homing' })
        self.engine.mm2.emitHome(self.engine.ball_screw_axis)
        self.engine.mm2.waitForMotionCompletion()
        self.engine.mm2.lockBrake(self.engine.brake1_aux, True)
        self.engine.mm2.lockBrake(self.engine.brake2_aux, True)
        sendNotification(NotificationLevel.UI_INFO, 'Ball Screw Home', { 'ui_ballscrew_state': 'Home' })

        sendNotification(NotificationLevel.UI_INFO, 'Home', { 'ui_state': 'Home' })
        sendNotification(NotificationLevel.INFO, 'All axis Home')
        self.engine.stop()
