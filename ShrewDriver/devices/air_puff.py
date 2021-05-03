# Class that controls the air puff Arduino via serial commands.

from __future__ import division
import sys
sys.path.append("..")

from serial_port import SerialPort


class AirPuff:

    def __init__(self, portName):
        """
        Checks to see if a USB port is supplied. If not, returns
        Args:
            portName: path to serial port
        """
        self.ser = None

        if portName is None or portName == "None":
            return

        self.ser = SerialPort(serialPortName=portName, baudRate=57600)
        self.ser.startReadThread()

    def puff(self):
        """Writes the command to cause an air puff to the serial port."""
        if self.ser is None:
            print "No air puff connected."
            return
        self.ser.write("x")

    def open_valve(self):
        """
        Writes the command to open the air puff valve to the serial port.
        Return if no air puff connected.
        """
        if self.ser is None:
            print "No air puff connected."
            return
        self.ser.write("1")

    def close_valve(self):
        """
        Writes the command to close the air puff valve to the serial port.
        Return if no air puff connected.
        """
        if self.ser is None:
            print "No air puff connected."
            return
        self.ser.write("0")


if __name__ == "__main__":
    import time
    airPuff = AirPuff("COM104")  # <--- change to whatever port the air puff is plugged into

    for i in range(10):
        airPuff.puff()
        time.sleep(2)
