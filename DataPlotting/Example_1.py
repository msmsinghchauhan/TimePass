from matplotlib import pyplot as plt
import numpy as np
import random


#plotting a simple graph

# plot function takes x and y coordinates and plot the graph,here y is mandatory and x is optional parameter if user
# does not provide x coordinates then it will take default x coordinates as 0,1,2,3,4,5,6,7,8,9 and so on which is index of y coordinates
# The third parameter is the format string that indicates the color and line type of the plot for example 'ro' means red color and circle marker
# 'b-' means blue color and solid line below are all the possible values of format string   https://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.plot
# The fourth parameter of plot function is optional and it is used to set the label of the graph for example plt.plot([1, 2, 3, 4], [1, 4, 9, 16], 'ro',label='square of x')

#plt.plot([1, 2, 3, 4], [1, 4, 9, 16], 'ro')
#plt.show()

#plt.plot([1, 4, 9, 16] )
#plt.show()
x = random.sample(range(1, 10000), 1000)
y=[i*i for i in x]
plt.plot(x, y, 'ro',label='square of x')
plt.ylabel('square of x coordinate')
plt.xlabel(' random generated x cordinate values')
plt.show()




