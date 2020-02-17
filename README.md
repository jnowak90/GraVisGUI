# GraVis
Python GUI for GraVis, a network-based shape descriptor.
Please cite the following paper if you use the tool:

   Nowak, J., Eng, R.C., Matz, T., Waack, M., Persson, S., Sampathkumar, A. and Nikoloski, Z.
   A network-based framework for shape analysis enables accurate characterization and classification of leaf epidermal cells.
   Submitted to *Science Advances*.

## Contents
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Shape Description](#shape-description)
  - [Shape Comparison](#shape-comparison)
  - [Complexity Heatmap](#complexity-heatmap)
  - [Demo](#demo)
  - [Troubleshooting](#troubleshooting)

## Requirements
GraVis and its graphical user interface (GUI) were written in Python 3 and can be downloaded as an executable file for all major operating systems. To run the GUI, no installation of Python is needed.

## Installation
Simply download the respository and double click the executable file (depending on your operating system):
  - GraVis.app (OSX)
  - GraVis.exe (Windows)
  - GraVis. (Linux)

Example data is available in the demo folder. For further information read the README.

## Shape Description
GraVis uses the concept of visibility graphs to describe global and local features of shapes. While GraVis was mainly developed to describe the shape of pavement cells (PCs) of leaves, it can also be used for shape description of other shapes.
To start the shape description, an image or an image folder has to be selected. If a folder is selected, the first image in the analysis pipeline will be displayed.
In the next step, the type of image to be analyzed has to be selected. If pavement cells are selected, the details of the analysis pipeline can be chosen:
  - image pre-processing only
  - graph extraction only
  - both image pre-processing and graph extraction

The image pre-processing pipeline automatically detects noise or artificial edges in the image and remove them. If the pre-processing is not satisfying for the user, some of these steps can be enforced by ticking the corresponding boxes. If the plotting of intermediate steps is selected, the binary and skeletonized images of  PC outlines are saved in the output folder. After completing the pre-processing, the image with the segmented and labeled PCs will be displayed on the right side.
For the graph extraction the resolution of the image has to be provided. Furthermor, the graph extraction is only working if the selected image(s) were pre-processed beforehand.

![Shape description PCs](/images/GraVisGUI_description_PCs.png)

If other shapes were selected for the analysis, the user has to provide binary images and has to provide the distance between nodes along the shapes (in pixel/node). The analysis pipeline is started by pressing "Run". The progress of the analysis will be printed in the log on the right side.

![Shape description other](/images/GraVisGUI_description_other.png)

## Shape Comparison
To measure the similarity of different shapes, we implemented an algorithm to calculate the distance between visibility graphs. The user has to provide a single or multiple sets of visibility graphs by clicking "Add graphs" (.gpickle files).

![Shape comparison single](/images/GraVisGUI_comparison_single.png)

If more than one graph set is selected, the user has to add labels for each set. All graphs can be removed with "Remove graphs".

![Shape comparison multiple](/images/GraVisGUI_comparison_multiple.png)

Starting the comparison will generate a distance matrix of the input graphs. Here, the user can select if plots of the PCA or clustering dendrogram should be displayed on the right side.

Due to computational limits, the total number of input graphs should not exceed 200.

## Complexity Heatmap
The complexity of visibility graphs can be displayed in a heatmap with the following code:

```python
import numpy as np
import pandas as pd
import networkx as nx
import pickle
import skimage
from skimage import io, morphology
from skimage.morphology import disk
import matplotlib
import matplotlib.pyplot as plt

# import the following files from the results folder of the analyzed image (enable plotting of intermediate steps)
branchless = skimage.io.imread('branchlessSkeleton.png') > 0
table = pd.read_csv('ShapeResultsTable.csv', index_col=0)
visGraphs = pickle.load(open('visibilityGraphs.gpickle', 'rb'))

# expand contours of pavement cells
dilation = skimage.morphology.binary_dilation(branchless, disk(1))
binaryBranchless = np.ma.masked_where(dilation == 0, dilation)

# extract complexity values from table
complexity = list(table['Complexity'])

# create color map for graph complexity
oranges = matplotlib.cm.get_cmap('Oranges_r', 256)
newcolors = np.vstack((oranges(np.linspace(0, 0.2, 100)),
                       oranges(np.linspace(0.2, 1, 156))))
cmapCells = matplotlib.colors.ListedColormap(newcolors, name='Orange')

# plot heatmap
fig, ax = plt.subplots(1, 1, figsize=(5, 6))
plt.imshow(branchless * 0, cmap='gray_r', zorder=0)
for label in visGraphs.keys():
    graph = visGraphs[label]
    pos = nx.get_node_attributes(graph, 'pos')
    posT = {}
    for key in pos.keys():
        posT[key] = [pos[key][1], pos[key][0]]
    rgba = cmapCells(complexity[label - 1])
    col = matplotlib.colors.rgb2hex(rgba)
    nx.draw_networkx(graph, posT, node_size=0, edge_color=col, width=0.2, with_labels=False)
ax.imshow(binaryBranchless, cmap='gray', zorder=10)
ax.axes.get_yaxis().set_visible(False)
ax.axes.get_xaxis().set_visible(False)
plt.gca().axison = False
m = plt.cm.ScalarMappable(cmap=cmapCells)
m.set_array(np.arange(0, 1, 0.05))
cb = fig.colorbar(m, ax=ax, shrink=0.5)
axs = cb.ax
cb.ax.tick_params(direction='out',width=2,length=4,labelsize=10)
cb.set_label('delta')
plt.axis('off')
plt.show()
```
This will result in the following plot:

![PC Heatmap](/images/GraVisGUI_heatmapPCs.png)

## Demo
The demo folder inludes example images for pavement cells and other organisms, as well as extracted visibility graphs which can be used to test the GUI.
1. **WT_24h-GFP.tif**: image of Col-0 pavement cells
  - select Shape Description tab
  - open image
  - select "Pavement cells"
  - add image resolution 0.221 µm/px
  - press "Run"
2. **SandGrains_binary.png**: binary image of sand grains
  - select Shape Description tab
  - open image
  - select "Other"
  - add image resolution 20 px/node
  - press "Run"
3. **Col0_visgraphs.gpickle**: 10 extracted visibility graphs from images of Col-0 PCs
4. **DNROP2_visgraphs.gpickle**: 10 extracted visibility graphs from images of DN-ROP2 PCs
  - select Shape Comparison tab
  - add graph sets (one of them or both)
  - add labels for the graphs if both sets were added
  - select if you want to plot the PCA or clusetering dendrogram
  - press "Run"

## Troubleshooting
