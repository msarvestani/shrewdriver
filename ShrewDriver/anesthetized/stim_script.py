from __future__ import division
import sys
from collections import deque
import os
import time
import pickle
import datetime
from scipy.io import savemat
sys.path.append("..")

"""
Used in anesthetized imaging to display the visual stimuli of behavior trials.
"""


class StimScript(object):

    def __init__(self, events=None, stimDevice=None, daq=None):
        """
        Events is a list of StimEvent objects.

        Args:
            events: list of stimulus events; defaults to None
            stimDevice: port at which stimulus device is located. Defaults to None
            daq: port at which DAQ is lcoated. Defaults to None.
        """

        if events is None:
            print "Supply a list of StimEvents"

        self.events = deque(events)

        self.stimDevice = stimDevice

        self.daq = daq

    def run(self):
        """
        Post screen command, wait, post another.
        """

        tStart = time.clock()
        totalEvents = len(self.events)
        lastPercentDone = -10

        while len(self.events) > 0:
            tElapsed = time.clock()
            if tElapsed >= self.events[0].startTime:
                # event is ready, pop it and execute it
                e = self.events.popleft()
                self.stimDevice.write(e.command)
                if self.daq is not None:
                    self.daq.send_stimcode(e.stimcode)
            else:
                # print progress
                eventsDone = totalEvents - len(self.events)
                percentDone = int(round(eventsDone / totalEvents * 100))
                if percentDone >= lastPercentDone + 10:
                    lastPercentDone += 10
                    print str(eventsDone) + " / " + str(totalEvents) + " (" + str(percentDone) + "% done)"

                # wait a bit and recheck
                time.sleep(0.005)

    def save(self):
        """Saves data in a new directory based on date, exp. number, etc."""
        baseDir = r"C:\ShrewData_Anesthetized"
        dateStr = str(datetime.date.today())

        dateDir = baseDir + os.sep + dateStr
        if not os.path.exists(dateDir):
            os.makedirs(dateDir)

        for i in range(1, 10000):
            sessionStr = str(i).zfill(4)
            experimentDir = dateDir + os.sep + sessionStr
            if not os.path.exists(experimentDir):
                os.makedirs(experimentDir)
                outFilePathPkl = experimentDir + os.sep + sessionStr + ".pkl"
                outFilePathMat = experimentDir + os.sep + sessionStr + ".mat"
                pickle.dump(self.events, open(outFilePathPkl, 'wb'))
                savemat(outFilePathMat, {'events': self.events})

                print "Saved settings to " + outFilePathPkl + " and " + outFilePathMat
                break


class StimEvent(object):

    def __init__(self, startTime=0, command="", stimcode=0):
        self.startTime = startTime
        self.command = command
        self.stimcode = stimcode
