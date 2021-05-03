# ard_speed_test.py: Arduino Speed Test
# Tests the update speed of the serial connection to an Arduino

from __future__ import division
import time
import serial_port


def speed():
    """Connects to a serial port and times the rate of sample updates"""
    ser = serial_port.SerialPort("/dev/ttyACM0")
    time.sleep(2)
    ser.startReadThread()
    print "Reading..."

    ser.getUpdates()
    nSamples = 100
    for i in range(nSamples):
        time.sleep(1)
        updates = ser.getUpdates()
        print len(updates)
    

if __name__ == "__main__":
    speed()
