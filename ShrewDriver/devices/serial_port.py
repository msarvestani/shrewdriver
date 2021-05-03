from __future__ import division
import sys
import serial
import time
import re
import threading
import copy


class SerialPort(object):
    """
    This class talks to an Arduino and reads the raw data from it, adding
    timestamps. This data is read by both the training program and the live
    plotting display. SerialPort accepts write commands from the training
    program to command the stimulus tablet.
    """
    
    # Don't forget to call startReadThread()!
    
    def __init__(self, serialPortName, baudRate=57600):
        # serial port setup
        self.serialPortName = serialPortName
        # self.serialPortName = int(serialPortName[3:])-1  # <--- Workaround for serial port oddities in old versions of pyserial.

        # All devices in lab standardize on 57600. If device isn't responding,
        # make sure you're not set to 9600.
        self.baudRate = baudRate
        print "Opening serial port [" + serialPortName + "] at " + str(self.baudRate) 
        sys.stdout.flush()
        self.ser = serial.Serial(self.serialPortName, self.baudRate, timeout=5)
        self.updates = []
        self.threadLock = threading.Lock()
        
        self.startTimeMillis = time.time()*1000
        
        self.stopFlag = False
        # prevents polling thread from eating up all the CPU
        self.SLEEP_TIME = 0.0001
        
    def getUpdates(self):
        # returns all of the raw text received since the last poll.
        updatesToReturn = self.updates
        with self.threadLock:
            self.updates = []
        return updatesToReturn
    
    def readSerial(self):
        b = ''
        while b == '' and not self.stopFlag:
            try:
                b = self.ser.readline()
            except:
                # Catch the extremely rare and useless exception:
                # serial.serialutil.SerialException: ReadFile failed
                # (WindowsError(0, 'The operation completed successfully.'))
                # Reportedly this is a bug in the library. Ugh.
                b = ''
                continue
        return b
    
    def readData(self):
        while not self.stopFlag:
            time.sleep(self.SLEEP_TIME)
            data = self.readSerial()
            t = time.time()  # all incoming messages get timestamped
            byteStr = str(data).rstrip()
            if byteStr != '' and byteStr != '\n': 
                with self.threadLock:
                    self.updates.append((byteStr, t))
    
    def close(self):
        self.stopFlag = True
        time.sleep(0.1)
        self.ser.close()
    
    def write(self, command):
        with self.threadLock:
            cmd = command.rstrip() + "\n"  # ensure newline
            self.ser.write(cmd)
    
    def startReadThread(self):
        self.stopFlag = False
        thread = threading.Thread(target=self.readData)
        thread.daemon = True
        thread.start()
