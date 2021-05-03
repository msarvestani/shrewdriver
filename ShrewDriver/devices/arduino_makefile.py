# Arduino Upload: arduino_makefile.py
# Author: Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Created: 10/23/2017
# Last Modified: 5 March 2018

# Description: Class to create a makefile and call a subprocess to compile and
# upload Arduino code on the fly. Requires the mkarduino package on Linux and
# Windows machines.

from __future__ import print_function
import subprocess
import time
import os
import sys


class ArduinoUpload:

    def __init__(self, arduino_dir_path, port, **kwargs):
        """
        Sets up command line arguments used by mkarduino to compile and load
        Arduino sketches via the command line and write the corresponding
        makefile.

        Args:
            arduino_dir_path: path to the directory containing the Arduino sketch
            port: COM port where the Arduino is located
            **kwargs: 'baudrate' - change the speed of the serial connection
                      'board' - change the board type (i.e. uno, mega)
        """
        self.arduino_dir_path = arduino_dir_path
        baudrate = kwargs.get('baudrate', 57600)
        board_type = kwargs.get('board', 'uno')

        # write a makefile that incorporates the correct information for the
        # current file
        self.makefilename = arduino_dir_path + os.sep + 'Makefile'
        with open(self.makefilename, 'w') as mf:
            mf.write('ARDUINO_DIR = /usr/share/arduino\n')
            mf.write('ARDUINO_PORT = ' + str(port) + '\n')
            mf.write('USER_LIB_PATH = /home/fitzlab1/arduino-1.8.3/libraries\n')
            mf.write('BOARD_TAG = ' + board_type + '\n')
            mf.write('MONITOR_BAUDRATE = ' + str(baudrate) + '\n')
            mf.write('include /usr/share/arduino/Arduino.mk\n')

    def compileAndUpload(self):
        """Runs the make upload clean commands to compile, upload, and cleanup
        the directory containing the Arduino sketch."""
        # create string of commands to send to the shell
        while not os.path.isfile(self.makefilename):
            time.sleep(0.001)
        cmds = ['make', 'upload', 'clean']
        rc = self.rc_run_cmd_basic(cmds)
        if rc == 0:
            print('Successfully uploaded Arduino code!')
        else:
            print('Upload to Arduino failed!')

    # The following code taken from user steveha found at
    # https://stackoverflow.com/questions/8529390/is-there-a-quiet-version-of-subprocess-call
    def rc_run_cmd_basic(self, lst_cmd, verbose=False, silent=False):
        """

        Args:
            lst_cmd: string of the most recent command to execute
            verbose: boolean indicating if logging is desired
            silent: boolean indicating if you want to show all mkarduino output

        Returns: Code indicating success of compilation and upload.

        """

        def prn(*args, **kwargs):
            """
            prn(value, ..., sep=' ', end='\\n', file=sys.stdout)
            Works just like the print function in Python 3.x but can be used in 2.x.

            Prints the values to a stream, or to sys.stdout by default.
            Optional keyword arguments:
            file: a file-like object (stream); defaults to the current sys.stdout.
            sep:  string inserted between values, default a space.
            end:  string appended after the last value, default a newline.
            """
            sep = kwargs.get("sep", ' ')
            end = kwargs.get("end", '\n')
            file = kwargs.get("file", sys.stdout)

            s = sep.join(str(x) for x in args) + end
            file.write(s)

        if silent and verbose:
            raise ValueError("Cannot specify both verbose and silent as true")

        # Create subprocess to run the commands
        p = subprocess.Popen(lst_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, cwd=self.arduino_dir_path)
        # Establish communication with the subprocess.
        tup_output = p.communicate()

        s_cmd = ' '.join(lst_cmd)
        if verbose:
            prn()
            prn("command: '%s'\n" % s_cmd)

            if 0 != p.returncode:
                prn()
                prn("Command failed with code %d:" % p.returncode)
            else:
                prn("Command succeeded!  code %d" % p.returncode)
        if verbose:
            prn("Output for: " + s_cmd)
            prn(tup_output[0])
            prn()
        if not silent and 0 != p.returncode:
            prn("Error output for: " + s_cmd)
            prn(tup_output[1])
            prn()

        return p.returncode


if __name__ == '__main__':
    ardUp = ArduinoUpload('/home/fitzlab1/Desktop/Blink', '/dev/ttyACM0')
    ardUp.compileAndUpload()
