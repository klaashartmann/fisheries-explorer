#By running "python setup_osx.py py2app" this script generates a OSX stand-alone
#distribution of the Fisheries Explorer
#Copyright 2016, University of Tasmania, Australian Seafood CRC
#This program is released under the Open Software License ("OSL") v. 3.0. See OSL3.0.htm for details.

from setuptools import setup



APP = ['fisheries_gui.py']
DATA_FILES = ['images','images/about.png','images/fish.ico','images/fish.png','images/fishnet.ico','images/fishnet.png','images/seafoodcrc.png','images/Top Menu_fishing boats.gif']
OPTIONS = {'argv_emulation': True}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
