from __future__ import division
import time
from serial_port import SerialPort

# Handles communications with the display tablet. Consider that this will
# eventually be a PsychoPy communication mechanism as well!


class Stimbot(SerialPort):
    """Wrapper for the SerialPort class to communicate with the stim tablet"""

    def __init__(self, serialPortName):
        """
        Args:
            serialPortName: COM port that the tablet lives at
        """

        SerialPort.__init__(self, serialPortName)
        Renderer.__init__(self)
        
        # turn screen on, if needed
        time.sleep(0.1) 
        self.write('screenon')        
    
    def setUpCommands(self,commandStrings):
        """

        Args:
            commandStrings: string containing render commands as defined in
            psycho.py

        Returns: Nothing

        """
        # set up stimbot commands for later use
        for i, commandString in enumerate(commandStrings):
            # wait a bit between long commands to make sure serial
            # sends everything
            time.sleep(0.1)
            saveCommand = 'save' + str(i) + ' ' + commandString
            self.write(saveCommand)    


if __name__ == '__main__':
    # Test code
    stimbot = Stimbot('COM92')
    stimbot.setUpCommands(["sx0 sy0", "ac pab sx50 sy50", "as paw sx50 sy50"])
    stimbot.setScreenDistance(100)

    for n in range(0,10):
        for i in range(0,3):
            print "Doing command " + str(i)
            stimbot.write(str(i))
            time.sleep(1)

    print "Done!"
