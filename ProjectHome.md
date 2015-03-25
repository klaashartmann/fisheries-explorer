# Fisheries Explorer #

Fisheries Explorer is an instructional tool for exploring fisheries management and economics. It was developed as a component of the Fisheries Economics Masterclass run by the Australian Seafood CRC and the University of Tasmania.

## How to Use it ##

Fisheries Explorer is designed to reinforce economic principles and concepts in an interactive manner. It is not a fisheries economics course and should be used by those with some familiarity with economics or in conjunction with a fisheries economics class.

Currently a single fishery - a generic rock lobster fishery - is included in the program and a worksheet is available for download. Further fisheries and more instructional material will be made available in future.

**Windows Installation**

Download the installation executable on the right (under the heading "Featured Downloads") and run it.

**Linux Installation**

I have yet to create a package. Download the Source using svn and run fisheries\_gui.py. Prerequisites are wxPython and scipy.

**Mac Installation**

I do not have access to a Mac, so this remains untested. Following the steps for Linux may work -- please let me know how you go.

## Expanding Fisheries Explorer ##

New fisheries can easily be added to the Fisheries Explorer with minimal programming. It has been designed in a modular fashion to enable straightforward inclusion of different fishery models with arbitrary sets of parameters. For example the entire rock lobster model included is defined in a total of 72 lines of code.

It has been designed as a tool for teaching economic principles using simple idealised fisheries and not as a front-end for real fishery models. As such incorporating advanced features such as large numbers of spatial zones and MSE would be difficult using the current interface. It is also questionable whether such complexities are required to illustrate basic fisheries economics principles.