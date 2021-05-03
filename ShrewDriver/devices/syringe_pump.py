# syringe_pump.py: Syringe Pump interface
# Last Modified: 5 March 2018

# Description: Wrapper for the SerialPort class to interface with the syringe
# pumps. Simply increments the bolus and logs the total reward delivered.

from __future__ import division
from serial_port import SerialPort


class SyringePump(SerialPort):
    """Wraps the SerialPort class"""
    
    def __init__(self, serialPortName):
        """Initializes the SyringePump class using the supplied serial port"""
        super(SyringePump, self).__init__(serialPortName)
        self.total_mL = 0
    
    def bolus(self, mL):
        """
        Writes the bolus amount to the serial port in mL. Increments the
        counter for total reward delivered.
        """
        self.write(str(mL*1000) + "\n")
        self.total_mL += mL

        # self.serialPort = SerialPort(serialPortName)
        # self.serialPort.startReadThread()
        
        # self.dispensed_mL = 0
    
    # def bolus(self, amount):
        # pass
