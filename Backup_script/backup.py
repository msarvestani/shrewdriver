from __future__ import division

import os
import shutil

from collection_utils import *



def get_filenames_in(directory):
    """
    Returns a list of all files under the given directory.
    """
    ls = []
    contents = list(os.walk(directory))
    for root, dirs, filenames in contents:
        for d in dirs:
            ls.append(root + os.sep + d)
        for f in filenames:
            ls.append(root + os.sep + f)     
    return ls


def backup(inDir, outDir, overwrite=False):
    """
    Copies any new files from inDir to outDir.
    """
    if not os.path.isdir(outDir):
        os.makedirs(outDir)

    inFiles = get_filenames_in(inDir)
    print inFiles
    files_to_copy = []
    
    #Determine what to copy
    if overwrite:
        files_to_copy = inFiles
    else:
        outFiles = get_filenames_in(outDir)
        
        inFileSubPaths = [f.replace(inDir, "") for f in inFiles]
        outFileSubPaths = [f.replace(outDir, "") for f in outFiles]

        newFileSubPaths = list_subtract(inFileSubPaths, outFileSubPaths)
 
        newFiles = [inDir + f for f in newFileSubPaths]

        files_to_copy = newFiles
    

    #Perform copying
    nFiles = len(newFileSubPaths)
    print "Copying " + str(nFiles) + " files."
    percentDone = 0
    for i, f in enumerate(files_to_copy):
        if i/nFiles*100 > percentDone:
            print str(percentDone) + "% done"
            percentDone += 5

        if os.path.isdir(f):
            os.makedirs(f.replace(inDir, outDir))
        else:
            dest = f.replace(inDir, outDir)
            shutil.copyfile(f,dest)

    print "100% done!"

if __name__ == "__main__":
    backup(r"C:\Users\fitzlab1\Documents\ShrewData", r"Z:\ShrewData")
