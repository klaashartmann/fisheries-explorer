#import matplotlib as mp
#mp.use('GTK')
#from matplotlib.figure import Figure
#from matplotlib.pyplot import show

import matplotlib.pyplot as plt
figure = plt.figure()

pos = [.1,.1,.8,.8]
pos2 = list(pos)
pos2[2]=.75
print pos
print pos2
ax1 = figure.add_axes(pos, frameon = False,label ='a')
ax2 = figure.add_axes(pos2, frameon = False,label = 'b')
ax1.yaxis.tick_right()
ax1.yaxis.set_label_position('right')
ax2.yaxis.tick_right()
ax2.yaxis.set_label_position('right')

ax1.set_ylabel('fda')
ax2.set_ylabel('$')
ax1.plot([0,1],[1,2],'r:')
ax2.plot([0,1],[10,1],'g-')
plt.show()
