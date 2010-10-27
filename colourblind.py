import numpy as np

#A set of safe plotting colours from http://jfly.iam.u-tokyo.ac.jp/color/
rgb = np.array([[0,0,0],[230,159,0],[86,180,233],[0,158,115],[240,228,66],[0,114,178],[213,94,0],[204,121,167]])
rgbScaled = rgb/255.0


#Colormaps from
#A. Light & P.J. Bartlein, "The End of the Rainbow? Color Schemes for
#Improved Data Graphics," Eos,Vol. 85, No. 40, 5 October 2004.
#http://geography.uoregon.edu/datagraphics/EOS/Light&Bartlein_EOS2004.pdf
def makeMap(inMap,name):
  import numpy
  import matplotlib
  inMap = numpy.array(inMap)/255.0
  return matplotlib.colors.LinearSegmentedColormap.from_list(name,inMap)
  
blueMap = makeMap([[243,246,248],[224,232,240],[171,209,236],[115,180,224],[35,157,213],[0,142,205],[0,122,192]],'cbBlue')
blueGrayMap = makeMap([[0,170,227],[53,196,238],[133,212,234],[190,230,242],[217,224,230],[146,161,170],[109,122,129],[65,79,81]],'cbBlueGray')
brownBlueMap = makeMap([[144,100,44],[187,120,54],[225,146,65],[248,184,139],[244,218,200],[241,244,245],[207,226,240],[160,190,225],[109,153,206],[70,99,174],[24,79,162]],'cbBrownBlue')
redBlueMap = makeMap([[175,53,71],[216,82,88],[239,133,122],[245,177,139],[249,216,168],[242,238,197],[216,236,241],[154,217,238],[68,199,239],[0,170,226],[0,116,188]],'cbRedBlue')