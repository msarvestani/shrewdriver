# arduino_sensor.py: ArduinoSensor
# Last Modified: 5 March 2018

# Description:

from __future__ import division
import time
from serial_port import SerialPort


class ArduinoSensor:
    
    def __init__(self, serialPortName):
        """Initializes the ArduinoSensor class using the supplied serial port"""
        self.serialPort = SerialPort(serialPortName)
        self.serialPort.startReadThread()        
        
        # thresholds (reasonable defaults given)
        self.lickThreshold = 1000

        self.tapThreshold = 1000

        self.irThreshold = 100
        
        # sensor state variables
        self._lick = False
        self._tap = False
        
        # sensor history entries are tuples of (booleanState, timestamp).
        self.historyLick = []
        self.historyTap = []
        
        # sensor data, not really used except for debugging
        self.lickRaw = []
        self.tapRaw = []
        
        # reference to objects we need to talk to
        self.task = None
        self.tracer = None

    def checkSensors(self):
        """
        Searches incoming serial updates from the sensors for new levels and
        event types

        Returns: tuple containing updated event history and timestamp
        """
        # Read from serial
        updates = self.serialPort.getUpdates()        

        # Add sensor data to log
        for update in updates:
            (data, t) = update
            # separate the incoming data at the spaces
            toks = data.rstrip().split()
            if len(toks) < 2 or not toks[1].isdigit:
                continue
            try:
                # Read sensor level
                level = int(toks[1])
                if toks[0] == "L":
                    self.lickRaw.append((level, t))
                    self.reportChange("lick " + str(level), t)
                    self.set_lick_state(level, t)
                if toks[0] == "R":
                    self.tapRaw.append((level, t))
                    self.reportChange("tap " + str(level), t)
                    self.set_tap_state(level, t)
            except:
                continue
        
        # parse / update state as needed
        for update in updates:
            (evt, t) = update
            
            if evt == "LEFTLx":
                self.lick = True
                self.historyLick.append(update)
            elif evt == "LEFTLo":
                self.lick = False
                self.historyLick.append(update)
            elif evt == "RIGHTLx":
                self.tap = True
                self.historyTap.append(update)
            elif evt == "RIGHTLo":
                self.tap = False
                self.historyTap.append(update)
       
        return updates
    
    def set_lick_state(self, level, t):
        """
        Sets the state of the lick sensor.
        If the state has changed (crossed threshold), change the state and note
        it in the log. Called from self.checkSensors()

        Args:
            level: [int] level of the arduino sensor
            t: [float] timestamp
        """
        if not self.lick and level > self.lickThreshold:
            self.lick = True
            self.historyLick.append(("LEFTLx", t))
                
        elif self.lick and level < self.lickThreshold:
            self.lick = False
            self.historyLick.append(("LEFTLo", t))

    def set_tap_state(self, level, t):
        """
        Sets the state of the tap sensor.
        If the state has changed (crossed threshold), change the state and note
        it in the log. Called from self.checkSensors()

        Args:
            level: [int] level of the arduino sensor
            t: [float] timestamp
        """
        if not self.tap and level > self.tapThreshold:
            self.tap = True
            self.historyTap.append(("RIGHTLx", t))
        elif self.tap and level < self.tapThreshold:
            self.tap = False
            self.historyTap.append(("RIGHTTo", t))

    def reportChange(self, evt, timestamp):
        """
        Reports lick and tap events to the task.
        Sends sensor readings to tracer. Called from self.checkSensors()

        Args:
            evt: [str] event type
            timestamp: [float] timestamp
        """

        if self.task is not None:
            self.task.notify(evt, timestamp)
            
        if self.tracer is not None:
            self.tracer.notify(evt, timestamp)
        
    '''
    Properties. All setters call reportChange().
    '''
    @property
    def lick(self):
        return _lick
    
    @lick.setter
    def lick(self, value):
        self._lick = value
        if self._lick:
            self.reportChange("LEFTLx", time.time())
        else:
            self.reportChange("LEFTLo", time.time())

    @property
    def tap(self):
        return _tap
    
    @tap.setter
    def tap(self, value):
        self._tap = value
        if self._tap:
            self.reportChange("RIGHTLx", time.time())
        else:
            self.reportChange("RIGHTLo", time.time())
                
    '''
    OK, now we have some boolean functions.
    These are used by CauseEffect objects, which poll sensor states to 
    determine task progression.
    '''
    
    # lick sensor   
    def isLicking(self):
        return self.lick

    def isNotLicking(self):
        return not self.lick
    
    def isTapping(self):
        return self.tap

    def isNotTapping(self):
        return not self.tap    
    
    def hasLickedSince(self, secondsAgo):
        """
        checks whether there was a recent lick (no more than secondsAgo)

        Args:
            secondsAgo: [float] time since last lick

        Returns: [Boolean] if currently licking or has never licked
                 [Boolean] if last lick occurred within secondsAgo

        """
        if self.isLicking:
            # is licking right now
            return True
        
        if len(self.historyLick) == 0:
            # never licked
            return False
        
        # last event must have been an offset; check when it happened
        (state, lickOffsetTime) = self.historyLick[-1]
        return (time.time() - lickOffsetTime) <= secondsAgo
    
    def hasNotLickedSinceAtLeast(self, secondsAgo):
        return not hasLickedSince(self, secondsAgo)
    
    
if __name__ == "__main__":
    ardSensor = ArduinoSensor("COM100")
    ardSensor.debug = True

    import sys
    sys.path.append('..')
    from ui import launch
    from ui import tracer

    tracer = tracer.Tracer()
    
    def add_data(qtThread):
        # called once PyQt is running. Reads data and sends it to PyQt.
        print "Reading data"
        
        tracer.sig_add_trace.emit("Lick")  
        tracer.sig_add_trace.emit("Tap")     

        tracer.sig_set_threshold.emit("Lick", ardSensor.lickThreshold)  
        tracer.sig_set_threshold.emit("Tap", ardSensor.tapThreshold)        

        li = 0
        ti = 0
        while True:
            updates = ardSensor.checkSensors()
            for update in updates:
                (data, t) = update
                toks = data.rstrip().split()
                if len(toks) < 2 or not toks[1].isdigit:
                    continue
                try:
                    level = int(toks[1])
                    if toks[0] == "L":
                        tracer.sig_add_data.emit("Lick", li, level)
                        li += 1
                    if toks[0] == "R":
                        tracer.sig_add_data.emit("Tap", ti, level)
                        ti += 1
                except:
                    continue
                
            time.sleep(0.01)

    launch.start_pyqt(add_data)
