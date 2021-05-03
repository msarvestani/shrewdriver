from __future__ import division
import sys
sys.path.append("..")

import inspect

#These are just a few junk classes we'll use to demonstrate
class SubSubClass():
    def __init__(self):
        self.footlong = True
        self.lettuce = True
        self.tomato = True
        self.type = 'Italian'
        
class SubClass():
    def __init__(self):
        self.states = [1, 2]
        self.subParameters = SubSubClass()
        self.subParameters.type = 'Meatball'
       
class MainClass():
    def __init__(self):
        
        self.timeout = 3
        self.isBrakeOn = False
        self.rewardStimFreq = 0.05
        self.failStimFreq = 0.05
        self.listything = [[0,1],[2,3]]
        
        self.tParams = SubClass()
        
    def anotherMethod(self):
        yep = 3

#magic happens here
def objectToStringRecursive(obj, prefix, objStr):
    for attr in dir(obj):
        if attr.startswith('__'):
            continue
        if not callable(getattr(obj, attr)):            
            value = (getattr(obj,attr))
            if type(value).__name__ == 'instance': #subclass - recurse!
                objStr += objectToStringRecursive(eval('obj.'+attr), prefix + attr + ".", objStr)
            else:
                if type(value).__name__ == 'str':
                    objStr += prefix + attr + " = '" + str(value) + "'\n"
                else:
                    objStr += prefix + attr + " = " + str(value) + '\n'
    return objStr

def objectToString(obj):
    return objectToStringRecursive(obj, '', '')

def stringToObject(objStr, objInstance):
    for line in objStr.split('\n'):
        if not len(line.rstrip()) == 0:
            print 'evaluating line: ' + line
            exec('objInstance.' + line)

if __name__ == '__main__':
    s = MainClass()
    objStr = objectToString(s) # save object to string representation
    s.timeout = 5 #make a change to the object
    
    stringToObject(objStr, s) #load object from string
    print "This should be 3: " + str(s.timeout) #verify that the change was undone by loading the object
