from __future__ import division
import sys
sys.path.append("..")


import os
import shutil

from util.collection_utils import *
from constants.graph_constants import *

def get_server_data():
    """Called from UI. Gets all shrew data (excluding video) from the standard network location."""
    serverPath = r"\\mpfi.org\Public\Fitzlab\ShrewData"
    localPath = DATA_DIR
    copy_shrew_data(serverPath, localPath)

def get_filenames_in(directory):
    """
    Returns a list of all files under the given directory.
    """

    print("Reading files in " + directory)
    ls = []
    nFiles = 0
    for root, dirs, filenames in os.walk(directory):
        for d in dirs:
            ls.append(root + os.sep + d)
        for f in filenames:
            if f.endswith("txt"):
                nFiles += 1
                ls.append(root + os.sep + f)
                if nFiles % 50 == 0:
                    print("  " + directory + ": " + str(nFiles) + " files found.")
    return ls


def copy_shrew_data(inDir, outDir, overwrite=False):
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
    pass