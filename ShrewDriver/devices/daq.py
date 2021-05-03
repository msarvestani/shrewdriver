# daq.py: Measurement Computing DAQ Interface
# Last Modified: 5 March 2018

# Description: Talks to Measurement Computing DAQ. Configures the USB port,
# converts trigger codes into the correct bit to send the the DAQ, and sends
# stim codes to the DAQ.

from __future__ import division
import sys
import traceback
import time
sys.path.append("..")
from constants.task_constants import *


"""
Talks to the Measurement Computing 1208-FS DAQ
Sends stimcodes to CED/Spike2.
"""


class MccDaq(object):
    
    def __init__(self):
        """
        Returns a Measurement Computing daq object, if possible.
        Returns None otherwise
        """

        self.UL = None
        print "MCC DAQ: Connecting..."
        try:
            import UniversalLibrary as UL
            self.UL = UL
        except ImportError:
            print "Could not open Measurement Computing DAQ. "
            print "Check that the daq is connected. Also, ensure InstaCal " \
                  "and PyUniversalLibrary are installed."
            print "DAQ output will be unavailable for this session."
            traceback.print_exc()
            return
        print "MCC Daq: Success!"

        # DAQ setup
        self.boardNum = 0
        UL.cbDConfigPort(self.boardNum, UL.FIRSTPORTA, UL.DIGITALOUT)
        UL.cbDConfigPort(self.boardNum, UL.FIRSTPORTB, UL.DIGITALOUT)
        
        # trigger bits for frame onset, stim onset, etc
        self.triggerBits = [0, 0, 0, 0, 0, 0, 0, 0]
        # constant telling you which bit tells CED to read the current stimcode
        self.stimcodeReadBit = 0
        # constant telling you which bit is for stim on / off
        self.stimBit = 2
        # constant telling you which bit is for frame flip trigger
        self.frameBit = 3
        
    def send_stimcode(self, stimcode):
        """
        Puts a stimcode on the wires, then flips a bit to tell CED to read the
        code. Stimcode values from 0 to 127 should be fine.
        """

        if self.UL is None:
            # if we didn't open the DAQ, don't do anything here.
            return

        stimNumber = stimcode
        # send stimcode to CED via measurement computing DAQ
        self.UL.cbDOut(self.boardNum, self.UL.FIRSTPORTA, stimNumber)
        
        self.triggerBits[self.stimcodeReadBit] = 1
        self.UL.cbDOut(self.boardNum, self.UL.FIRSTPORTB, self.getTriggerValue())

        # Tell CED to read stimcode and set stim to "on"
        # this costs 1.2ms (+/- 0.1ms).
        self.triggerBits[self.stimcodeReadBit] = 0
        self.triggerBits[self.stimBit] = 1
        self.UL.cbDOut(self.boardNum, self.UL.FIRSTPORTB, self.getTriggerValue())

    def getTriggerValue(self):
        """
        Convert the trigger bits into a number value for output.
        """

        triggerValue = 0
        for i in range(len(self.triggerBits)):
            triggerValue += self.triggerBits[i] * pow(2, i)
        return triggerValue


if __name__ == "__main__":
    daq = MccDaq()
    
    for i in range(10):
        print "sending " + str(i) 
        daq.send_stimcode(i)
        time.sleep(1)
