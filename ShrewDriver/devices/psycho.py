# psycho.py: PsychoPy Interface and Subclass
# Max Planck Florida Institute for Neuroscience
# Last Modified: 6 March 2018

from __future__ import division
import sys
from collections import deque
import time
import threading
import re
import subprocess
import os
import platform
from random import randint
from psycho_textures import circleGaussianFade, circleLinearFade


class Psycho:
    """
    Provides an easy interface to PsychoSubproc, which is what actually does
    all the work. Never call PsychoSubproc() directly, use Psycho() instead.

    IMPORTANT: The way this works is a bit weird. Instead of housing the
    PsychSubproc() class in a different file, both Psycho() and PsychoSubproc()
    are contained in this file. The way the subprocess call works is by
    running this script in a new instance of Python (see the bottom of this
    file), and opening communication between the main ShrewDriver process and
    the new subprocess via the standard input/output PIPE method.

    Psycho.write() sends stim commands to the subprocess via pipes, where
    PsychoSubproc() parses, interprets, and displays those stim commands.
    """

    def __init__(self, *args, **kwargs):
        self.thisfile = os.path.realpath(__file__)
        self.argStr = str(kwargs)

        self.logFile = None
        if "logFilePath" in kwargs:
            self.logFile = open(kwargs[logFilePath], 'w')

        # Explicit path to virtualenv python executable or whatever environment
        # houses PsychoPy
        if platform.platform().startswith('Windows'):
            self.python_exec = "python"
        else:
            self.python_exec = "/home/fitzlab1/anaconda2/envs/psychopy/bin/python"

        # Create the subprocess
        self.proc = None

    def start(self):
        print "Launching PsychoPy window..."
        sys.stdout.flush()

        os.environ['PATH'] = self.python_exec + os.pathsep + os.environ.get('PATH', '')

        self.proc = subprocess.Popen([self.python_exec, self.thisfile, self.argStr],
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)
        # wait to confirm start
        self.proc.stdout.readline()

    def write(self, s):
        """Writes stim commands from the task to PsychoSubproc"""
        self.proc.stdin.write(s + "\n")        
        if self.logFile:
            t = time.time()
            
    def close(self):
        pass
    
    def getUpdates(self):
        pass


class PsychoSubproc:
    """
    Renders stimbot commands in a PsychoPy window.
    
    PsychoPy runs inside a subprocess, and commands to the PsychoPy process are
    sent through pipes. This allows PsychoPy to run completely independent
    of the rest of ShrewDriver. Gets around the GIL, keeping other operations
    (e.g. camera updates, disk writes) from affecting framerate.

    Thus, you shouldn't call this ever. Just call Psycho() instead.
    """
    
    def __init__(self, screen=0, windowed=True, movie_dir=None):
        # stim params
        self.tf = 0
        self.windowed = windowed
        self.gratingStartTime = 0
        self.jitterAmount = 0
        self.jitterFrequency = 0
        self.phaseAtStart = 0
        self.sPlusDir = None
        self.sMinusDir = None

        # Initialize directory with stim movies (added for Doris Tsao collab)
        self.movie_dir = movie_dir
        self.mv_file = None

        # commands are stored in a double-ended queue
        self.cmds = deque()

        # make slots for command saving
        self.savedCommands = [""] * 100

        # initialize masks
        self.gaussianMask = circleGaussianFade(0.8)
        # self.linearMask = circleLinearFade(0.8) #unused
        
        # stim state variables
        self.drawPhotodiodeStim = False
        self.drawGrating = True
        self.drawPatch = False
        self.drawMovie = False
        self.useMovie = False
        self.updateMovie = False

        # allow plenty of time for window to start up
        time.sleep(4)
        self.beginRender()

    def beginRender(self):
        # start render thread
        print "Starting PsychoPy window..."
        thread = threading.Thread(target=self.renderThreadFcn)
        thread.daemon = True
        thread.start()

    def updatePhase(self):
        # called before grating appears, and again on each flip
        # updates grating's phase according to phase, tf, and jitter commands
        elapsed = time.time() - self.gratingStartTime
        tfOffset = elapsed * self.tf

        jitterPhase = (elapsed * self.jitterFrequency) % 1
        jitterOffset = jitterPhase
        if jitterOffset < 0.5:
            jitterOffset = 1-jitterOffset

        jitterOffset *= self.jitterAmount*2

        newPhase = self.phaseAtStart + tfOffset + jitterOffset
        self.grating.setPhase(newPhase)

    def renderThreadFcn(self):
        """Makes a PsychoPy window and begins listening for commands"""

        # setup must be done in same thread as rendering
        from psychopy import visual, logging, core, filters, event, monitors

        # Set up a monitor
        self.mon = monitors.Monitor('StimMonitor')

        # Change these values for your setup
        self.mon.setDistance(25)
        self.mon.setSizePix([1920, 800])
        self.mon.setWidth(51)
        res = [1920, 800]
        if self.windowed:
            res = [800, 600]

        # make window
        self.win = visual.Window(size=res, monitor=self.mon,
                                 fullscr=(not self.windowed), screen=1)
        # get the framerate
        self.framerate = self.win.getActualFrameRate(nIdentical=10,
                                                     nMaxFrames=100,
                                                     nWarmUpFrames=10,
                                                     threshold=1)

        # stimulus
        self.grating = visual.GratingStim(self.win, tex="sqr", mask="gauss",
                                          units="deg", size=(30, 30), sf=0.05,
                                          ori=2, interpolate=True)
        self.drawGrating = True

        self.patch = visual.ImageStim(self.win, image = "color", color=(0.0, 0.0, 0.0),
                                      units="deg", mask="circle",
                                      size=(50, 50), texRes=1024)
        self.drawPatch = False
        
        # photodiode stim
        photodiodeStimPos = (-self.mon.getSizePix()[0]/2,
                             self.mon.getSizePix()[1]/2)
        self.photodiodeStim = visual.ImageStim(self.win,
                                               color=(-1.0, -1.0, -1.0),
                                               units="pix",
                                               pos=photodiodeStimPos,
                                               size=(200, 200))

        # will be manually drawn on top of whatever stim is up
        self.drawPhotodiodeStim = False

        # do some initial commands to get the screen set up
        self.doCommands()

        # Set up a dummy movie . This will be dynamically updated with each call
        # It gets changed for the actual stim
        self.mv_file = self.sPlusDir + '1.avi'
        # Change the size for your stim monitor as well
        mov_size = (1248, 624)
        mov_size = (1920,1080)
        if self.useMovie:
            try:
                self.mov = visual.MovieStim3(self.win, self.mv_file,
                                             size=mov_size, loop=True)
            except AttributeError:
                self.mov = visual.MovieStim(self.win, self.mv_file,
                                             size=mov_size, loop=True)

            self.drawMovie = False

        # render loop
        # timeBetweenFrames = 0.008
        timeBetweenFrames = 1. / 60    # refresh rate of monitor [1/Hz]

        while True:
            # update window
            self.win.flip()
            t0 = time.time()
            
            # read commands
            self.doCommands()

            # update stim phase based on jitter / temporal frequency
            self.updatePhase()

            # update movie
            if self.updateMovie:
                del self.mov
                self.mov = visual.MovieStim3(self.win, self.mv_file,
                                             size=mov_size, loop=True)
                self.updateMovie = False
            
            # update photodiode stim
            self.updatePhotodiodeStim()

            # draw stims
            if self.drawPatch:
                self.patch.draw()
            if self.drawGrating:
                self.grating.draw()
            if self.drawMovie:
                self.mov.draw()
            if self.drawPhotodiodeStim:
                # must draw this last so it's on top
                self.photodiodeStim.draw()

            elapsed = time.time()-t0

            # sleep for half the time remaining until the next frame
            sleepTime = max((timeBetweenFrames-elapsed)/2, 0.010)
            time.sleep(sleepTime) 

    def updatePhotodiodeStim(self):
        """Photodiode stim is solid white when no grating is displayed.
        At the start of a grating, it goes black. It then oscillates between
        gray and black while as long as the grating is displayed.
        """

        if self.drawGrating and self.grating.size[0] > 0 and self.grating.size[1] > 0:
            if self.photodiodeStim.color[0] == -1.0:
                self.photodiodeStim.setColor((0.0, 0.0, 0.0))
            else:
                self.photodiodeStim.setColor((-1.0, -1.0, -1.0))
        else:
            self.photodiodeStim.setColor((1.0, 1.0, 1.0))

    def write(self, cmdStr):
        """Writes incoming commands to the command queue"""
        self.cmds.append(cmdStr)

    def doCommand(self, cmd, number=None):
        """
        Called by self.doCommands(), this function executes the commands that
        were parsed earlier. New commands can be added easily.

        Args:
            cmd: [str] the command to be executed
            number: [float or int] some value or flag specific to the command
        """

        # load existing
        if cmd == "load":
            self.commands.append(self.savedCommands[number])
            self.doCommands()

        # configuration
        if cmd == "screendist":
            print "setting dist to " + str(number)
            self.mon.setDistance(number)

        elif cmd == 'setSPD':
            print 'setting sPlus movie directory to ' + str(number)
            self.sPlusDir = self.movie_dir + str(number)

        elif cmd == 'setSMD':
            print 'setting sMinus movie directory to ' + str(number)
            self.sMinusDir = self.movie_dir + str(number)

        # textures
        elif cmd == "sin":
            self.grating.tex = "sin"
            self.grating.ori = 90+number
            self.showGrating()
        elif cmd == "sqr":
            self.grating.tex = "sqr"
            self.grating.ori = 90+number
            self.showGrating()

        # colors. Recall that -1 is black, 0 is gray, 1 is white in PsychoPy.
        elif cmd == "pab":  # black
            self.patch.setColor((-1.0, -1.0, -1.0))
            self.patch.color = [-1.0,-1.0,-1.0]
            self.showPatch()
        elif cmd == "paw":  # white
            self.patch.setColor((1.0, 1.0, 1.0))
            self.showPatch()
        elif cmd == "pag":  # gray
            self.patch.setColor((0.0, 0.0, 0.0))
            self.showPatch()
        elif cmd == "par":  # red
            self.patch.setColor((1.0, 0.0, 0.0))
            self.showPatch()
        elif cmd == "pae":  # green
            self.patch.setColor((0.0, 1.0, 0.0))
            self.showPatch()
        elif cmd == "pau":  # blue
            self.patch.setColor((0.0, 0.0, 1.0))
            self.showPatch()
        elif cmd == "pac":  # cyan
            self.patch.setColor((0.0, 1.0, 1.0))
            self.showPatch()
        elif cmd == "pay":  # yellow
            self.patch.setColor((1.0, 1.0, 0.0))
            self.showPatch()
        elif cmd == "pam":  # magenta
            self.patch.setColor((1.0, 0.0, 1.0))
            self.showPatch()
        
        # position
        elif cmd == "px":
            self.grating.setPos([number, self.grating.pos[1]])
            self.patch.setPos([number, self.patch.pos[1]])
        elif cmd == "py":
            self.grating.setPos([self.grating.pos[0], number])
            self.patch.setPos([self.patch.pos[0], number])

        # size
        elif cmd == "sx":
            self.grating.setSize([number, self.grating.size[1]])
            self.patch.setSize([number, self.patch.size[1]])
        elif cmd == "sy":
            self.grating.setSize([self.grating.size[0], number])
            self.patch.setSize([self.patch.size[0], number])

        # aperture
        elif cmd == "ac":
            self.grating.setMask("circle")
        elif cmd == "ag":
            self.grating.setMask("gauss")
        
        # aperture todo
        elif cmd == "as":     # square
            self.grating.setMask(None)
        elif cmd == "acgf":   # circle, gauss fade
            self.grating.setMask(self.gaussianMask)
        elif cmd == "aclf":   # circle, linear fade
            raise NotImplementedError
            # unused, not worth waiting for
            # self.grating.setMask(self.linearMask)

        # grating funtimes
        elif cmd == "sf":
            self.grating.setSF(number)
        elif cmd == "tf":
            self.tf = number
        elif cmd == "ph":
            self.phaseAtStart = number
        elif cmd == "gc":
            self.grating.setContrast(number)
        elif cmd == "ja":
            self.jitterAmount = number
        elif cmd == "jf":
            self.jitterFrequency = number

        # movie
        elif cmd == 'movSP':
            # movie
            mv_file = self.sPlusDir + str(int(number)) + '.avi'
            self.mv_file = mv_file
            self.showMovie()

        elif cmd == 'movSM':
            # movie
            mv_file = self.sMinusDir + str(int(number)) + '.avi'
            self.mv_file = mv_file
            self.showMovie()

    def doCommands(self):
        """
        Parses commands from the command queue into a command string and a
        number indicating the value to be changes or action performed.
        """

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
                
                # handle special case of "save".
                # "save" must be at the beginning of saved command.
                if cmd == "save":
                    remainder = (" ").join(toks[1:])
                    assert "save" not in remainder  # avoid infinite loop
                    self.savedCommands[int(number)] = remainder
                    break
                elif cmd in ['setSPD', 'setSMD']:
                    number = str(cmdStr.split('&')[1].replace('\n', ''))
                    self.doCommand(cmd, number)
                    self.useMovie = True

                else:
                    # do the command
                    self.doCommand(cmd, number)
                    
    def showPatch(self):
        """Sets booleans for drawing photodiode patch"""
        self.drawGrating = False
        self.drawPatch = True
        self.drawMovie = False
        self.updateMovie = False

    def showGrating(self):
        """Sets booleans for drawing oriented grating & sets start time"""
        self.drawGrating = True
        self.drawPatch = False
        self.drawMovie = False
        self.updateMovie = False
        self.gratingStartTime = time.time()

    def showMovie(self):
        """Sets booleans for using a movie as a stimulus"""
        self.drawGrating = False
        self.drawPatch = False
        self.drawMovie = True
        self.updateMovie = True
        self.gratingStartTime = time.time()


class NoRender:
    """Use this class when you want no stim display, nice for testing"""
    def __init__(self):
        pass

    def write(self, s):
        pass


if __name__ == "__main__":

    if len(sys.argv) == 1:
        # Demonstration
        pw = Psycho(windowed=False, movie_dir='/FIG_Movies/FIG_Movie_')

        cmds = ["as pab sx999 sy999",
                "save0 ac sf2 ph0.76",
                "save1 sf0.5 sx30 sy30 as",
                "0 sqr45 ph0.76",
                "1",
                "tf1.0",
                "tf0",
                "ph0.25",
                "ph0.5 gc0.5",
                "ph0.75",
                "sx3 sy3 acgf sqr45 ja1.0 jf1.0"]

        for cmd in cmds:
            time.sleep(1.5)
            print cmd
            pw.write(cmd)

        cmds = ["paw", "pab"]
        pw.write("as pab sx30 sy30")
        while True:
            for cmd in cmds:
                pw.write(cmd)

        # don't close pipe until parent has finished reading, or error will occur
        time.sleep(10.0)
        
    else:
        # This is the child process that Psycho runs in.

        # parse kwargs. Will have to change this if you add any more args actually.
        kwargStr = "".join(sys.argv[1:]).split(',')
        w = False
        md = None
        for item in kwargStr:
            if "windowed" in item and "True" in item:
                w = True
            if "movie_dir" in item:
                md = item.split()[1].replace("'", "")

        p = PsychoSubproc(windowed=w, movie_dir=md)
        
        # send back a "ready" confirmation to main process
        print "PsychoPy ready!"
        sys.stdout.flush()
        
        # listen to stdin for commands, pass them to Psycho
        while True:
            try:
                s = raw_input()
                p.write(s.rstrip() + "\n")  # ensure newline on writes
            except EOFError:
                break
