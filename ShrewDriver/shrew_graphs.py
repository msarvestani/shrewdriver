from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, uic

from ui import graph_ui

"""
Displays many graphs of shrew performance.

The graphs are generated using data stored in your local "ShrewData" folder. Data must be copied from the server and
then processed before you can see it on the graphs. Use buttons in upper right of UI to copy and process data.

Note that data from all four training rigs is automatically copied to the server each night.
This is implemented using Windows's "Scheduled Task" feature, which runs a Python script located in
the "ShrewDriver\Backup Script" directory.

Processed data is stored in db files, e.g. "Bernadette_events.db". If you change the analysis code,
you should delete the .db files in ShrewData and re-generate them by running "Process Local Data" from the UI.
"""

if __name__ == '__main__':
    print "Loading shrew data..."
    app = QtGui.QApplication(sys.argv)
    graphUI = graph_ui.GraphUI(None)
    graphUI.show()
    app.exec_()
