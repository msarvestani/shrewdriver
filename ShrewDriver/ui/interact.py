# InteractUI: interact.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 16 March 2018

from __future__ import division
import time
import os
import random
from PyQt4 import QtCore, QtGui
from PyQt4 import uic
import sys
sys.path.append("..")

from constants.task_constants import *
from task.task_gonogo import TaskGNG

# load the .ui files
Interact_class = uic.loadUiType("ui/interact.ui")[0]


class InteractUI(QtGui.QMainWindow, Interact_class):

    def __init__(self, parent=None):
        # make Qt window
        QtGui.QMainWindow.__init__(self, parent)
        self.setGeometry(500, 1300, 400, 200)
        self.setupUi(self)

        # --- button actions --- #
        # shrew feedback
        self.btnGiveReward.clicked.connect(self.btn_give_reward_clicked)
        self.btnAirPuff.clicked.connect(self.btn_air_puff_clicked)

        # task manipulation
        self.btnFailTrial.clicked.connect(self.btn_fail_trial_clicked)
        self.btnStartTrial.clicked.connect(self.btn_start_trial_clicked)

        self.btnShowNow.clicked.connect(self.btn_show_now_clicked)
        self.btnReplaceNext.clicked.connect(self.btn_replace_next_clicked)

        # screen manipulation
        self.btnBlack.clicked.connect(self.btn_black_clicked)
        self.btnGrayScreen.clicked.connect(self.btn_gray_screen_clicked)

        self.btnSPlusGrating.clicked.connect(self.btn_splus_grating_clicked)
        self.btnSMinusGrating.clicked.connect(self.btn_sminus_grating_clicked)

        self.btnRunStimCommand.clicked.connect(self.btn_run_stim_command_clicked)

        # setup
        self.show()

    def set_task(self, task):
        """
        Sets the task type for the UI from the task task defined in ShrewDriver

        Args:
            task: [obj] the shrewdriver task object
        """

        self.task = task
        self.training = self.task.training
        sdGeom = self.training.shrewDriver.geometry()  # QtCore.QRect
        geom = self.geometry()                         # QtCore.QRect
        # setGeometry args are: posX, posY, sizeX, sizeY
        self.setGeometry(sdGeom.right() + 20, sdGeom.top(), geom.width(), geom.height())

    def log_and_print(self, s):
        """
        Logs and prints the time a UI-based interaction occurs to the training
        logfile

        Args:
            s: [str] the lone to be written
        """

        print s
        self.training.logFile.write(s + " " + str(time.time()) + "\n")

    # --- shrew feedback -- #
    def btn_give_reward_clicked(self):
        """Delivers a reward based on button click. The bolus volume is
        defined by the number entered in the self.txtRewardSize text box."""

        rewardMicroliters = str(self.txtRewardSize.text())
        self.training.syringeSerial.write(rewardMicroliters + "\n")
        self.log_and_print("User gave reward: " + rewardMicroliters)
        self.training.log_plot_and_analyze("user_reward:" + str(int(rewardMicroliters)/1000),
                                           time.time())
        self.training.daq.send_stimcode(STIMCODE_REWARD_GIVEN)

    def btn_air_puff_clicked(self):
        """Delivers air puff on button click, and logs the press to the log
        file and the daq."""

        if self.training.airPuff is not None:
            self.training.airPuff.puff()
            self.log_and_print("User administered air puff")
            self.training.daq.send_stimcode(STIMCODE_AIR_PUFF)
        else:
            print "No air puff device specified."

    # --- task manipulation --- #
    def btn_start_trial_clicked(self):
        """Starts a trial on button click."""
        self.task.ui_start_trial()

    def btn_fail_trial_clicked(self):
        """Fails trial on button click."""
        self.task.ui_fail_task()

    def btn_replace_next_clicked(self):
        """Replaces the next trial with the stim as commanded in
        self.txtGratingOrientation text box."""

        if not isinstance(self.task, TaskGNG):
            # doesn't make sense on headfix task
            return
        newOri = str(self.txtGratingOrientation.text())
        print "Next orientation set to " + newOri
        self.task.replaceOrientation = newOri

    def btn_show_now_clicked(self):
        """Displays the given grating for 0.5 seconds, then gray screen"""
        ori = str(self.txtGratingOrientation.text())
        stimCommand = "sqr" + ori + " as sf0.25 tf0 jf3 ja0.25 px0 py0 sx999 sy999"
        self.training.stimDevice.write(stimCommand)
        self.log_and_print("Set screen to grating (" + ori + ")")
        self.training.daq.send_stimcode(STIMCODE_USER_COMMAND)
        # sleeping on the UI thread, such hacks *shudder*
        time.sleep(0.5)
        self.training.stimDevice.write("sx0 sy0")
        self.training.daq.send_stimcode(STIMCODE_GRAY_SCREEN)

    # --- screen manipulation --- #
    def btn_black_clicked(self):
        """Blacks out the stim monitor on button click."""

        self.training.stimDevice.write("ac pab px0 py0 sx12 sy12")
        self.log_and_print("Set screen to black (timeout)")
        self.training.daq.send_stimcode(STIMCODE_BLACK_SCREEN)

    def btn_gray_screen_clicked(self):
        """Greys out the stim monitor on button click."""

        self.training.stimDevice.write("sx0 sy0")
        self.log_and_print("Set screen to gray")
        self.training.daq.send_stimcode(STIMCODE_GRAY_SCREEN)

    def btn_splus_grating_clicked(self):
        """Displays a moving S+ grating for 0.5 seconds, then gray screen"""

        if not isinstance(self.task, TaskGNG):
            # doesn't make sense on headfix task
            return

        ori = random.choice(self.task.sPlusOrientations)
        stimCommand = "sqr" + str(ori) + " as sf0.25 tf0 jf3 ja0.25 px0 py0 sx999 sy999"
        self.training.stimDevice.write(stimCommand)
        self.log_and_print("Set screen to S+ grating: " + str(ori))
        self.training.daq.send_stimcode(STIMCODE_SPLUS_SCREEN)
        time.sleep(0.5)       # sleeping on the UI thread, such hacks *shudder*
        self.training.stimDevice.write("sx0 sy0")         # back to gray screen
        self.training.daq.send_stimcode(STIMCODE_GRAY_SCREEN)

    def btn_sminus_grating_clicked(self):
        """Displays a moving S- grating for 0.5 seconds, then gray screen"""

        if not isinstance(self.task, TaskGNG):
            # doesn't make sense on headfix task
            return

        ori = random.choice(self.task.sMinusOrientations)
        stimCommand = "sqr" + str(ori) + " as sf0.25 tf0 jf3 ja0.25 px0 py0 sx999 sy999"
        self.training.stimDevice.write(stimCommand)
        self.log_and_print("Set screen to S- grating: " + str(ori))
        self.training.daq.send_stimcode(STIMCODE_SMINUS_SCREEN)
        time.sleep(0.5)       # sleeping on the UI thread, such hacks *shudder*
        self.training.stimDevice.write("sx0 sy0")         # back to gray screen
        self.training.daq.send_stimcode(STIMCODE_GRAY_SCREEN)

    def btn_run_stim_command_clicked(self):
        """Sets current stim according to the given command"""

        stimCommand = str(self.txtStimCommand.text())
        self.log_and_print("Stim command: " + stimCommand)
        self.training.stimDevice.write(stimCommand)
        self.training.daq.send_stimcode(STIMCODE_USER_COMMAND)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    myWindow = InteractUI()
    app.exec_()
