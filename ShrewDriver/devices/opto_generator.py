#!/usr/bin/env python

# opto_generator.py: Waveform Generator for Optogenetics
# Author: Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Created: 10/30/2017
# Last Modified: 12/20/2017

# Description: A GUI to set a waveform for optogenetic stimulation. Users can define the
# amplitude, duration, wave type, ramp up/ramp down, isi. A preview of the wave is displayed in the GUI.
# Method class for controlling a measurement computing USB-1208FS DAQ.
# Waveforms are generated as composite functions of sustained voltage, linear ramps, and sinusoidal ramps
# The user can pass the specific analog out channel used to control multiple LEDs from the same DAQ

from __future__ import division, print_function
import os
import re
import sys
import time
import inspect
import threading
import subprocess
import platform
from math import cos, pi
from psychopy import core
from collections import deque
from PyQt4 import QtCore, QtGui, uic
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

sys.path.append('..')

# # load the .ui files
if sys.argv[-1] == '--called':
    # load the .ui files
    sys.path.append(os.getcwd())
    opto_class = uic.loadUiType("ui/opto_generator.ui")[0]
else:
    # load the .ui files
    try:
        opto_class = uic.loadUiType("../ui/opto_generator.ui")[0]
    except:
        opto_class = uic.loadUiType('ui/opto_generator.ui')[0]


class LedController:

    def __init__(self, **kwargs):

        print("Starting Opto LED Controller")

        # Explicit path to virtualenv python executable or whatever environment
        # houses PsychoPy
        if platform.platform().startswith('Windows'):
            self.python_exec = "python"
        else:
            self.python_exec = "/home/fitzlab1/anaconda2/envs/psychopy/bin/python"

        # Get cwd
        self.working_dir = kwargs.get('cwd', os.getcwd())

        # Start subprocess
        self.proc = None

    def start(self):
        print('Starting LED Controller')
        sys.stdout.flush()
        os.environ['PATH'] = self.python_exec + os.pathsep + os.environ.get('PATH', '')

        self.proc = subprocess.Popen([self.python_exec, 'devices/opto_generator.py', '--called'],
                                     cwd=self.working_dir, stdin=subprocess.PIPE)

    def write(self, s):
        """Writes stim commands from the task to OptoSubprocess"""
        self.proc.stdin.write(s + '\n')
        #self.proc.stdin.write(s) #ms edit 7/11/2018

    def close(self):
        pass

    def getUpdates(self):
        pass


class OptoSubprocess(QtGui.QMainWindow, opto_class):

    def __init__(self, parent=None):

        self.boardNum = 1 #If no stim trigger, set to zero, should crash, then set to 1, then should work
        self.clock = core.Clock()
        self.gain = UL.UNI4VOLTS
        self.EngUnits = 1
        self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, self.EngUnits, 0)

        self.trainTime = core.Clock()
        self.power = 5          # Power from the LED in mW/mm^2
        self.amplitude = 0      # Amplitude to DAQ (V)

        # waveform parameters
        self.waveform = None
        self.windowArea = 7     # mm^2
        self.stimSustain = 5    # Duration of period of max power (ms)
        self.rampUp = 1         # Duration of ramp up (ms) appended to
        self.rampDown = 1       # Duration of ramp down (ms)
        self.cycles = 2         # Number of cycles during pulse trains
        self.ISI = 5            # duration of inter stim interval (ms)
        self.pulseTrain = False
        self.t_tot = self.rampUp + self.stimSustain + self.rampDown

        self.pulse_set = ['RAMP', 'SAWTOOTH', 'SINE_RAMP', 'SINE_TRAP', 'SQUARE', 'TRAP', 'TRIANGLE']
        self.cmds = deque()

        # ------------------------------------------------------------
        # UI Setup
        # ------------------------------------------------------------

        # make Qt window
        super(OptoSubprocess, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Waveform Builder')

        # get waveform functions and add them to checkbox
        funcs = inspect.getmembers(OptoSubprocess, predicate=inspect.ismethod)
        for f in sorted(funcs, key=lambda x: x[0]):
            if f[0].endswith('wf'):
                self.cbWaveform.addItem(f[0].rsplit('_', 1)[0])

        # set valid range for power
        self.spPower.setRange(0, 20)
        self.spPower.setSingleStep(5)
        self.maxVolt = 4.096

        # set options for window radius
        self.cbWindow.addItem(str(3))
        self.cbWindow.addItem(str(5))

        # set valid range for pulse train cycles
        self.spCycles.setMinimum(1)

        # set valid range for all spin boxes
        self.spSustain.setMinimum(0)
        self.spRampUp.setMinimum(1)
        self.spRampDown.setMinimum(1)

        # set individual values initially
        self.spPower.setValue(self.power)
        self.spSustain.setValue(self.stimSustain)
        self.spRampUp.setValue(self.rampUp)
        self.spRampDown.setValue(self.rampDown)
        self.spCycles.setValue(self.cycles)
        self.spISI.setValue(self.ISI)

        # define UI functions
        self.btnOpto.clicked.connect(self.manual_opto)
        self.btnDummy.clicked.connect(self.manual_dummy)
        self.cbxCycles.clicked.connect(self.set_pulse_train)
        self.cbWaveform.currentIndexChanged.connect(self.set_wave)
        self.cbWindow.currentIndexChanged.connect(self.set_area)
        self.spPower.valueChanged.connect(lambda: self.change_spin(self.spPower, 'power'))
        self.spSustain.valueChanged.connect(lambda: self.change_spin(self.spSustain, 'stimSustain'))
        self.spRampUp.valueChanged.connect(lambda: self.change_spin(self.spRampUp, 'rampUp'))
        self.spRampDown.valueChanged.connect(lambda: self.change_spin(self.spRampDown, 'rampDown'))
        self.spCycles.valueChanged.connect(lambda: self.change_spin(self.spCycles, 'cycles'))
        self.spISI.valueChanged.connect(lambda: self.change_spin(self.spISI, 'ISI'))

        # Make live plot
        # a figure instance to plot on
        self.figure = Figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)

        # set the layout
        self.wgMPL.addWidget(self.canvas)

        # show UI and set first waveform
        self.show()
        self.set_wave()
        self.set_area()
        self.change_spin(self.spPower, 'power')
        self.change_spin(self.spSustain, 'stimSustain')
        self.change_spin(self.spRampUp, 'rampUp')
        self.change_spin(self.spRampDown, 'rampDown')
        self.change_spin(self.spISI, 'ISI')
        self.change_spin(self.spCycles, 'cycles')

        # start cmd line listening thread
        time.sleep(0.05)
        self.stopFlag = True
        self.startThread()

    # -- general UI functions -- #
    def set_combo_box(self, cbx, value):
        index = cbx.findText(str(value))
        cbx.setCurrentIndex(index)

    def disable_gui_element(self, cbx):
        cbx.setEnabled(False)

    def enable_gui_element(self, cbx):
        cbx.setEnabled(True)

    def change_spin(self, spin, key):
        var = spin.value()
        if key not in ['power', 'cycles']:
            var /= 1000     # convert the times into sec

        # Set the variable
        setattr(self, key, var)

        # If this is the power, we need to convert this to a voltage for the DAQ to read
        if key in ['power']:
            self.amplitude = self.convertWattsToVolts(self.power)

        # Assess changes to the waveform
        self.check_waveform()

    def set_wave(self):
        self.waveform = str(self.cbWaveform.currentText())
        self.check_waveform()

    def set_area(self):
        rad = int(self.cbWindow.currentText())
        self.windowArea = pi * (rad/2)**2
        self.set_waveform()
        # self.plot()

    def check_waveform(self):
        "Checks the selected waveform and parameters to prevent divide by zero errors"
        if self.waveform in ['ramp', 'sine_ramp'] and self.rampUp == 0:
            # We're now no longer a ramp but a square
            self.waveform = 'square'

        elif (self.waveform == 'ramp' and self.stimSustain == 0) or (self.waveform == 'triangle' and self.rampDown == 0):
            # We're now no longer a ramp but a sawtooth
            self.waveform = 'sawtooth'

        elif self.waveform in ['trap'] and self.stimSustain == 0:
            # We're now no longer a trap but a triangle
            self.waveform = 'triangle'

        else:
            pass

        self.set_waveform()
        self.set_combo_box(self.cbWaveform, self.waveform)

        # To handle long stimulus pulses
        t_tot = (self.rampUp + self.stimSustain + self.rampDown) * 1000
        if self.spCycles.isEnabled():
            t_tot = t_tot + int(self.ISI*1000)
            t_tot *= self.cycles
        self.t_tot = t_tot

    def set_waveform(self):
        if self.waveform in ['ramp', 'sine_ramp']:
            self.enable_gui_element(self.spRampUp)
            self.enable_gui_element(self.lbRampUp)
            self.disable_gui_element(self.spRampDown)
            self.disable_gui_element(self.lbRampDown)
            self.enable_gui_element(self.spSustain)
            self.enable_gui_element(self.lbSustain)
        elif self.waveform in ['trap', 'sine_trap']:
            self.enable_gui_element(self.spRampUp)
            self.enable_gui_element(self.lbRampUp)
            self.enable_gui_element(self.spRampDown)
            self.enable_gui_element(self.lbRampDown)
            self.enable_gui_element(self.spSustain)
            self.enable_gui_element(self.lbSustain)
        elif self.waveform in ['triangle']:
            self.enable_gui_element(self.spRampUp)
            self.enable_gui_element(self.lbRampUp)
            self.enable_gui_element(self.spRampDown)
            self.enable_gui_element(self.lbRampDown)
            self.disable_gui_element(self.spSustain)
            self.disable_gui_element(self.lbSustain)
        elif self.waveform in ['sawtooth']:
            self.enable_gui_element(self.spRampUp)
            self.enable_gui_element(self.lbRampUp)
            self.disable_gui_element(self.spRampDown)
            self.disable_gui_element(self.lbRampDown)
            self.disable_gui_element(self.spSustain)
            self.disable_gui_element(self.lbSustain)
        else:
            self.disable_gui_element(self.spRampUp)
            self.disable_gui_element(self.lbRampUp)
            self.disable_gui_element(self.spRampDown)
            self.disable_gui_element(self.lbRampDown)
            self.enable_gui_element(self.spSustain)
            self.enable_gui_element(self.lbSustain)

    def set_pulse_train(self):
        if not self.pulseTrain:
            self.pulseTrain = True
            self.enable_gui_element(self.spCycles)
            self.enable_gui_element(self.spISI)
            self.enable_gui_element(self.lbISI)
        else:
            self.pulseTrain = False
            self.disable_gui_element(self.spCycles)
            self.disable_gui_element(self.spISI)
            self.disable_gui_element(self.lbISI)

        # To handle long stimulus pulses
        t_tot = (self.rampUp + self.stimSustain + self.rampDown) * 1000
        if self.spCycles.isEnabled():
            t_tot = t_tot + int(self.ISI * 1000)
            t_tot *= self.cycles
        if t_tot < 50:
            self.plot()
        else:
            self.plot(int(t_tot))

    def manual_opto(self):
        pinOut = 2
        if not self.pulseTrain:
            self.single_pulse(pinOut)
        else:
            self.pulse_train(pinOut)

    def manual_dummy(self):
        pinOut = 1
        if not self.pulseTrain:
            self.single_pulse(pinOut)
        else:
            self.pulse_train(pinOut)

    def opto_stim(self, pinOut):
        if not self.pulseTrain:
            self.single_pulse(pinOut)
        else:
            self.pulse_train(pinOut)

    # -- waveforms -- #
    # We're going to make waveforms that are composites of basic functions
    def steady_state(self, pinOut, amp):
        self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, amp, 0)
        if pinOut < 2:
            # If the pinout is specified as 0 or 1, we can trigger the opto LED or
            # sham LED individually
            UL.cbAOut(self.boardNum, pinOut, self.gain, self.dataValue)
        else:
            # If we're calling pinOut = 2, flash both the opto and sham LED simultaneously
            self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, amp, 0)
            dV = UL.cbFromEngUnits(self.boardNum, self.gain, self.maxVolt, 0)
            UL.cbAOut(self.boardNum, 0, self.gain, self.dataValue)
            UL.cbAOut(self.boardNum, 1, self.gain, dV)

        # maintain this voltage for the sustain period
        time.sleep(self.stimSustain)

    def linear_ramp(self, pinOut, direction, amp):
        if pinOut < 2:
            # If the pinout is specified as 0 or 1, we can trigger the opto LED or
            # sham LED individually

            # direction is 0 for up and 1 for down
            if direction == 0:
                while self.trainTime.getTime() < self.rampUp:
                    power = amp * self.trainTime.getTime() / self.rampUp
                    self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, power, 0)
                    UL.cbAOut(self.boardNum, pinOut, self.gain, self.dataValue)
            else:
                t0 = self.rampUp + self.stimSustain
                while self.trainTime.getTime() <= t0 + self.rampDown:
                    power = amp - (self.amplitude / self.rampDown) * (self.trainTime.getTime()-t0)
                    self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, power, 0)
                    UL.cbAOut(self.boardNum, pinOut, self.gain, self.dataValue)

        else:
            # If we're calling pinOut = 2, flash both the opto and sham LED simultaneously
            if direction == 0:
                while self.trainTime.getTime() < self.rampUp:
                    power = amp * self.trainTime.getTime() / self.rampUp
                    self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, power, 0)
                    dV = UL.cbFromEngUnits(self.boardNum, self.gain, self.maxVolt, 0)
                    UL.cbAOut(self.boardNum, 0, self.gain, self.dataValue)
                    UL.cbAOut(self.boardNum, 1, self.gain, dV)

            else:
                t0 = self.rampUp + self.stimSustain
                while self.trainTime.getTime() <= t0 + self.rampDown:
                    power = amp - (self.amplitude / self.rampDown) * (self.trainTime.getTime() - t0)
                    self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, power, 0)
                    dV = UL.cbFromEngUnits(self.boardNum, self.gain, self.maxVolt, 0)
                    UL.cbAOut(self.boardNum, 0, self.gain, self.dataValue)
                    UL.cbAOut(self.boardNum, 1, self.gain, dV)

    def sinusiodal_ramp(self, pinOut, direction, amp):
        if pinOut < 2:
            # If the pinout is specified as 0 or 1, we can trigger the opto LED or
            # sham LED individually

            # direction is 0 for up and 1 for down
            if direction == 0:
                while self.trainTime.getTime() < self.rampUp:
                    # force the period of the cosine function to be 2*rampUp
                    t = pi * self.trainTime.getTime() / self.rampUp
                    power = 0.5*amp * (1 + cos(t + pi))
                    self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, power, 0)
                    UL.cbAOut(self.boardNum, pinOut, self.gain, self.dataValue)
            else:
                t0 = self.rampUp + self.stimSustain
                while self.trainTime.getTime() < t0 + self.rampDown:
                    t = pi * ((self.trainTime.getTime()-t0) / self.rampDown)
                    power = 0.5 * amp * (1 + cos(t))
                    self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, power, 0)
                    UL.cbAOut(self.boardNum, pinOut, self.gain, self.dataValue)

        else:
            # If we're calling pinOut = 2, flash both the opto and sham LED simultaneously
            # direction is 0 for up and 1 for down
            if direction == 0:
                while self.trainTime.getTime() < self.rampUp:
                    # force the period of the cosine function to be 2*rampUp
                    t = pi * self.trainTime.getTime() / self.rampUp
                    power = 0.5 * amp * (1 + cos(t + pi))
                    self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, power, 0)
                    dV = UL.cbFromEngUnits(self.boardNum, self.gain, self.maxVolt, 0)
                    UL.cbAOut(self.boardNum, 0, self.gain, self.dataValue)
                    UL.cbAOut(self.boardNum, 1, self.gain, dV)
            else:
                t0 = self.rampUp + self.stimSustain
                while self.trainTime.getTime() < t0 + self.rampDown:
                    t = pi * ((self.trainTime.getTime() - t0) / self.rampDown)
                    power = 0.5 * amp * (1 + cos(t))
                    self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, power, 0)
                    dV = UL.cbFromEngUnits(self.boardNum, self.gain, self.maxVolt, 0)
                    UL.cbAOut(self.boardNum, 0, self.gain, self.dataValue)
                    UL.cbAOut(self.boardNum, 1, self.gain, dV)

    def reset(self, pinOut):
        self.dataValue = UL.cbFromEngUnits(self.boardNum, self.gain, 0, 0)
        if pinOut < 2:
            # If the pinout is specified as 0 or 1, we can trigger the opto LED or
            # sham LED individually
            UL.cbAOut(self.boardNum, pinOut, self.gain, self.dataValue)
        else:
            # If we're calling pinOut = 2, flash both the opto and sham LED simultaneously
            UL.cbAOut(self.boardNum, 0, self.gain, self.dataValue)
            UL.cbAOut(self.boardNum, 1, self.gain, self.dataValue)

    def ramp_wf(self, pinOut, amp):
        # Reset clock
        self.trainTime.reset()
        # Begin ramp
        self.linear_ramp(pinOut, 0, amp)
        # Maintain max voltage for some duration of time
        self.steady_state(pinOut, amp)
        # reset
        self.reset(pinOut)

    def sine_ramp_wf(self, pinOut, amp):
        # reset clock
        self.trainTime.reset()
        # ramp up
        self.sinusiodal_ramp(pinOut, 0, amp)
        # set DAQ high and maintain
        self.steady_state(pinOut, amp)
        # reset
        self.reset(pinOut)

    def square_wf(self, pinOut, amp):
        # reset clock
        self.trainTime.reset()
        # set DAQ high and maintain
        self.steady_state(pinOut, amp)
        # drop to zero
        self.reset(pinOut)

    def sawtooth_wf(self, pinOut, amp):
        # reset clock
        self.trainTime.reset()
        # Begin ramp
        self.linear_ramp(pinOut, 0, amp)
        # drop back to zero
        self.reset(pinOut)

    def triangle_wf(self, pinOut, amp):
        # reset clock
        self.trainTime.reset()
        # ramp up
        self.linear_ramp(pinOut, 0, amp)
        # ramp down
        self.linear_ramp(pinOut, 1, amp)

    def trap_wf(self, pinOut, amp):
        # reset clock
        self.trainTime.reset()
        # ramp up
        self.linear_ramp(pinOut, 0, amp)
        # set DAQ high and maintain
        self.steady_state(pinOut, amp)
        # ramp down
        self.linear_ramp(pinOut, 1, amp)

    def sine_trap_wf(self, pinOut, amp):
        # reset clock
        self.trainTime.reset()
        # ramp up
        self.sinusiodal_ramp(pinOut, 0, amp)
        # set DAQ high and maintain
        self.steady_state(pinOut, amp)
        # ramp down
        self.sinusiodal_ramp(pinOut, 1, amp)

    def pulse_train(self, pinOut):
        wf = getattr(self, self.waveform + '_wf')
        if pinOut != 1:
            amp = self.amplitude
        else:
            amp = self.maxVolt
        for c in range(self.cycles):
            wf(pinOut, amp)
            # Fix debounce problems
            self.reset(pinOut)
            time.sleep(self.ISI)

    def single_pulse(self, pinOut):
        wf = getattr(self, self.waveform + '_wf')
        if pinOut != 1:
            amp = self.amplitude
        else:
            amp = self.maxVolt
        wf(pinOut, amp)
        # Fix debounce problems
        self.reset(pinOut)

    def convertVoltsToWatts(self, V):
        # convert data to milliwatts/mm^2 using the regression we found from calibration
        # return (V*31.4 + 7.5) / self.windowArea
        return (-2.3983* V**2 + 40.126*V + 3.3914) / self.windowArea

    def convertWattsToVolts(self, W):
        # convert input power/area using the regression we found from calibration
        # return (W*self.windowArea - 7.5) / 31.4
        return 0.0105*((W*self.windowArea)**1.225)

    # -- plotting -- #
    def plot(self, t_len=50):

        if 'ax' in locals():
            # discards the old graph
            ax.clear()
            # create an axis
            # ax = self.figure.add_subplot(111)
        else:
            # create an axis
            ax = self.figure.add_subplot(111)
            # discards the old graph
            # ax.clear()

        ax.set_ylim([0,25])
        ax.spines['right'].set_color('none')
        ax.spines['top'].set_color('none')
        ax.grid(True)
        ax.set_ylabel('mW/mm^2')
        ax.set_xlabel('mSec')
        ax.set_title('Power Conversion: V * 31.4 + 7.5')

        # make some random x and y data
        scale_factor = 100
        t_len = t_len
        t = np.linspace(0, t_len, num=t_len*scale_factor)
        V = np.zeros(len(t))

        def plot_wave(t, V):
            # bunch of if statements to make the plots
            if self.waveform == 'square':
                idx0 = np.where(t <= self.stimSustain*1000)[0][-1]
                V[1:idx0] = self.amplitude
                V[idx0+1:] = np.NaN
                t_tot = self.stimSustain

            elif self.waveform == 'sawtooth':
                idx0 = np.where(t <= self.rampUp*1000)[0][-1]
                V[:idx0+1] = t[:idx0+1] * self.amplitude/(self.rampUp*1000)
                V[idx0+2:] = np.NaN
                t_tot = self.rampUp

            elif self.waveform == 'triangle':
                idx0 = np.where(t <= self.rampUp*1000)[0][-1]
                idx1 = np.where(t <= (self.rampUp + self.rampDown) * 1000)[0][-1]
                V[:idx0+1] = t[:idx0+1] * self.amplitude/(self.rampUp*1000)
                V[idx0+1:idx1+1] = self.amplitude - (self.amplitude / (self.rampDown*1000)) * (t[idx0+1:idx1+1] - (self.rampUp*1000))
                V[idx1+2:] = np.NaN
                t_tot = self.rampUp + self.rampDown

            elif self.waveform == 'ramp':
                idx0 = np.where(t <= self.rampUp*1000)[0][-1]
                idx1 = np.where(t <= (self.rampUp + self.stimSustain) * 1000)[0][-1]
                V[:idx0+1] = t[:idx0+1] * self.amplitude/(self.rampUp*1000)
                V[idx0+1:idx1+1] = self.amplitude
                V[idx1+2:] = np.NaN
                t_tot = self.rampUp + self.stimSustain

            elif self.waveform == 'sine_ramp':
                idx0 = np.where(t <= self.rampUp*1000)[0][-1]
                idx1 = np.where(t <= (self.rampUp + self.stimSustain) * 1000)[0][-1]
                tp = pi * (1 + (t[:idx0+1] / (self.rampUp*1000)))
                power = np.array([0.5 * self.amplitude * (1 + cos(tP)) for tP in tp])
                V[:idx0+1] = power
                V[idx0+1:idx1+1] = self.amplitude
                V[idx1+2:] = np.NaN
                t_tot = self.rampUp + self.stimSustain

            elif self.waveform == 'trap':
                idx0 = np.where(t <= self.rampUp*1000)[0][-1]
                idx1 = np.where(t <= (self.rampUp + self.stimSustain) * 1000)[0][-1]
                idx2 = np.where(t <= (self.rampUp + self.stimSustain + self.rampDown) * 1000)[0][-1]
                V[:idx0+1] = t[:idx0+1] * self.amplitude/(self.rampUp*1000)
                V[idx0:idx1+1] = self.amplitude
                V[idx1+1:idx2+1] = self.amplitude - (self.amplitude / (self.rampDown*1000)) * (t[idx1+1:idx2+1] - (self.rampUp + self.stimSustain)*1000)
                V[idx2+2:] = np.NaN
                t_tot = self.rampUp + self.stimSustain + self.rampDown

            elif self.waveform == 'sine_trap':
                idx0 = np.where(t <= self.rampUp * 1000)[0][-1]
                idx1 = np.where(t <= (self.rampUp + self.stimSustain) * 1000)[0][-1]
                idx2 = np.where(t <= (self.rampUp + self.stimSustain + self.rampDown) * 1000)[0][-1]
                # define the cosine function for the ramp up
                tpu = pi * (1 + (t[:idx0] / (self.rampUp * 1000)))
                powerUp = np.array([0.5 * self.amplitude * (1 + cos(tPU)) for tPU in tpu])
                # define the cosine function for the ramp down
                tpd = pi * ((t[idx1:idx2+1] - ((self.rampUp + self.stimSustain)*1000)) / (self.rampDown*1000))
                powerDown = np.array([0.5 * self.amplitude * (1 + cos(tPD)) for tPD in tpd])
                V[:idx0] = powerUp
                V[idx0:idx1] = self.amplitude
                V[idx1:idx2+1] = powerDown
                V[idx2+2:] = np.NaN
                t_tot = self.rampUp + self.stimSustain + self.rampDown

            return t, V, t_tot

        # plot data
        if not self.pulseTrain:
            t, V, t_tot = plot_wave(t, V)
            W = self.convertVoltsToWatts(V)
            ax.plot(t, W, 'r-')
        else:
            t, V, t_tot = plot_wave(t, V)
            for c in range(self.cycles):
                if c > 0:
                    t_len += (t_tot + self.ISI)*1000
                    t = np.linspace(0, t_len, num=t_len*scale_factor)
                    V = np.pad(V, (int(self.ISI*1000)*scale_factor, 0), 'constant')
                    V = np.pad(V, (int(t_tot*1000)*scale_factor, 0), 'constant', constant_values=np.NaN)

                W = self.convertVoltsToWatts(V)
                ax.plot(t, W, 'r-')

        # refresh canvas
        self.canvas.draw()

    # -- command line communication -- #
    def listen(self):
        while self.stopFlag:
            # listen for new commands from the pipe
            self.cmds.append(sys.stdin.readline())
            self.doCommands()

    def doCommand(self, cmd, number=None):

        # pulse type
        if cmd == "pls":
            self.waveform = self.pulse_set[int(number)].lower()
            self.set_combo_box(self.cbWaveform, self.waveform)
            self.check_waveform()

        # sustain period
        elif cmd == "sus":
            self.spSustain.setValue(int(number))
            self.change_spin(self.spSustain, 'stimSustain')

        # ramp times (always equal if programmatically controlled)
        elif cmd == "rmp":
            self.spRampUp.setValue(int(number))
            self.spRampDown.setValue(number)
            self.change_spin(self.spRampUp, 'rampUp')
            self.change_spin(self.spRampDown, 'rampDown')

        # power
        elif cmd == "pwr":

            if number == 0:
                # This is a dummy trial
                self.opto_stim(1)
            else:
                # This is a real trial
                self.spPower.setValue(number)
                self.change_spin(self.spPower, 'power')
                self.opto_stim(2)

        elif cmd == 'reset':
            self.reset(2)

        elif cmd == 'kill':
            self.reset(2)
            self.stopFlag = False

    def doCommands(self):
        # splits command string into tokens and executes each one
        cmdStr = ""
        if len(self.cmds) > 0:
            cmdStr = self.cmds.popleft()
        if not cmdStr:
            return

        toks = cmdStr.rstrip().split()
        for t in toks:
            m = re.search("([a-z|A-Z]*)(\-?\d*\.?\d*)", t)
            if m is None:
                continue

            if m.group(1) == "" and m.group(2) != "":
                # load saved command and run it
                number = int(m.group(2))
                self.cmds.append(self.savedCommands[number])

            else:
                # parse token
                cmd = m.group(1)
                number = None
                if len(m.group(2)) > 0:
                    number = float(m.group(2))

                self.doCommand(cmd, number)

    def startThread(self):
        print('LED: Listening for commmands!')
        thread = threading.Thread(target=self.listen)
        thread.daemon = True
        thread.start()


if __name__ == "__main__":
    import UniversalLibrary as UL

    app = QtGui.QApplication(sys.argv)
    myWindow = OptoSubprocess(None)
    myWindow.show()
    app.exec_()
