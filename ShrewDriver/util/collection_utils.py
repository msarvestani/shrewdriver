from __future__ import division
import sys
sys.path.append("..")

"""
A set of tools for working with collections
"""

from collections import OrderedDict

def tally(ls):
    """
    Returns an OrderedDict containing the number of occurrences of each element in a list.
    Result is ordered by first occurrence.
    """
    d = OrderedDict()
    for e in ls:
        if e in d:
            d[e] += 1
        else:
            d[e] = 1
    return d

def list_subtract(list1, list2):
    """
    Returns a copy of list1 that is missing the elements of list2.
    Examples:
    list_subtract([1,2,3], [2]) -> [1,3]
    list_subtract([1,2,2,3], [2]) -> [1,2,3]
    list_subtract([1,2,2,2,3], [2,2,3]) -> [1,2]
    Inputs do not need to be sorted.
    Result will be in the same order as the input list.
    """
    result = []
    t2 = tally(list2)

    for e in list1:
        if e in t2:
            t2[e] -= 1
            if t2[e] == 0:
                t2.pop(e)
        else:
            result.append(e)

    return result

if __name__ == "__main__":
    print "\n[1, 2, 3] minus [2] is:\n", list_subtract([1,2,3], [2])
    print "\nCounts of each number in list ['a','a','a','b','a']:\n", tally(['a','a','a','b','a'])
