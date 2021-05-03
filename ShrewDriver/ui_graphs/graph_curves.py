from __future__ import division
import sys
sys.path.append("..")

import numpy as np

from PyQt4 import QtCore, QtGui

from constants.graph_constants import *


class IntCurve:
    """
    Used by the Events graph.

    Curve for showing discrete events such as licks (off=0, on=1) or states (integers).
    Draws two lines and fills the space between them.
    """

    def __init__(self, name, index, color, yMax, pw):
        self.name = name
        self.yMin = index * 1.1

        self.x = [0]
        self.xBase = [0]
        self.y = [self.yMin]
        self.yBase = [self.yMin]
        self.yMax = yMax

        self.yPrev = 0
        self.xPrev = 0

        #init curve on plotwidget 'pw'
        self.sig = pw.plot(pen=color, name=self.name)
        self.sig.setData(self.x, self.y)
        self.base = pw.plot(pen=color)
        self.base.setData(self.xBase,self.yBase)
        fill = pg.FillBetweenItem(self.base, self.sig, color)
        pw.addItem(fill)

    def add_data(self, x, y):
        """
        x is typically a timestamp, y is an integer
        """

        #add point to curve
        self.x.append(x)
        self.y.append(self.yPrev/self.yMax + self.yMin)
        self.x.append(x)
        self.y.append(y/self.yMax + self.yMin)

        #update base curve
        self.xBase.append(x)
        self.yBase.append(self.yMin)

        self.xPrev = x
        self.yPrev = y

    def update(self, xNew=None):
        """
        We want to update more often than just when the state changes.
        We want users to know that the state has remained the same.
        xNew is usually a time value (epoch timestamp as given by time.time())
        """

        if xNew is None:
            self.sig.setData(self.x, self.y)
            self.base.setData(self.xBase, self.yBase)
        else:
            if len(self.y) > 0 and len(self.yBase) > 0:
                self.sig.setData(self.x + [xNew], self.y + [self.y[-1]])
                self.base.setData(self.xBase + [xNew], self.yBase + [self.yBase[-1]])

    def clear(self):
        self.x = []
        self.y = []
        self.xBase = []
        self.yBase = []
        self.update(None)



class ThresholdCurve(object):
    """
    Used by the Sensors graph.

    Holds the data for a curve and a threshold, so that users can
    easily tell when the curve is above / below the threshold value.

    Object uses several "curves" internally. This is because adding
    data to a single curve gets progressively slower as the curve gets longer.
    So once a curve reaches a certain length, another curve is started.
    """

    #constants
    MAX_CURVE_ELEMENTS = 5000

    def __init__(self, pw):
        self.plot = pw

        self.t = []
        self.y = []
        self.curves = []

        self.threshold = 0
        self.color = (255,255,255)

        #make first curve
        self.curves.append(pg.PlotCurveItem([], []))
        self.curves[0].setFillLevel(self.threshold)

    def add_data(self, t, y):
        # So we just make another curve if the current curve is too long
        if len(self.t) > self.MAX_CURVE_ELEMENTS:
            newCurve = pg.PlotCurveItem([], [])

            #visual properties
            newCurve.setFillLevel(self.threshold)
            newCurve.setFillLevel(self.threshold)
            pColor = self.color + (255,)
            bColor = self.color + (80,)
            newCurve.setPen(pColor)
            newCurve.setBrush(bColor)

            self.curves.append(newCurve)
            self.plot.addItem(self.curves[-1])

            self.t = []
            self.y = []

        #add point
        self.t.append(t)
        self.y.append(y)

        #update
        if len(self.t) == len(self.y):
            self.curves[-1].setData(self.t,self.y)
        else:
            #This happened (very rarely) in testing.
            #Maybe a race condition? Anyway, safe to ignore.
            pass

    def set_color(self, color):
        """Draw the curve in the given color and shade below"""
        self.color = color

        pColor = self.color + (255,) #alpha of 255 (pen)
        bColor = self.color + (80,) #alpha of 80 (shading)
        for curve in self.curves:
            curve.setPen(pColor)
            curve.setBrush(bColor)

    def set_threshold(self, threshold):
        self.threshold = threshold
        for curve in self.curves:
            curve.setFillLevel(threshold)


class LineDotCurve():

    def __init__(self, pw, name):

        self.plot = pw
        self.name = name
        self.color = get_color(name)

        self.dotCurve = pg.ScatterPlotItem(size=8, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 120))
        self.lineCurve = pg.PlotCurveItem(pen=pg.mkPen(255, 255, 0, 255))

        self.plot.addItem(self.dotCurve)
        self.plot.addItem(self.lineCurve)

        self.xpoints = []
        self.ypoints = []
        self.data = []  # Array of strings containing info on each point. Optional.

        self.show()  # ensures coloring happens

    def set_color(self, color):
        self.color = color


    def clear(self):
        self.xpoints = []
        self.ypoints = []
        self.data = []
        self.update()

    def add_data(self, x, y, data=""):
        """
        Add data to the curve. Does not actually update the curve displayed -- call update() to do that.

        Scatter plots have an additional "data" field which can store additional information about a point.
        For example, the metadata can display when a user clicks on the point.
        """
        self.xpoints.append(x)
        self.ypoints.append(y)
        self.data.append(data)

    def update(self):
        """
        Changes the actual curve data, causing a screen update. (Slow.)
        """
        scatterPoints = [{'pos': [self.xpoints[i], self.ypoints[i]], 'data': self.data[i]} for i in range(len(self.xpoints))]
        self.dotCurve.setPoints(scatterPoints)
        self.lineCurve.setData(self.xpoints, self.ypoints)


    def hide(self):
        self.lineCurve.setPen(None)
        self.lineCurve.setBrush(None)
        self.dotCurve.setPen(None)
        self.dotCurve.setBrush(None)

    def show(self):
        linePen = pg.mkPen(self.color + (255,))
        self.lineCurve.setPen(linePen)
        dotBrush = pg.mkBrush(self.color + (120,))
        self.dotCurve.setBrush(dotBrush)


class HistogramCurve:

    def __init__(self):
        ## make interesting distribution of values
        vals = np.hstack([np.random.normal(size=500), np.random.normal(size=260, loc=4)])

        ## compute standard histogram
        y,x = np.histogram(vals, bins=np.linspace(-3, 8, 40))

        ## Using stepMode=True causes the plot to draw two lines for each sample.
        ## notice that len(x) == len(y)+1
        plt1.plot(x, y, stepMode=True, fillLevel=0, brush=(0,0,255,150))

        ## Now draw all points as a nicely-spaced scatter plot
        y = pg.pseudoScatter(vals, spacing=0.15)
        #plt2.plot(vals, y, pen=None, symbol='o', symbolSize=5)
        plt2.plot(vals, y, pen=None, symbol='o', symbolSize=5, symbolPen=(255,255,255,200), symbolBrush=(0,0,255,150))

        ## Start Qt event loop unless running in interactive mode or using pyside.
        if __name__ == '__main__':
            import sys
            if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
                QtGui.QApplication.instance().exec_()
