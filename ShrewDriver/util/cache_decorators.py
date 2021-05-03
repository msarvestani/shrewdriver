from __future__ import division
import sys
sys.path.append("..")

import os
import pickle
import time

def getFiles(dirPath):
    """ 
    Returns a sorted dict of files in dirPath.
    Key is relative path, value is modified time.
    Recurses.
    """
    files = {}
    contents = os.listdir(dirPath)
    for c in contents:
        if os.path.isdir(dirPath + os.sep + c):
            #recurse. Note that "." and ".." are not returned by os.listdir, so no worries there.
            subfiles = getFiles(dirPath + os.sep + c)
            for (fname, modtime) in subfiles.items():
                files[c + os.sep + fname] = modtime
        else:
            files[c] = os.path.getmtime(dirPath + os.sep + c)
    return files

class CacheUnlessFilesChanged(object):
    """
    Decorator. Acts on functions that take a directory as their input and return a result.
    Produces a pickled file in a neighboring directory ../{dirName}_cache containing the function's result.
    Then, if the function is called again with the directory contents unchanged, results are loaded from the pickled file
    and returned instead.

    Keep in mind, this doesn't help you if you change the way the function works. This code does not attempt
    to track changes in your function's behavior, so if you change that, it's up to you to go delete the cache.
    """

    def __init__(self, f):
        self.f = f

    def checkCache(self, dirPath):
        if not os.path.isfile(self.cacheFilePath):
            #cache doesn't exist
            return False
        
        fh = open(self.cacheFilePath,'rb')
        (results, fileList) = pickle.load(fh)
        fh.close()

        
        #check if file names and dates line up
        currentFiles = getFiles(dirPath)
        if len(currentFiles) != len(fileList):
            #files were added / removed, so cache is invalid
            return False
        
        for (fileName, modTime) in currentFiles.items():
            if not fileName in fileList:
                #new file added that wasn't in the cache
                return False
            if fileList[fileName] != modTime:
                #file in cache was updated since caching
                return False
        
        #all the files line up. Cache is valid!
        return results
    
    def saveToCache(self, results):
        fileList = getFiles(self.dirPath)
        if not os.path.isdir(self.cacheDir):
            os.makedirs(self.cacheDir)
        fh=open(self.cacheFilePath,'wb')
        pickle.dump((results, fileList), fh, -1)
        fh.close()

    def __call__(self, dirPath):
        cacheDir = dirPath
        if cacheDir[-1] == os.sep:
            cacheDir = cacheDir[0:-1] #saw off the "\"
        cacheDir += "_cache"  
       
        self.dirPath = dirPath
        self.cacheDir = cacheDir
        self.cacheFilePath = cacheDir + os.sep + "cache.pkl"        
            
        results = self.checkCache(dirPath) #returns either False or cached results
        if results:
            #print "using cached result"
            return results
        else:
            #compute results and save to cache
            #print "cache invalid, computing result"
            results = self.f(dirPath)
            self.saveToCache(results)
            return results
        
@CacheUnlessFilesChanged
def test_cache(inDir):
    return inDir.upper()

if __name__ == "__main__":
    print test_cache(r"C:\wallpaper")