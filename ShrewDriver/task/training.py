from __future__ import division
import sys
import time
import threading
import subprocess
from platform import platform

sys.path.append("..")

from devices.serial_port import SerialPort
from devices.air_puff import AirPuff
from devices.daq import MccDaq
from devices.psycho import *
from devices.opto_generator import *

from util.enumeration import *
from util.serialize import *
from constants.task_constants_2AFC import *

from sequencer.sequencer_base import *

from task.task_generic_1port import *
from task.task_generic_2port import *
from task.task_generic_2port_alt import *
from task.task_gonogo import *
from task.task_2AFC import*
from task.task_2AFC_OpenEnd import *
from task.task_mixin import *
from task.trial import *
from task.task_gonogo_earlyLick import *

from ui.live_plot_2AFC import *
from ui.live_plot import *
from shrewdriver import *

from analysis.generic_analysis import *
from analysis.gonogo_analysis import *
from analysis.twoafc_analysis import*
from analysis.twoafc_openend_analysis import *

'''
Training.py is the control center. 
It also controls live plotting, analysis, and camera recording.
'''


class Training:
    
    def __init__(self, shrewDriver):

        # Set stop flag for threads
        self.stopFlag = False

        # Inherit the shrewdriver class variables
        self.shrewDriver = shrewDriver

        # start live plotting (based on task type)
        if self.shrewDriver.taskType.startswith('2'):
            self.livePlot = LivePlot_2AFC(self.shrewDriver.animalName)
        else:
            self.livePlot = LivePlot_GNG(self.shrewDriver.animalName)

        # start camera - both eye tracking camera and observation webcam
        self.behaviorCameraReader = None
        self.start_observation_camera()

        # start eye tracking
        self.fitPreview = None          # dummy
        if self.shrewDriver.eyeCameraID != "None":
            sys.stdout.flush()
            self.fitPreview = subprocess.Popen([sys.executable, 'ui/preview_fit.py',
                                                '--called'],
                                                cwd=self.shrewDriver.workingDir)

        # set up opto controller, if needed
        if self.shrewDriver.useOpto:
            # Talk to the subprocess through pipes
            self.optoController = LedController(cwd=self.shrewDriver.workingDir)
            self.optoController.start()
            time.sleep(1)

        # start daq, if any
        self.daq = MccDaq()

        # start sensor serial
        print("sensors " + str(self.shrewDriver.sensorPortName))
        self.sensorSerial = SerialPort(self.shrewDriver.sensorPortName)
        self.sensorSerial.startReadThread()

        # start syringe serials, depending on task
        if self.shrewDriver.taskType.startswith('2'):
            # start left syringe pump serial
            self.leftsyringeSerial = SerialPort(self.shrewDriver.leftsyringePortName)
            self.leftsyringeSerial.startReadThread()

            # start right syringe pump serial
            self.rightsyringeSerial = SerialPort(self.shrewDriver.rightsyringePortName)
            self.rightsyringeSerial.startReadThread()

        else:
            self.syringeSerial = SerialPort(self.shrewDriver.leftsyringePortName)

        # start air puff serial, if any
        self.airPuff = None
        if self.shrewDriver.airPuffPortName is not None:
            self.airPuff = AirPuff(self.shrewDriver.airPuffPortName)

        # start stim serial
        movie_dir = self.shrewDriver.moviePath
        # We pass the animal-specific base directory to psychopy
        if self.shrewDriver.stimPortName == "PsychoPy":
            # If we're upstairs, use PsychoPy to render stims
            sys.stdout.flush()
            time.sleep(5)  # lets users drag windows around.
            self.stimDevice = Psycho(windowed=False, movie_dir=movie_dir)
            self.stimDevice.start()
        else:
            self.stimDevice = SerialPort(self.shrewDriver.stimPortName)
            self.stimDevice.startReadThread()

        # set up task
        if (self.shrewDriver.animalName == 'Generic' and
                self.shrewDriver.taskType == '2 port'):
            self.task = TaskGeneric_2port(self, shrewDriver)

        elif (self.shrewDriver.animalName == 'Generic' and
              self.shrewDriver.taskType == '2 port alt'):
            # ask user to enter the number of licks one on side before
            # alternating to next rewarded port
            try:
                self.shrewDriver.alternate_n = int(raw_input("Enter number of "
                                                             "unilateral licks "
                                                             "before alternating:"))
            except ValueError:
                self.shrewDriver.alternate_n = 1

            print self.shrewDriver.alternate_n
            self.task = TaskGeneric_2port_alt(self, shrewDriver)

        elif (self.shrewDriver.animalName == 'Generic' and
              self.shrewDriver.taskType == '1 port'):
            self.task = TaskGeneric_1port(self, shrewDriver)
        elif self.shrewDriver.taskType == 'Go-no-Go':
            self.task = TaskGNG(self, shrewDriver)
        elif self.shrewDriver.taskType =='Go-no-Go Early':
            self.task = TaskGNG_EL(self, shrewDriver)
        elif self.shrewDriver.taskType == '2AFC':
            self.task = Task2AFC(self, shrewDriver)
        elif self.shrewDriver.taskType == '2AFC_OE':
            self.task = Task2AFCOpenEnd(self, shrewDriver)

        # make interact window, if needed
        if hasattr(self.task, "showInteractUI") and self.task.showInteractUI:
            self.shrewDriver.show_interact_ui(self.task)

        # start file logging
        self.logFilePath = self.shrewDriver.experimentPath + \
                           self.shrewDriver.sessionFileName + "_log.txt"
        self.logFile = open(self.logFilePath, 'w')
        
        # make the live data analyzer
        if (self.shrewDriver.animalName == "Generic" and
                self.shrewDriver.taskType.startswith('2')):
            self.analyzer = GenericAnalysis_2port(logFile=None,
                                    settingsFile=self.task.settingsFilePath)

        elif (self.shrewDriver.animalName == 'Generic' and
                self.shrewDriver.taskType.startswith('1')):
            self.analyzer = GenericAnalysis_1port(logFile=None,
                                    settingsFile=self.task.settingsFilePath)

        elif (self.shrewDriver.taskType == 'Go-no-Go' or
              self.shrewDriver.taskType == 'Go-no-Go Early'):
            self.analyzer = GNGAnalysis(logFile=None,
                                    settingsFile=self.task.settingsFilePath)

        elif self.shrewDriver.taskType == '2AFC_OE':
            self.analyzer = TwoAFCOpenEndAnalysis(logFile=None,
                                    settingsFile=self.task.settingsFilePath)

        else:
            self.analyzer = TwoAFCAnalysis(logFile=None,
                                    settingsFile=self.task.settingsFilePath)

        # turn screen on, if needed
        time.sleep(0.1) 
        self.stimDevice.write('screenon\n')
    
    def main_loop(self):
        """Called by start(). This runs in a separate thread so that it can
        update rapidly without blocking."""
        while not self.stopFlag:
            # check serial
            updates = self.sensorSerial.getUpdates()
            for update in updates:
                self.process_updates(update)

            # update state
            self.task.check_state_progression()
            self.livePlot.sigUpdate.emit()

            # get results from other serial threads
            # Prevents potential serial buffer overflow bugs
            bunchaCrap = self.stimDevice.getUpdates()
            if self.shrewDriver.taskType.startswith('2'):
                bunchaCrap = self.leftsyringeSerial.getUpdates()
                bunchaCrap = self.rightsyringeSerial.getUpdates()
            else:
                bunchaCrap = self.syringeSerial.getUpdates()

            if self.shrewDriver.useOpto:
                bunchaCrap = self.optoController.getUpdates()
            # Don't do anything with that information because it's crap

    def process_updates(self, update):
        """
        Args:
            update: text from lick sensor serial port

        Returns: Nothing

        Parses the event type (Lick On/Off, etc.) from the lick/tap sensor and
        sends the information to the task and plotting functions.

        Called by main_loop()
        """
        evtType = update[0]
        timestamp = float(update[1])
        self.task.sensor_update(evtType, timestamp)
        self.log_plot_and_analyze(evtType, timestamp)

    def log_plot_and_analyze(self, eventType, timestamp):
        """
        Args:
            eventType: Code from lick sensors
            timestamp: time in msec

        Returns: Nothing

        Called by process_updates(). Signals events to the live plotter, writes
        the event to the log file, and runs analysis for live stats.
        """
        self.livePlot.sigEvent.emit(eventType, timestamp)
        line = eventType + " " + str(timestamp) + "\n"
        self.logFile.write(line)
        self.analyzer.process_line(line)

    def dispense_hint(self, rewardMillis):
        """
        Args:
            rewardMillis: milliliters of liquid to give as hint

        Returns: Nothing.

        Logs the delivery, time, and bolus amount for a hint
        """
        timestamp = time.time()
        self.daq.send_stimcode(STIMCODE_HINT)
        self.log_plot_and_analyze("RL", timestamp)
        self.log_plot_and_analyze("hint:" + str(rewardMillis), + timestamp)
        self.syringeSerial.write(str(int(rewardMillis * 1000)) + "\n")

    def dispense_hint_left(self, rewardMillis):
        """
        Args:
            rewardMillis: milliliters of liquid to give as hint

        Returns: Nothing.

        Logs the delivery, time, and bolus amount for a hint to the left syringe
        """
        timestamp = time.time()
        self.daq.send_stimcode(STIMCODE_HINT_LEFT)
        self.log_plot_and_analyze("LeftRL", timestamp)
        self.log_plot_and_analyze("left_hint:" + str(rewardMillis), + timestamp)
        self.leftsyringeSerial.write(str(int(rewardMillis * 1000)) + "\n")

    def dispense_hint_right(self, rewardMillis):
        """
        Args:
            rewardMillis: milliliters of liquid to give as hint

        Returns: Nothing.

        Logs the delivery, time, and bolus amount for a hint to the right syringe
        """
        timestamp = time.time()
        self.daq.send_stimcode(STIMCODE_HINT_RIGHT)
        self.log_plot_and_analyze("RightRL", timestamp)
        self.log_plot_and_analyze("right_hint:" + str(rewardMillis), + timestamp)
        self.rightsyringeSerial.write(str(int(rewardMillis * 1000)) + "\n")

    def dispense_reward(self, rewardMillis):
        """
        Args:
            rewardMillis: [float] milliliters of liquid to give as reward

        Returns: Nothing.

        Logs the delivery, time, and bolus amount for a reward
        """
        timestamp = time.time()
        self.daq.send_stimcode(STIMCODE_CORRECT_REWARD)
        self.log_plot_and_analyze("RH", timestamp)
        self.log_plot_and_analyze("bolus:" + str(rewardMillis), timestamp)
        self.syringeSerial.write(str(int(rewardMillis*1000)) + "\n")

    def dispense_reward_left(self, rewardMillis):
        """
        Args:
            rewardMillis: [float] milliliters of liquid to give as reward

        Returns: Nothing.

        Logs the delivery, time, and bolus amount for a reward to the left syringe
        """
        timestamp = time.time()
        self.daq.send_stimcode(STIMCODE_CORRECT_REWARD_LEFT)
        self.log_plot_and_analyze("LeftRH", timestamp)
        self.log_plot_and_analyze("left_bolus:" + str(rewardMillis), timestamp)
        self.leftsyringeSerial.write(str(int(rewardMillis*1000)) + "\n")

    def dispense_reward_right(self, rewardMillis):
        """
        Args:
            rewardMillis: milliliters of liquid to give as reward

        Returns: Nothing.

        Logs the delivery, time, and bolus amount for a reward to the right syringe
        """
        timestamp = time.time()
        self.daq.send_stimcode(STIMCODE_CORRECT_REWARD_RIGHT)
        self.log_plot_and_analyze("RightRH", timestamp)
        self.log_plot_and_analyze("right_bolus:" + str(rewardMillis), timestamp)
        self.rightsyringeSerial.write(str(int(rewardMillis*1000)) + "\n")

    def black_screen(self):
        """Writes to the standard input stream of the stim device, usually
        devices.psycho, to black out the screen when the program is killed"""
        # used by "stop recording" to black out screen at end of experiment
        self.stimDevice.write('as pab px0 py0 sx999 sy999\n')
        time.sleep(0.05)
        self.stimDevice.write('screenoff\n')
        self.daq.send_stimcode(STIMCODE_BLACK_SCREEN)

    def stop(self):
        """Cleanup function called when ending training. Closes the log file,
        kills the observation camera thread if needed, stops the eye tracking
        subprocess if needed, closes the stimulus, and shuts down the serial
        connection to syringe pumps, air puff, and lick sensors."""

        # end logfile
        self.logFile.close()

        # close camera
        self.stop_camera()

        # kill subprocess
        if self.fitPreview is not None:
            self.fitPreview.terminate()

        # stop training thread and reset screen
        self.stopFlag = True
        time.sleep(0.01)
        self.black_screen()
        time.sleep(0.5)
        
        # stop serial threads for syringe pumps, air puff, and stim
        if self.shrewDriver.taskType.startswith('2'):
            self.leftsyringeSerial.close()
            self.rightsyringeSerial.close()
        else:
            self.syringeSerial.close()

        self.sensorSerial.close()
        self.stimDevice.close()

        if self.airPuff is not None:
            self.airPuff.ser.close()

    def start(self):
        """Starts the task analysis thread and begins the update processing
        thread found in self.main_loop()"""
        self.stopFlag = False
        self.task.start()
        
        # threading /  main loop stuff goes here
        thread = threading.Thread(target=self.main_loop)
        thread.daemon = True
        thread.start()

    def start_observation_camera(self):
        """begin live view from webcam """

        # get UI information from shrewdriver
        self.observationCameraID = self.shrewDriver.observationCameraID

        # set up observation camera - this video isn't saved
        if self.observationCameraID != "None":
            vidPath = self.shrewDriver.experimentPath + self.shrewDriver.sessionFileName + '_obs.avi'

            try:
                print "Trying to start observation camera"
                self.behaviorCameraReader = CameraReader(int(self.observationCameraID),
                                                         self.shrewDriver.animalName,
                                                         vidPath=vidPath)
                self.behaviorCameraReader.startReadThread()
                print "Behavior camera started"

            except:
                print "Couldn't start observation camera."
                traceback.print_exc()

        else:
            print "No observation camera selected."

    def stop_camera(self):
        """ Throws flag to stop any camera threads"""

        if self.behaviorCameraReader is not None:
            self.behaviorCameraReader.stopFlag = True
