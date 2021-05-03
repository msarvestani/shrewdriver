# Constants used throughout 2AFC and open-ended 2AFC task. For some constants
# and task types, some setup is required (ex. Interval, Interval Retry) in
# sequencer/SequencerInterval.py

from __future__ import division
import sys
sys.path.append("..")
from util.enumeration import *


'''
Sequences:
    RANDOM - Each trial is chosen randomly from the set of possible trials. 
            (sample with replacement)
    BLOCK - Each trial is presented once (random order). 
    RANDOM_RETRY - Each trial is chosen randomly. If a trial is failed, keep 
                   retrying until success.
    BLOCK_RETRY - Each trial is presented once (random order). Unsuccessful 
                  trials are repeated until success.
    SEQUENTIAL - Each trial is presented once (in order).
    INTERVAL - A set of hard trials, then a set of easy trials, and so on. 
               Requires some setup, see SequencerInterval.py.
    INTERVAL_RETRY - A set of hard trials, then a set of easy trials, and so on. 
                     Requires setup. Unsuccessful trials are repeated until success.
'''

sequenceSet = ['RANDOM', 'BLOCK', 'RANDOM_RETRY', 'BLOCK_RETRY','SEQUENTIAL','INTERVAL','INTERVAL_RETRY']
Sequences = Enumeration("Sequences", sequenceSet)


'''
Trial States:
    TIMEOUT - TIMEOUT caused by task failure before stim identity (left vs right) 
              is revealed.
    TIMEOUT_LEFT - Left syringe. the black screen between trials. Longer timeout 
                   for failing, shorter for succeeding.
    TIMEOUT_RIGHT - Left syringe. the black screen between trials. Longer 
                    timeout for failing, shorter for succeeding.
    INIT - Trial initiation phase. See "Trial Initiation Modes" below.
    DELAY - gray screen of variable duration preceding the first grating 
            presentation
    SLEFT - grating that is precedes rewardPeriod
    SRIGHT - grating that does not precede rewardPeriod
    REWARD_LEFT- Left syringe. gray screen during which reward is available on 
                 left spout. Same duration as GRAY.
    REWARD_RIGHT Right syringe. gray screen during which reward is available on 
                 right spout. Same duration as GRAY.
'''

stateSet = ['TIMEOUT', 'TIMEOUT_LEFT', 'TIMEOUT_RIGHT', 'INIT', 'DELAY', 'SLEFT',
            'SRIGHT', 'REWARD_LEFT', 'REWARD_RIGHT']
States = Enumeration("States", stateSet)


'''
Trial Actions:
    LEFT_LICK - Shrew licks (onset)
    RIGHT_LICK - Shrew licks (onset)
    CENTER_LICK - Shrew center licks (offset)
    LEFT_LICK_DONE - Shrew finishes a left lick (offset)
    RIGHT_LICK_DONE - Shrew finishes a right lick (offset)
    CENTER_LICK_DONE - Shrew finishes a center lick (offset)
'''

actionSet = ['LEFT_LICK', 'RIGHT_LICK', 'LEFT_LICK_DONE', 'RIGHT_LICK_DONE',
             'CENTER_LICK', 'CENTER_LICK_DONE']
Actions = Enumeration("Actions", actionSet)


'''
Trial Results:
    HIT_LEFT - Correct lick on left
    HIT_RIGHT - Correct lick on left
    TASK_FAIL - Left or right lick before trial identity is revealed 
                (left or right stim).
    TASK_FAIL_LEFT - Left Lick when no reward is possible by task structure 
                     (e.g. during a grating)
    TASK_FAIL_RIGHT - Left Lick when no reward is possible by task structure 
                      (e.g. during a grating)
    MISS_LEFT -  Licked wrong port (right on left-rewarded trial)
    MISS_RIGHT -  Licked wrong port (left on right-rewarded trial)
    NO_RESPONSE_LEFT - Shrew didn't lick during reward period
    NO_RESPONSE_RIGHT - Shrew didn't lick during reward period
'''
resultsSet = ['HIT_LEFT', 'HIT_RIGHT', 'TASK_FAIL', 'TASK_FAIL_LEFT',
              'TASK_FAIL_RIGHT', 'MISS_LEFT', 'MISS_RIGHT', 'NO_RESPONSE_LEFT',
              'NO_RESPONSE_RIGHT']
Results = Enumeration("Results", resultsSet)


'''
Trial Initiation Modes:
    IR - Shrew enters infrared beam
    LICK - Lick during INIT period starts trial; licks during DELAY are ignored
    TAP - Tap sensor during INIT starts trial. Shrew can hold tap sensor constantly.
    TAP_ONSET - Tap sensor during INIT starts trial. Tap sensor must be released 
                first.
    AUTO - The task automatically starts upon entering the INIT state.
'''
initSet = ['IR', 'LICK', 'TAP', 'TAP_ONSET', 'AUTO']
Initiation = Enumeration("Initiation", initSet)


'''
Air Puff Modes:
    NONE - Don't use air puff
    BAD_LICK - Puff when the shrew licks at any incorrect time (discrimination 
               or task error)
    TASK_FAIL_LICK - Puff for any lick during trial that's outside a discrimination 
                     response period
    FALSE_ALARM_LICK - Puff if shrew licks for the sMinus grating
    SMINUS_OFFSET - Puff every time the sMinus grating finishes displaying
'''
airPuffSet = ['NONE', 'BAD_LICK', 'TASK_FAIL_LICK', 'FALSE_ALARM_LICK', 'SMINUS_OFFSET']
AirPuffMode = Enumeration("AirPuffMode", airPuffSet)

'''
Stimcodes are sent to Spike2 via the Measurement Computing DAQ. They are only 
used in imaging experiments. Each stimcode is just an arbitrary number.
'''

StateStimcodes = {
    States.TIMEOUT: 0,
    States.TIMEOUT_LEFT: 1,
    States.TIMEOUT_RIGHT: 2,
    States.INIT: 3,
    States.DELAY: 4,
    States.SLEFT: 5,
    States.SRIGHT: 6,
    States.REWARD_LEFT: 7,
    States.REWARD_RIGHT: 8,
}

STIMCODE_BLACK_SCREEN = 10
STIMCODE_GRAY_SCREEN = 11
STIMCODE_SLEFT_SCREEN = 12
STIMCODE_SRIGHT_SCREEN = 13
STIMCODE_GRATING_SCREEN = 14
STIMCODE_USER_COMMAND = 15

STIMCODE_REWARD_GIVEN_LEFT = 19
STIMCODE_REWARD_GIVEN_RIGHT = 20
STIMCODE_AIR_PUFF = 21

# Added later
STIMCODE_USER_TRIAL = 22

STIMCODE_LICK_ON = 30
STIMCODE_LICK_OFF = 31

STIMCODE_FAIL_PUFF = 40
STIMCODE_HINT = 41
STIMCODE_HINT_LEFT = 42
STIMCODE_HINT_RIGHT = 43

STIMCODE_CORRECT_REWARD = 50
STIMCODE_CORRECT_REWARD_LEFT = 51
STIMCODE_CORRECT_REWARD_RIGHT = 52
