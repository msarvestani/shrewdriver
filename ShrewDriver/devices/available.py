# available.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 6 March 2018

# Description: Finds available serial ports with peripheral hardware attached.
# On Windows this accesses the hardware registry for video and COM ports
# separately, while on Linux it searches for tty connections. Generally not
# used in shrewdriver, but may be useful for future versions.

from __future__ import division
import sys
import platform
import serial
import serial.tools.list_ports
import glob
import itertools
if platform.platform().startswith('Windows'):
    import _winreg as winreg


def get_serial_ports():
    # Uses the Win32 registry to return a iterator of serial
    # (COM) ports existing on this computer.
    serialPorts = []
    try:
        try:
            serialPath = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, serialPath)
        except WindowsError:
            print "Error reading serial ports. Typically, this means no serial " \
                  "devices are connected."
            return []
        for i in itertools.count():
            try:
                val = winreg.EnumValue(key, i)
                serialPorts.append(val[1])
            except EnvironmentError:
                break
    except OSError:
        serialPorts.append[0]

    return sorted(serialPorts)


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = serial.tools.list_ports.comports()
        ports = [port[0] for port in ports if port[-1] != 'n/a']

    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            print s.name
            s.close()
            result.append(port)
        except serial.SerialException:
            pass
    return result


def get_cameras():
    cameraPath = 'HARDWARE\\DEVICEMAP\\VIDEO'
    cameraIDs = []
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cameraPath)
    except WindowsError:
        raise IterationError
    for i in itertools.count():
        try:
            val = winreg.EnumValue(key, i)
            cameraIDs.append(val)
        except EnvironmentError:
            break
    return cameraIDs


if __name__ == "__main__":
    print serial_ports()
