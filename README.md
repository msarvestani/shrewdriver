ShrewDriver
===========

Automated training system for training tree shrews to discriminate visual stimuli. Originally coded by Theo Walker circa 2012, then modified by Matt McCann, and a bit by Madineh Sarvestani, all members of Fitzpatrick lab at MPFI.

Core Python code is in the ShrewDriver directory. "shrewdriver.py" runs training. 

"shrew_graphs.py" is a tool for analysis and display of historical training data. Details of invididual sessions as well as overall performance history can be viewed.

PyQt is used for UI. Plotting is done using the excellent [pyqtgraph library](https://github.com/pyqtgraph/pyqtgraph).

Visual stimuli for monitors using the PsychoPy library. ShrewDriver can also display to Nexus 10 tablets; code for the Nexus 10 display app is in the Stimbot directory.

Firmware for the electronic components (sensors, syringe pump, and air puff) is in the Arduino directory.
"# shrewdriver" 

Eyetracking camera is PointGrey, controlled by flycpature which integrates with python. See notes on on setting up flycapture2 using python 2.7 [here](https://docs.google.com/document/d/1mZ2dGPB34mWH2FYYXsnw2rjmyVcFWtj5UnZAEjEzjXg/edit#heading=h.qheoagm4vwag)
