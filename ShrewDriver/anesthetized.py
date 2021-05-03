from __future__ import division


import time
import datetime
from collections import deque
import pickle
import os

from anesthetized.stim_script import StimEvent, StimScript
from devices.psycho import Psycho
from devices.daq import MccDaq

'''
Run this file to show trial-like stimuli to an anesthetized shrew.
'''

def make_trial_script_nonmatch(
    t_timeout=2,
    t_init = 1,
    t_grating = 0.5,
    t_timingDelay = 2.0,
    t_responsePeriod = 1.0,
    t_memoryDelay = 1.0,
    jitter = " jf3 ja0.25 ",
    splus = " sqr135 ",
    sminus = " sqr160 ",
    rfPos = " px0 py0 ",
    nBlocks=12
    ):

    """
    Build an array of stim events, make a StimScript out of it, and return.
    This shows nonmatch-to-sample style stimuli, so there is a sample grating at the beginning.
    Each block contains a match trial and a nonmatch trial.
    """
    events = []
    t=0
    for i in xrange(nTrials):
        #=== 3-grating trial ===#
        events.append( StimEvent(startTime=t, command="ac pab sx12 sy12"+rfPos, stimcode=0) ) #Timeout
        t+=t_timeout
        events.append( StimEvent(startTime=t, command="ac paw sx12 sy12"+rfPos, stimcode=1) ) #Init
        t+=t_init
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=2) ) #TimingDelay
        t+=t_timingDelay
        events.append( StimEvent(startTime=t, command="as sf0.25 tf0 px0 py0 sx999 sy999"+sminus+jitter, stimcode=3) ) #Sample Grating
        t+=t_grating
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=4) ) #Memory Delay
        t+=t_memoryDelay
        events.append( StimEvent(startTime=t, command="as sf0.25 tf0 px0 py0 sx999 sy999"+sminus+jitter, stimcode=5) ) #Match
        t+=t_grating
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=6) ) #Response Period (false alarm)
        t+=t_responsePeriod
        events.append( StimEvent(startTime=t, command="as sf0.25 tf0 px0 py0 sx999 sy999"+splus+jitter, stimcode=7) ) #Nonmatch
        t+=t_grating
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=8) ) #Nonmatch Response Period (correct reject)
        t+=t_responsePeriod

        #=== 2-grating trial ===#
        events.append( StimEvent(startTime=t, command="ac pab sx12 sy12"+rfPos, stimcode=0) ) #Timeout
        t+=t_timeout
        events.append( StimEvent(startTime=t, command="ac paw sx12 sy12"+rfPos, stimcode=1) ) #Init
        t+=t_init
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=2) ) #TimingDelay
        t+=t_timingDelay
        events.append( StimEvent(startTime=t, command="as sf0.25 tf0 px0 py0 sx999 sy999"+sminus+jitter, stimcode=3) ) #Sample Grating
        t+=t_grating
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=4) ) #Memory Delay
        t+=t_memoryDelay
        events.append( StimEvent(startTime=t, command="as sf0.25 tf0 px0 py0 sx999 sy999"+splus+jitter, stimcode=7) ) #Nonmatch
        t+=t_grating
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=8) ) #Nonmatch Response Period (hit)
        t+=t_responsePeriod

    script = StimScript(events, daq=MccDaq())
    return script


def make_trial_script_go_nogo(
    t_timeout=2,
    t_init = 1,
    t_grating = 0.5,
    t_timingDelay = 2.0,
    t_responsePeriod = 1.0,
    jitter = " jf3 ja0.25 ",
    splus = " sqr135 ",
    sminus = " sqr160 ",
    rfPos = " px0 py0 ",
    nBlocks=12
    ):

    """
    Build an array of stim events, make a StimScript out of it, and return.
    This shows go/no-go style stimuli, so it displays either 1 or 2 gratings.
    A block contains both a go trial and a no-go trial.
    """
    events = []
    t=0
    for i in xrange(nBlocks):
        #=== 2-grating trial ===#
        events.append( StimEvent(startTime=t, command="ac pab sx12 sy12"+rfPos, stimcode=0) ) #Timeout
        t+=t_timeout
        events.append( StimEvent(startTime=t, command="ac paw sx12 sy12"+rfPos, stimcode=1) ) #Init
        t+=t_init
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=2) ) #TimingDelay
        t+=t_timingDelay
        events.append( StimEvent(startTime=t, command="as sf0.25 tf0 px0 py0 sx999 sy999"+sminus+jitter, stimcode=5) ) #No-Go
        t+=t_grating
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=6) ) #Response Period (false alarm)
        t+=t_responsePeriod
        events.append( StimEvent(startTime=t, command="as sf0.25 tf0 px0 py0 sx999 sy999"+splus+jitter, stimcode=7) ) #Go
        t+=t_grating
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=8) ) #Response Period (correct reject)
        t+=t_responsePeriod

        #=== 1-grating trial ===#
        events.append( StimEvent(startTime=t, command="ac pab sx12 sy12"+rfPos, stimcode=0) ) #Timeout
        t+=t_timeout
        events.append( StimEvent(startTime=t, command="ac paw sx12 sy12"+rfPos, stimcode=1) ) #Init
        t+=t_init
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=2) ) #TimingDelay
        t+=t_timingDelay
        events.append( StimEvent(startTime=t, command="as sf0.25 tf0 px0 py0 sx999 sy999"+splus+jitter, stimcode=7) ) #Go
        t+=t_grating
        events.append( StimEvent(startTime=t, command="sx0 sy0", stimcode=8) ) #Response Period (hit)
        t+=t_responsePeriod

    script = StimScript(events, daq=MccDaq())
    return script


if __name__ == "__main__":
    """
    Displays trial stimuli to an anesthetized shrew using one of the functions above.
    Spike2 will receive stimcodes, so make sure to start running Spike2 first.

    Saves configuration data to C:\ShrewData_Anesthetized.
    """

    script = make_trial_script_go_nogo(
        t_timeout=6,
        t_init = 1,
        t_grating=0.5,
        t_timingDelay=2.0,
        t_responsePeriod=1.5,
        jitter=" jf3 ja0.25 ",
        splus=" sqr135 ",  #<--- adjust go orientation here
        sminus=" sqr160 ", #<--- adjust no-go orientation here
        rfPos=" px0 py0 ",
        nBlocks=12)  # type: StimScript

    # config
    script.stimDevice = Psycho(windowed=False)  # either a devices.stimbot.StimBot() or a devices.psycho.Psycho().
    script.stimDevice.write("screendist25")
    script.save()
    time.sleep(10)  # allow PsychoPy window to wake up

    # go!
    script.run()
