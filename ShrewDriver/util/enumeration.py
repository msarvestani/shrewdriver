from __future__ import division
import sys
sys.path.append("..")

import types
import string
import pprint
import exceptions

# Class that takes in a list of strings and makes two dicts,
# one for forward lookup and one for reverse lookup.
# Run this file to see an example.

class EnumException(exceptions.Exception):
    pass

class Enumeration:
    def __init__(self, name, enumList):
        self.__doc__ = name
        lookup = { }
        reverseLookup = { }
        i = 0
        uniqueNames = [ ]
        uniqueValues = [ ]
        for x in enumList:
            if type(x) == types.TupleType:
                x, i = x
            if type(x) != types.StringType:
                raise EnumException, "enum name is not a string: " + x
            if type(i) != types.IntType:
                raise EnumException, "enum value is not an integer: " + i
            if x in uniqueNames:
                raise EnumException, "enum name is not unique: " + x
            if i in uniqueValues:
                raise EnumException, "enum value is not unique for " + x
            uniqueNames.append(x)
            uniqueValues.append(i)
            lookup[x] = i
            reverseLookup[i] = x
            i = i + 1
        self.lookup = lookup
        self.reverseLookup = reverseLookup
    def __getattr__(self, attr):
        if not self.lookup.has_key(attr):
            raise AttributeError
        return self.lookup[attr]
    def whatis(self, value):
        return self.reverseLookup[value]

if __name__ == '__main__':
    states = Enumeration("States", ['Fixation', 'ISI', 'Target_Presentation'])
    print '\ndicts:'
    print states.lookup
    print states.reverseLookup
    print '\nUsage:'
    print states.whatis(1)
    print states.Target_Presentation
    
