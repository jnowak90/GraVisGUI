from tkinter import *
from tkinter import Tk, Label, Button, Frame, Canvas, Entry, Checkbutton, Radiobutton, OptionMenu, ttk, messagebox, filedialog
from tkinter.ttk import Notebook
import tkinter.scrolledtext as ScrolledText
from PIL import Image, ImageTk
import logging
import os
import sys
import numpy as np
from numpy import linalg
import glob
import skimage
from skimage import io, color, morphology, filters, transform, measure, exposure, restoration, feature, draw
from skimage.morphology import disk
from skimage.util import dtype
import scipy as sp
from scipy import ndimage, stats, spatial, cluster
import itertools
import pandas as pd
import networkx as nx
from packaging.version import Version
import math
import shapely
from shapely import geometry
import pickle
import time
import sklearn
from sklearn import decomposition
import matplotlib
from matplotlib.legend_handler import HandlerPatch
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

# add class for logging messages
class LogHandler(logging.Handler):

    def __init__(self, text):
        logging.Handler.__init__(self)
        self.text = text

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text.configure(state='normal')
            self.text.insert(END, msg + '\n')
            self.text.configure(state='disabled')
            self.text.yview(END)
        self.text.after(0, append)

# create circles for legend in visual output
class HandlerEllipse(HandlerPatch):
    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize, trans):
        center = 0.5 * width - 0.5 * xdescent, 0.5 * height - 0.5 * ydescent
        p = matplotlib.patches.Ellipse(xy=center, width=width*0.5, height=width*0.5)
        self.update_prop(p, orig_handle, legend)
        p.set_transform(trans)
        return [p]

##### GUI #####
class ShapeGui:

    def __init__(self, root):
        self.root = root
        self.fileName = ""
        self.lastDir = ""
        self.fileType = ""
        self.fileList = ""
        self.scriptPath = os.path.abspath(os.getcwd())

        ### settings for adjustable GUI size
        self.root.title('GraVis - a Network-Based Shape Descriptor')
        self.height = int(self.root.winfo_screenheight() * 0.9)
        self.width = int(self.height * 1.25)
        self.root.geometry('%dx%d' % (self.width, self.height))

        ##### tabs #####
        self.tabParent = ttk.Notebook(self.root)
        self.tabHome = Frame(self.tabParent)
        self.tabDescription = Frame(self.tabParent)
        self.tabComparison = Frame(self.tabParent)
        self.tabParent.add(self.tabHome, text="Home")
        self.tabParent.add(self.tabDescription, text="Shape Description")
        self.tabParent.add(self.tabComparison, text="Shape Comparison")
        self.tabParent.pack(expand=1, fill='both')
        self.widthTab = int(self.width * 0.5)
        self.origColor = self.tabDescription.cget("background")

        ### home frame
        self.FrameHome = Frame(self.tabHome, width=self.width, height=self.height)
        self.FrameHome.grid(row=0, column=0, padx=5, pady=5)
        self.labelWelcome = Label(self.FrameHome, text="Welcome to GraVis, a framework for network-based \nshape description and comparison.", justify=LEFT, font=(None, 14)).grid(row=0, column=0, sticky=W, padx=20, pady=40)
        self.labelDescriptionHeader = Label(self.FrameHome, text="Shape description", justify=LEFT, font=(None, 12, 'bold')).grid(row=1, column=0, sticky=W, padx=20)
        self.labelDescription = Label(self.FrameHome, text="To describe pavement cell shapes, images are pre-processed to segment individual cells. For each cell a visibility graph \nis then created which can be used for shape comparison or to detect lobes and necks.\n\nInput: images of pavement cells (.tif, .png. .jpg), or binary images of other shapes (.tif, .png, .jpg) \nOutput: visibility graphs (.gpickle files) \n\n1. Select an image or image folder. \n2. Select the analysis of pavement cells or other shapes. \n3. Select parameters for analysis. \n4. Press 'Run' to start analysis.", justify=LEFT, font=(None, 12)).grid(row=2, column=0, sticky=NW, padx=20)
        self.labelComparisonHeader = Label(self.FrameHome, text="\nShape comparison", justify=LEFT, font=(None, 12, 'bold')).grid(row=3, column=0, sticky=W, padx=20)
        self.labelComparison = Label(self.FrameHome, text="Shapes are compared by calculating the distance between their visibility graphs. If a single set of visibility graphs is \nselected, each graph is assigned a numerical label. If multiple sets of visibility graphs are selected, the user \nhas to assign labels.\n\nInput: visibility graphs (gpickle files) \nOutput: distance matrix (.npy file)\n\n1. Add graphs for the computation of the distance matrix. \n2. Add labels to graphs if more than one set was selected. \n3. Select optional plots. \n4. Press 'Run' to start analysis.", justify=LEFT, font=(None, 12)).grid(row=4, column=0, sticky=NW, padx=20)

        ### shape description frame
        self.FrameDescription = Frame(self.tabDescription, width=self.widthTab, height=self.height)
        self.FrameDescription.grid(row=0, column=0, padx=5, pady=5)
        self.buttonOpenImage = Button(self.FrameDescription, text="Open Image", command=self.select_and_show_image).grid(row=0, column=0, sticky=E)
        self.buttonOpenFolder = Button(self.FrameDescription, text="Open Folder", command=self.select_and_show_folder).grid(row=0, column=1, sticky=W)
        self.canvasOriginal = Canvas(self.FrameDescription, width = int(self.widthTab*0.45), height = int(self.widthTab*0.45), bg='honeydew')
        self.canvasOriginal.create_text(50, 50, text="First select an image or \nan image folder.", anchor=W, tag="textCanvas")
        self.canvasOriginal.grid(row=1, column=0, padx=5, pady=5, sticky=N, columnspan=2)
        self.settingsDescription = Frame(self.FrameDescription, width=self.widthTab)
        self.settingsDescription.grid(row=2, column=0, sticky=W, columnspan=2)
        self.labelSelectionImages = Label(self.settingsDescription, text="What kind of image(s) do you want to analyze?", anchor=W, justify=LEFT).grid(row=0, column=0)
        self.selectedImages = StringVar()
        self.buttonPavementCells = Radiobutton(self.settingsDescription, text="Pavement Cells", value="pavement", var=self.selectedImages, command=self.select_settings).grid(row=1, column=0, sticky=W)
        self.buttonOthers = Radiobutton(self.settingsDescription, text="Other",value="other", var=self.selectedImages, command=self.select_settings).grid(row=2, column=0, sticky=W)
        self.parametersDescription = Frame(self.FrameDescription, width=self.widthTab)
        self.parametersDescription.grid(row=3, column=0, columnspan=2)
        self.labelSegemented = Label(self.FrameDescription, text="Segmented image:", anchor=W, justify=LEFT).grid(row=0, column=2, sticky=W)
        self.quitDescription = Button(self.FrameDescription, text="Exit", command=self.root.destroy, highlightbackground='medium sea green').grid(row=0, column=3, sticky=E)
        self.canvasSegmented = Canvas(self.FrameDescription, width = int(self.widthTab*0.8), height = int(self.widthTab*0.8), bg='honeydew')
        self.canvasSegmented.grid(row=1, column=2, rowspan=2, columnspan=2)
        self.scrolltext = ScrolledText.ScrolledText(self.FrameDescription, state='disabled')
        self.scrolltext.configure(font='TkFixedFont', background='snow2', height=int(self.widthTab*0.45/15), width=int(self.widthTab*0.8/7.5))
        self.textHandler = LogHandler(self.scrolltext)
        logging.basicConfig(filename='GraVis.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger()
        self.logger.addHandler(self.textHandler)
        self.scrolltext.grid(row=3, column=2, columnspan=2, pady=10)

        ### shape comparison Frame
        self.FrameComparison = Frame(self.tabComparison, width=self.widthTab, height=self.height)
        self.FrameComparison.grid(row=0, column=0, padx=5, pady=5)
        self.graphCounter = 0
        self.buttonAddGraph = Button(self.FrameComparison, text="Add graphs", command=self.select_graphs).grid(row=0, column=0, sticky=E)
        self.buttonRemoveGraph = Button(self.FrameComparison, text="Remove graphs", command=self.remove_graphs).grid(row=0, column=1, sticky=W)
        self.labelComparisonGraphs = Label(self.FrameComparison, text="Select your visibility graphs for the shape comparison by \nclicking 'Add graphs.'").grid(row=1, column=0, columnspan=2, sticky=W)
        self.labelDateSet = Label(self.FrameComparison, text="Data set").grid(row=2, column=0, sticky=NW)
        self.dataKeys = ["data1", "data2", "data3", "data4", "data5", "data6", "data7"]
        self.entriesDict = {}
        self.graphsDict = {}
        self.selectedGraphs = Frame(self.FrameComparison, width=self.widthTab)
        self.selectedGraphs.grid(row=3, column=0, columnspan=2, sticky=NW)
        self.settingsComparison = Frame(self.FrameComparison, width=self.widthTab)
        self.settingsComparison.grid(row=4, column=0, columnspan=2, sticky=SW)
        self.labelPlotChoice = Label(self.settingsComparison, text="Selected output of distance matrix: \n(if none is selected, only the distance matrix is saved).", justify=LEFT).grid(row=0, column=0, sticky=W)
        self.varPCA = IntVar()
        self.varDend = IntVar()
        self.checkPCA = Checkbutton(self.settingsComparison, text="plot PCA", variable=self.varPCA).grid(row=1, column=0, sticky=W)
        self.checkDend = Checkbutton(self.settingsComparison, text="plot dendrogram", variable=self.varDend).grid(row=2, column=0, sticky=W)
        self.RunComparison = Button(self.settingsComparison, text="Run Comparison", highlightbackground='medium sea green', command=self.start_comparison).grid(row=3, column=0, padx=20, pady=10)
        self.quitComparison = Button(self.FrameComparison, text="Exit", command=self.root.destroy, highlightbackground='medium sea green').grid(row=0, column=2, sticky=E)
        self.canvasPlotPCA = Canvas(self.FrameComparison, width = int(self.widthTab*0.75), height=int(self.widthTab*0.75))
        self.canvasPlotPCA.grid(row=1, column=2, rowspan=3, sticky=NE)
        self.canvasPlotDend = Canvas(self.FrameComparison, width=int(self.widthTab*0.75), height=int(self.widthTab*0.65))
        self.canvasPlotDend.grid(row=4, column=2, sticky=NE)

    ##### FUNCTIONS #####
    def display_image(self, imagePath, imageWidth, imageHeight):
        """
        open and show selected images
        """
        imageRaw = Image.open(imagePath)
        if imageHeight != None:
            imageResized = imageRaw.resize((int(self.widthTab * imageWidth), int(self.widthTab * imageHeight)), Image.ANTIALIAS)
        else:
            imageResized = self.resize_image(imageRaw, int(self.widthTab * imageWidth))
        imagePlot = ImageTk.PhotoImage(imageResized)
        return(imagePlot)

    def resize_image(self, image, size):
        """
        resize input image to canvas size
        """
        if image.size[0] == image.size[1]:
            resized = image.resize((size, size), Image.ANTIALIAS)
        else:
            maxSize, argmaxSize = np.max(image.size), np.argmax(image.size)
            minSize = int((np.min(image.size) * size) / maxSize)
            if argmaxSize == 0:
                resized = image.resize((size, minSize), Image.ANTIALIAS)
            else:
                resized = image.resize((minSize, size), Image.ANTIALIAS)
        return(resized)

    def select_and_show_image(self):
        """
        select image and show in canvas
        """
        if self.lastDir == "":
            self.lastDir = './'
        self.fileName = filedialog.askopenfilename(initialdir=self.lastDir, title="Select image!", filetypes=(("png images", "*.png"), ("tif images", "*.tif"), ("tif images", "*.TIF"), ("tif images", "*.tiff"), ("tif images", "*.TIFF"), ("tif images", "*.jpeg"), ("jpeg images", "*.jpg")))
        self.fileType = "image"
        self.display_original_image(self.fileName)
        if self.fileName != "":
            self.lastDir = os.path.dirname(self.fileName)
        show_Message("Opened image: " + self.fileName)

    def select_and_show_folder(self):
        """
        select image folder and show first image in canvas
        """
        if self.lastDir == "":
            self.lastDir = './'
        self.directoryName = filedialog.askdirectory()
        self.fileType = "directory"
        self.fileList = [item for sublist in [glob.glob(self.directoryName + ext) for ext in ["/*.png", "/*.jpg", "/*.jpeg", "/*.tif", "/*.tiff", "/*.TIF", "/*.TIFF"]] for item in sublist]
        self.fileName = self.fileList[0]
        self.display_original_image(self.fileName)
        show_Message("Selected image folder: " + self.directoryName)
        show_Message("Detected " + str(len(self.fileList)) + " image files in the folder.")

    def display_original_image(self, filename):
        """
        plot original image in canvas
        """
        self.imageOriginal = self.display_image(filename, 0.45, None)
        self.canvasOriginal.create_image(0, 0, anchor=NW, image=self.imageOriginal)
        self.canvasOriginal.config(background=self.origColor)
        self.canvasOriginal.delete("textCanvas")

    def display_segmented_image(self, image, pathToFolder, msg):
        """
        plot segmentation image in canvas
        """
        self.imageSegmented = self.display_image(pathToFolder + image, 0.8, None)
        self.canvasSegmented.create_image(0, 0, anchor=NW, image=self.imageSegmented)
        self.canvasSegmented.config(background=self.origColor)
        show_Message(msg)

    def select_settings(self):
        """
        display different settings for PCs and other shapes
        """
        if self.selectedImages.get() == 'pavement':
            self.parametersPCs = Frame(self.FrameDescription, width=self.widthTab)
            self.parametersPCs.grid(row=3, column=0, sticky='nsew', columnspan=2)
            self.varAnalysis = StringVar()
            self.analysisChoices = {'Pre-processing & Graph extraction', 'Pre-processing', 'Graph extraction'}
            self.varAnalysis.set('Pre-processing & Graph extraction')
            self.dropdownAnalysis = OptionMenu(self.parametersPCs, self.varAnalysis, *self.analysisChoices, command=self.show_settings_PCs).grid(row=0, column=0, sticky=W)
            self.show_settings_PCs(self.varAnalysis)
        else:
            self.parametersOther = Frame(self.FrameDescription, width=self.widthTab)
            self.parametersOther.grid(row=3, column=0, sticky='nsew', columnspan=2)
            self.labelAnalysisOther = Label(self.parametersOther, text="Please provide binary images for the analysis \nof other objects. If an image folder was selected, \nthe visibility graphs of all images in the folder \nwill be saved in one file.", anchor=W, justify=LEFT).grid(row=0, column=0, padx=20, pady=20, sticky=W)
            self.graphextractionSettings(self.parametersOther)
            self.RunDescription = Button(self.parametersOther, text="Run Analysis", highlightbackground='medium sea green', command=self.start_description_other)
            self.labelResolution.grid(row=1, column=0, padx=20, sticky=W)
            self.addResolution.grid(row=2, column=0, padx=20, pady=10, sticky=W)
            self.RunDescription.grid(row=3, column=0)

    def show_settings_PCs(self, ev):
        """
        show the different settings for PCs depending on the user's choice
        """
        if self.varAnalysis.get() == 'Pre-processing & Graph extraction':
            self.parameterChoices = Frame(self.parametersPCs, width=self.widthTab)
            self.parameterChoices.grid(row=1, column=0, sticky='nsew')
            self.preprocessingSettings(self.parameterChoices)
            self.graphextractionSettings(self.parameterChoices)
            self.RunDescription = Button(self.parameterChoices, text="Run Analysis", highlightbackground='medium sea green', command=self.start_description_PCs)
            self.labelPreprocessing.grid(row=0, column=0, padx=20, pady=10, sticky=W)
            self.checkEdges.grid(row=1, column=0, padx=20, sticky=W)
            self.checkNoise.grid(row=2, column=0, padx=20, sticky=W)
            self.checkRescaling.grid(row=3, column=0, padx=20, sticky=W)
            self.checkPlot.grid(row=4, column=0, padx=20, sticky=W)
            self.labelResolution.grid(row=5, column=0, padx=20, sticky=W)
            self.addResolution.grid(row=6, column=0, padx=20, sticky=W)
            self.RunDescription.grid(row=7, column=0)
        elif self.varAnalysis.get() == 'Pre-processing':
            self.parameterChoicesPP = Frame(self.parametersPCs, width=self.widthTab)
            self.parameterChoicesPP.grid(row=1, column=0, sticky='nsew')
            self.preprocessingSettings(self.parameterChoicesPP)
            self.RunDescription = Button(self.parameterChoicesPP, text="Run Analysis", highlightbackground='medium sea green', command=self.start_description_PCs)
            self.labelPreprocessing.grid(row=1, column=0, padx=20, pady=10, sticky=W)
            self.checkEdges.grid(row=2, column=0, padx=20, sticky=W)
            self.checkNoise.grid(row=3, column=0, padx=20, sticky=W)
            self.checkRescaling.grid(row=4, column=0, padx=20, sticky=W)
            self.checkPlot.grid(row=5, column=0, padx=20, sticky=W)
            self.RunDescription.grid(row=6, column=0)
        else:
            self.parameterChoicesGE = Frame(self.parametersPCs, width=self.widthTab)
            self.parameterChoicesGE.grid(row=1, column=0, sticky='nsew')
            self.labelGraphextraction = Label(self.parameterChoicesGE, text="This step should only be selected, if the pre-processing \nof this image was already done previously.", anchor=W, justify=LEFT)
            self.graphextractionSettings(self.parameterChoicesGE)
            self.RunDescription = Button(self.parameterChoicesGE, text="Run Analysis", highlightbackground='medium sea green', command=self.start_description_PCs)
            self.labelGraphextraction.grid(row=1, column=0, padx=20, sticky=W)
            self.labelResolution.grid(row=2, column=0, padx=20, sticky=W)
            self.addResolution.grid(row=3, column=0, padx=20, sticky=W)
            self.RunDescription.grid(row=4, column=0)

    def preprocessingSettings(self, settings):
        """
        settings for image pre-processing
        """
        self.labelPreprocessing = Label(settings, text="The following pre-processing steps can be enforced by ticking \nthe corresponding box(es) if not detected automatically. \nLeave unchecked if you want to use the default pipeline.", anchor=W, justify=LEFT)
        self.varEdges = IntVar()
        self.varNoise = IntVar()
        self.varRescaling = IntVar()
        self.varPlot = IntVar()
        self.checkEdges = Checkbutton(settings, text="enforce removal of artificial edges", variable=self.varEdges)
        self.checkNoise = Checkbutton(settings, text="enforce noise removal from image", variable=self.varNoise)
        self.checkRescaling = Checkbutton(settings, text="enforce rescaling of the image", variable=self.varRescaling)
        self.checkPlot = Checkbutton(settings, text="plot intermediate pre-processing steps", variable=self.varPlot)

    def graphextractionSettings(self, settings):
        """
        settings for graph extraction
        """
        self.varResolution = StringVar()
        if self.selectedImages.get() == 'pavement':
            self.labelResolution = Label(settings, text="\n\nImage resolution (µm/px):")
        else:
            self.labelResolution = Label(settings, text="\n\nPixel distance (px/node):")
        self.addResolution = Entry(settings, textvariable=self.varResolution)

    def start_description_PCs(self):
        """
        workflow for the shape description framework
        """
        if self.fileName != "":
            if self.fileType == "image":
                self.analyze_image(self.fileName)
            else:
                for file in self.fileList:
                    self.fileName = file
                    self.display_original_image(self.fileName)
                    self.canvasOriginal.update()
                    self.analyze_image(self.fileName)
            messagebox.showinfo("GraVis", "Analysis is done. \n\nResults were saved into: \n\n" + self.outputFolder)
            self.filename = ""
        else:
            messagebox.showinfo("Warning", "No image was selected. Please open an image first before starting the analysis.")

    def analyze_image(self, filename):
        """
        processing steps for PCs depending on user input
        """
        self.outputFolder = filename.split('.')[:-1][0]
        if not os.path.exists(self.outputFolder):
            os.mkdir(self.outputFolder)
        if self.varAnalysis.get() == 'Pre-processing':
            self.start_preprocessing()
        elif self.varAnalysis.get() == 'Graph extraction':
            self.preprocessedImage = None
            self.start_graphextraction()
        else:
            self.start_preprocessing()
            self.start_graphextraction()

    def start_preprocessing(self):
        """
        start pre-processing pipeline
        """
        msg = ""
        if self.varEdges.get() == 1:
            msg += "Selected artificial edge removal. "
        if self.varNoise.get() == 1:
            msg += "Selected noise removal. "
        if self.varRescaling.get() == 1:
            msg += "Selected image rescaling. "
        if self.varPlot.get() == 1:
            msg += "Selected plotting of intermediate steps."
        msg += "\nStart pre-processing of the image."
        show_Message(msg)
        self.preprocessedImage = Preprocessor(self.fileName, self.varEdges.get(), self.varNoise.get(), self.varRescaling.get(), self.varPlot.get(), self.outputFolder)
        self.display_segmented_image('/LabeledPavementCells.png', self.preprocessedImage.pathToFolder, "Show pre-processed image.")
        show_Message("..." + str(self.preprocessedImage.labels-1) + " cells were detected")

    def start_graphextraction(self):
        """
        start graph extraction pipeline
        """
        if self.varResolution.get() != "":
            show_Message("\nStart graph extraction for detected cells.")
            self.visibilityGraphs = VisGraph(self.preprocessedImage, self.varPlot.get(), self.varResolution.get(), self.outputFolder)
        else:
            messagebox.showinfo("Warning", "No resolution was provided. Please enter the image resolution and run the analysis again.")

    def start_description_other(self):
        """
        pipeline for description of other shapes
        """
        if self.fileName != "":
            show_Message("\nStart graph extraction.")
            self.outputFolder = "/".join(self.fileName.split('/')[:-1])
            self.visibilityGraphs = VisGraphOther(self.fileName, self.varResolution.get(), self.outputFolder, self.fileType, self.fileList)
            messagebox.showinfo("GraVis", "Analysis is done. \n\nResults were saved into: \n\n" + self.outputFolder)
            if self.fileType == 'image':
                self.display_segmented_image('/LabeledShapes.png', self.outputFolder, "")
            else:
                self.display_segmented_image('/LabeledShapes_1.png', self.outputFolder, "")
            self.filename = ""
        else:
            messagebox.showinfo("Warning", "No image was selected. Please open an image first before starting the analysis.")

    def select_graphs(self):
        """
        select visibility graphs for shape comparison
        """
        if self.graphCounter <= 6:
            if self.lastDir == "":
                self.lastDir = './'
            self.graphLocation = filedialog.askopenfilename(initialdir=self.lastDir, title="Select graph file.", filetypes=[("pickle files", "*.gpickle")])
            if self.graphLocation != "":
                self.lastDir = os.path.dirname(self.graphLocation)
            self.display_graphs()
            self.graphsDict[self.dataKeys[self.graphCounter]] = self.graphLocation
            self.graphCounter += 1
        else:
            messagebox.showinfo("Warning", "The maximal number of input graph sets is seven.")

    def remove_graphs(self):
        """
        remove all selected visibility graphs
        """
        for widget in self.selectedGraphs.winfo_children():
            widget.destroy()
        self.entriesDict = {}
        self.graphsDict = {}
        self.graphCounter = 0

    def display_graphs(self):
        """
        display selected visibility graphs
        """
        self.graphFileName = '.'.join(self.graphLocation.split('/')[-1].split('.')[:-1])
        if self.graphCounter == 0:
            firstLabel = Label(self.selectedGraphs, text=self.graphFileName, justify=LEFT).grid(row=self.graphCounter, column=0, sticky=NW)
        else:
            if self.graphCounter == 1:
                self.labelDataLabel = Label(self.FrameComparison, text="Label", justify=LEFT).grid(row=2, column=1, sticky=NW)
                firstVar = StringVar()
                firstEntry = Entry(self.selectedGraphs, textvariable=firstVar)
                firstEntry.grid(row=0, column=1, sticky=NW)
                self.entriesDict[self.dataKeys[0]] = firstEntry
            newLabel = Label(self.selectedGraphs, text=self.graphFileName, justify=LEFT)
            newLabel.grid(row=self.graphCounter, column=0, sticky=NW)
            newVar = StringVar()
            newEntry = Entry(self.selectedGraphs, textvariable=newVar)
            newEntry.grid(row=self.graphCounter, column=1, sticky=NW)
            self.entriesDict[self.dataKeys[self.graphCounter]] = newEntry

    def start_comparison(self):
        """
        start comparison pipeline and show plots if selected by user
        """
        if len(self.graphsDict) != 0:
            self.varPCA.get()
            self.varDend.get()
            show_Message("\nStart shape comparison. \n...Selected " + str(len(self.graphsDict)) + " graph sets for shape comparison.")
            self.outputFolder = '/'.join(self.graphsDict['data1'].split('/')[:-1])
            Comparison(self.outputFolder, self.graphsDict, self.entriesDict, self.varPCA.get(), self.varDend.get())
            if self.varPCA.get() == True:
                self.imagePCA = self.display_image(self.outputFolder + '/PCA_DistanceMatrix.png', 0.75, None)
                self.canvasPlotPCA.create_image(0, 0, anchor=NW, image=self.imagePCA)
                self.canvasPlotPCA.config(background=self.origColor)
            if self.varDend.get() == True:
                self.imageDend = self.display_image(self.outputFolder + '/Dendrogram_DistanceMatrix.png', 0.75, None)
                self.canvasPlotDend.create_image(0, 0, anchor=NW, image=self.imageDend)
                self.canvasPlotDend.config(background=self.origColor)
            messagebox.showinfo("GraVis", "Comparison is done. \n\nResults were saved into: \n\n" + self.outputFolder)
        else:
            messagebox.showinfo("Warning", "No graph was selected. Please select graphs first before starting the comparison.")

class Preprocessor:

    def __init__(self, filename, cleanEdges, changeRescaling, cleanNoise, plotIntermediate, outputFolder):
        self.filename = filename
        self.pathToFolder = outputFolder

        # parameters
        self.cleanEdges = cleanEdges
        self.changeRescaling = changeRescaling
        self.cleanNoise = cleanNoise
        self.plotIntermediate = plotIntermediate

        # pre-processing pipeline
        self.rawImage = self.import_image(self.filename)
        self.backgroundImage = self.detect_edges(self.rawImage)
        self.detect_noisy_image(self.backgroundImage)
        self.zeroPixelImage = self.detect_white_pixels(self.rawImage)
        self.cleanImage = self.remove_artificial_edges(self.zeroPixelImage)
        self.branchlessSkeleton, self.binaryImage, self.skeletonImage = self.skeletonize_image(self.cleanImage)
        self.labeledImage, self.labels = sp.ndimage.label(~self.branchlessSkeleton)
        self.plot_labeled_image(self.labeledImage, self.labels)

        if self.plotIntermediate == 1:
            skimage.io.imsave(self.pathToFolder + '/binaryImage.png', skimage.img_as_uint(self.binaryImage))
            skimage.io.imsave(self.pathToFolder + '/cleanedImage.png', skimage.img_as_uint(self.cleanImage))
            skimage.io.imsave(self.pathToFolder + '/skeletonImage.png', skimage.img_as_uint(self.skeletonImage))
            skimage.io.imsave(self.pathToFolder + '/branchlessSkeleton.png', skimage.img_as_uint(self.branchlessSkeleton))

    ### FUNCTIONS ###
    def import_image(self, filename):
        """
        import image from filename and convert to 8-bit 2D image
        """
        show_Message("...Load image and convert to grayscale.")
        rawImage = skimage.io.imread(filename, plugin='tifffile')
        if len(rawImage) > 2:
            rawImage = skimage.color.rgb2gray(rawImage)
        rawImage = skimage.util.img_as_ubyte(rawImage)
        return(rawImage)

    def detect_edges(self, rawImage):
        """
        use Sobel filter and probabilistic Hough lines to detect artificial edges from image stitching
        """
        backgroundImage = rawImage > 25
        backgroundImage = skimage.morphology.remove_small_objects(backgroundImage, 500)
        backgroundImage = skimage.morphology.remove_small_holes(backgroundImage, 500)
        sobelImage = skimage.filters.sobel(backgroundImage)
        houghLines = skimage.transform.probabilistic_hough_line(sobelImage, threshold=50, line_length=100, line_gap=0)
        if len(houghLines) != 0:
            self.cleanEdges = 1
            show_Message("...Artificial edges were detected in the image and will be removed.")
        return(backgroundImage)

    def detect_noisy_image(self, backgroundImage):
        """
        calculate noise of image by calculating the ratio of background pixels and image resize
        """
        noiseGrade = np.sum(backgroundImage) / backgroundImage.size
        if noiseGrade > 0.5:
            self.cleanNoise = 1
            show_Message("...The image is very noisy and will be cleaned.")

    def detect_white_pixels(self, rawImage):
        """
        calculate the ratio of 0-pixels in the image to infer if intensity rescaling is neccessary
        """
        zeroPixelImage = rawImage == 0
        zeroPixelImage = skimage.morphology.remove_small_objects(zeroPixelImage, 500)
        zeroPixelRatio = np.sum(zeroPixelImage) / zeroPixelImage.size
        if zeroPixelRatio > 0.6:
            self.changeRescaling = 1
            show_Message("...The image rescaling was changed.")
        return(zeroPixelImage)

    def remove_artificial_edges(self, zeroPixelImage):
        """
        remove artificial edges from the image
        """
        if self.cleanEdges == 1:
            cleanImage = self.rawImage.copy()
            zeroPixelLabelImage, zeroPixelLabels = sp.ndimage.label(zeroPixelImage)
            zeroPixelBorders = keep_labels_on_border(zeroPixelLabelImage)
            zeroPixelBordersLabelImage, _ = sp.ndimage.label(zeroPixelBorders)
            zeroPixelBordersRP = skimage.measure.regionprops(zeroPixelBordersLabelImage)
            edgeContours = self.detect_edge_contours(zeroPixelBordersRP, zeroPixelBordersLabelImage)
            for idx in range(len(edgeContours)):
                contourRescaled = self.rescale_contour_to_original(edgeContours[idx])
                cleanImage = self.remove_pixels_in_periphery(contourRescaled, cleanImage)
        else:
            cleanImage = self.rawImage.copy()
        return(cleanImage)

    def detect_edge_contours(self, regionProps, labeledImage):
        """
        find the contour of all artificial edges
        """
        edgeContourList = []
        for idx in range(len(regionProps)):
            if regionProps[idx].euler_number == 1:
                imageLabel = labeledImage == idx + 1
                edgeContour = find_edge_contour(imageLabel)
                edgeContourList.append(edgeContour)
        return(edgeContourList)

    def rescale_contour_to_original(self, contour):
        """
        rescale contours back to original image shape
        """
        contourRescaled = contour-2
        for idx, (xPos,yPos) in reversed(list(enumerate(contourRescaled))):
            if xPos <= 1 or xPos >= self.rawImage.shape[0]-1 or yPos <= 1 or yPos >= self.rawImage.shape[1]-1:
                contourRescaled = np.delete(contourRescaled, idx, 0)
        return(contourRescaled)

    def remove_pixels_in_periphery(self, contourRescaled, cleanImage):
        """
        remove pixels in periphery of contour
        """
        contourPixels = {}
        listOfCorrectedPixels = []
        xLen, yLen = cleanImage.shape[0] - 1, cleanImage.shape[1] - 1
        for idx, (xPos, yPos) in reversed(list(enumerate(contourRescaled))):
            window = cleanImage[xPos-1:xPos+2, yPos-1:yPos+2]
            orientContourPixel = contour_orientation(window)
            for pxl in range(len(orientContourPixel)):
                if pxl < 2:
                    contourPixels[(xPos, yPos)] = [orientContourPixel[pxl]]
                    listOfCorrectedPixels = measure_intensity_along_contour(cleanImage, xPos, yPos, orientContourPixel[pxl], listOfCorrectedPixels)
        listOfCorrectedPixelsSorted = sorted(listOfCorrectedPixels)
        correctEdges = self.calculate_consecutive_difference(listOfCorrectedPixelsSorted)

        for start, end in correctEdges:
            edgePixels = listOfCorrectedPixelsSorted[int(start):int(end)]
            for xPos, yPos in edgePixels:
                pixelOrientation = contourPixels[(xPos, yPos)]
                for orient in pixelOrientation:
                    xmin, xmax, ymin, ymax = self.define_pixel_periphery(xPos, yPos, orient, xLen, yLen)
                    cleanImage[xmin:xmax, ymin:ymax] = 0
                del contourPixels[xPos, yPos]

        for xPos, yPos in contourPixels:
            xmin, xmax = bounds(xPos-5, 0, xLen), bounds(xPos+6, 0, xLen)
            ymin, ymax = bounds(yPos-5, 0, yLen), bounds(yPos+6, 0, yLen)
            cleanImage[xmin:xmax, ymin:ymax] = 0

        cleanImage[:10, :] = 0
        cleanImage[-9:, :] = 0
        cleanImage[:, :10] = 0
        cleanImage[:, -9:] = 0
        return(cleanImage)

    def calculate_consecutive_difference(self, sequence):
        """
        calculate difference for all consecutive point coordinates in an array and return a range of at least 50 continous, consecutive points (artificial edge)
        """
        correctEdges = []
        consecutiveDifference = np.diff(sequence, axis=0)
        differenceDistances = np.sqrt((consecutiveDifference ** 2).sum(axis=1))
        groupedDifferences = np.array(list([value, len(list(counts))] for value, counts in itertools.groupby(differenceDistances)))
        consecutiveEdges = np.where(groupedDifferences[:,1] > 50)
        for idx in consecutiveEdges[0]:
            correctEdges.append([np.sum(groupedDifferences[:idx,1]),np.sum(groupedDifferences[:idx+1,1])])
        return(correctEdges)

    def define_pixel_periphery(self, x, y, orientation, xLen, yLen):
        """
        find the direction of the pixel periphery to be cleaned
        """
        if orientation == 'right':
            xmin, xmax = bounds(x-1, 0, xLen), bounds(x+2, 0, xLen)
            ymin, ymax = bounds(y-1, 0, yLen), bounds(y+21, 0, yLen)
        if orientation == 'top':
            xmin, xmax = bounds(x-20, 0, xLen), bounds(x+1, 0, xLen)
            ymin, ymax = bounds(y-1, 0, yLen), bounds(y+2, 0, yLen)
        if orientation == 'left':
            xmin, xmax = bounds(x-1, 0, xLen), bounds(x+2, 0, xLen)
            ymin, ymax = bounds(y-20, 0, yLen), bounds(y+1, 0, yLen)
        if orientation == 'bottom':
            xmin, xmax = bounds(x-1, 0, xLen), bounds(x+21, 0, xLen)
            ymin, ymax = bounds(y-1, 0, yLen), bounds(y+2, 0, yLen)
        return(xmin, xmax, ymin, ymax)

    def skeletonize_image(self, cleanImage):
        """
        skeletonize cleaned image according to whether the images is noisy or not
        """
        show_Message("...Image is skeletonized.")
        if self.cleanNoise == 0:
            if self.changeRescaling == 0:
                pLower, pUpper = np.percentile(cleanImage, (2, 98))
            else:
                pLower, pUpper = np.percentile(cleanImage, (2, 90))
            rescaledImage = skimage.exposure.rescale_intensity(cleanImage, (pLower, pUpper))
            gaussianImage = skimage.filters.gaussian(rescaledImage, sigma=3)
            tubeImage = tube_filter(gaussianImage, sigma=3)
            binaryImage = self.binarize_image(tubeImage)
            smallObjects = skimage.morphology.remove_small_objects(binaryImage, 500)
            smallHoles = skimage.morphology.remove_small_holes(smallObjects, 200)
            skeletonImage = skimage.morphology.skeletonize(smallHoles)
            correctedSkeletonImage = correct_gaps_in_skeleton(skeletonImage)
            skeletonImage = correctedSkeletonImage
            branchlessSkeleton = detect_branches(correctedSkeletonImage, mode='remove')
        else:
            branchlessSkeleton, binaryImage, skeletonImage = self.remove_noise_from_image(cleanImage)
        return(branchlessSkeleton, binaryImage, skeletonImage)

    def binarize_image(self, tubeImage):
        """
        binarize image with mean of Otsu threshold and intensity histogram
        """
        show_Message("...Image is binarized.")
        counts, bins = np.histogram(tubeImage.flatten(), 256, range=(0, 256))
        thresholdHist = np.where(counts == np.max(counts))[0][0]
        thresholdOtsu = skimage.filters.threshold_otsu(tubeImage)
        thresholdImage = np.mean([thresholdHist, thresholdOtsu])
        binaryImage = tubeImage > thresholdImage
        return(binaryImage)

    def remove_noise_from_image(self, cleanImage):
        """
        remove noise from image and then skeletonize
        """
        denoisedImage = skimage.restoration.denoise_tv_chambolle(cleanImage)
        tophatImage = skimage.morphology.white_tophat(denoisedImage, selem=disk(3))
        adapthistImage = skimage.exposure.equalize_adapthist(tophatImage, clip_limit=0.1)
        otsuImage = skimage.filters.threshold_otsu(adapthistImage)
        binaryImage = adapthistImage > otsuImage
        smallObjects = skimage.morphology.remove_small_objects(binaryImage, 200)
        intermediateSkeletonImage = skimage.morphology.skeletonize(smallObjects)
        correctedSkeletonImage = correct_gaps_in_skeleton(intermediateSkeletonImage)
        intermediateBranchlessSkeleton = detect_branches(correctedSkeletonImage, mode='remove')
        smallHoles = skimage.morphology.remove_small_holes(intermediateBranchlessSkeleton, 100)
        skeletonImage = skimage.morphology.skeletonize(smallHoles)
        skeletonImage = correctedSkeletonImage
        branchlessSkeleton = detect_branches(skeletonImage, mode='remove')
        return(branchlessSkeleton, binaryImage, skeletonImage)

    def plot_labeled_image(self, labeledImage, labels):
        """
        plot the labeled image with labels
        """
        textPositions = []
        textString = []
        for idx in range(2, labels + 1):
            label = labeledImage == idx
            cmx, cmy = sp.ndimage.measurements.center_of_mass(label)
            textPositions.append([cmx, cmy])
            textString.append(str(idx-1))
        labelThreshold = int(80*labels/100)

        fig, axs = plt.subplots(1, 1, figsize=(10, 10))
        plt.imshow(labeledImage, cmap='viridis')
        axs.axes.get_yaxis().set_visible(False)
        axs.axes.get_xaxis().set_visible(False)
        for idx in range(len(textString)):
            if int(textString[idx]) >= labelThreshold:
                plt.text(textPositions[idx][1], textPositions[idx][0], textString[idx], fontsize=8, color='black')
            else:
                plt.text(textPositions[idx][1], textPositions[idx][0], textString[idx], fontsize=8, color='white')
        fig.savefig(self.pathToFolder + '/LabeledPavementCells.png', bbox_inches='tight', dpi=300)

class VisGraph:

    def __init__(self, preprocessedImage, plotIntermediate, resolution, outputFolder):
        self.outputFolder = outputFolder
        self.plotIntermediate = plotIntermediate
        self.resolution = float(resolution)
        if preprocessedImage != None:
            self.skeletonImage = preprocessedImage.skeletonImage
            self.branchlessSkeleton = preprocessedImage.branchlessSkeleton
            self.labeledImage = preprocessedImage.labeledImage
            self.labels = preprocessedImage.labels
        else:
            try:
                self.skeletonImage = skimage.io.imread(self.outputFolder + '/skeletonImage.png') > 0
                self.branchlessSkeleton = skimage.io.imread(self.outputFolder + '/branchlessSkeleton.png') > 0
                self.labeledImage, self.labels = sp.ndimage.label(~self.branchlessSkeleton)
            except FileNotFoundError:
                messagebox.showinfo("Warning", "No pre-processed files were found for the selected image.")
        self.shapeResultsTable = pd.DataFrame(columns=['CellNumber', 'Lobes', 'Necks', 'Junctions', 'JunctionLobes', 'Complexity', 'Circularity', 'Area', 'Perimeter'])
        self.lobeParameters = pd.DataFrame(columns=['CellLabel', 'NodeLabelLobe', 'NodeLabelNeck1', 'NodeLabelNeck2', 'LobeLength', 'NeckWidth'])
        if os.path.isfile(self.outputFolder + '/visibilityGraphs.gpickle'):
            os.remove(self.outputFolder + '/visibilityGraphs.gpickle')
            os.remove(self.outputFolder + '/cellContours.gpickle')
            os.remove(self.outputFolder + '/shapeResultsTable.csv')

        self.junctions = self.detect_threeway_junctions(self.skeletonImage, self.branchlessSkeleton, self.labeledImage)
        self.visibilityGraphs, self.cellContours = self.visibility_graphs(self.labeledImage, self.labels, self.resolution)

        if not os.path.exists(self.outputFolder + '/resultsGraVis'):
            try:
                os.makedirs(self.outputFolder + '/resultsGraVis')
            except OSError:
                messagebox.showinfo("Warning", "Creation of the results directory failed.")

        self.add_data_to_table(self.visibilityGraphs, self.cellContours, self.labeledImage, self.labels, self.junctions, self.resolution)
        show_Message("\nGraVis is done!")

    def detect_threeway_junctions(self, skeletonImage, branchlessSkeleton, labeledImage):
        """
        detect threeway junctions of cells in skeletonized image
        """
        show_Message("...Detect tri-cellular junctions.")
        finalListJunctions = []
        labeledTrackedImage = create_labeled_and_tracked_image(skeletonImage, labeledImage)
        allJunctionsList = detect_crossings_and_endpoints(skeletonImage, mode='crossings', output='list')
        lenX, lenY = branchlessSkeleton.shape
        for xPos, yPos in allJunctionsList:
            if branchlessSkeleton[xPos, yPos] == 1:
                window, winBounds = create_window(labeledTrackedImage, xPos, yPos, 1, 2, 1, 2)
                tracked = np.transpose(np.where(window == 2))
                if len(tracked) == 0:
                    finalListJunctions.append([xPos, yPos])
                else:
                    newWindow, _ = create_window(labeledTrackedImage, tracked[0][0]+winBounds[0], tracked[0][1]+winBounds[2], 1, 2, 1, 2)
                    if np.sum(newWindow == 0) != 0 and np.sum(newWindow == 0) >= np.sum(newWindow >= 3):
                        finalListJunctions.append([xPos, yPos])

        if self.plotIntermediate == 1:
            self.plot_cell_junctions(finalListJunctions, branchlessSkeleton)
        return(finalListJunctions)

    def plot_cell_junctions(self, finalListJunctions, branchlessSkeleton):
        """
        plot the threeway junctions on the branchless skeleton
        """
        graph = nx.Graph()
        for idx, (x,y) in enumerate(finalListJunctions):
            graph.add_node(idx, pos=(y, x))
        posGraph = nx.get_node_attributes(graph, 'pos')

        fig,axs = plt.subplots(1, 1, figsize=(10, 10))
        plt.imshow(branchlessSkeleton, cmap='gray')
        nodes=nx.draw_networkx_nodes(graph, posGraph, with_labels=False, node_color='red', node_size=30)
        nodes.set_edgecolor('None')
        axs.axes.get_yaxis().set_visible(False)
        axs.axes.get_xaxis().set_visible(False)
        fig.savefig(self.outputFolder + '/JunctionsOnSkeleton.png', bbox_inches='tight', dpi=300)

    def visibility_graphs(self, labeledImage, labels, resolution):
        """
        create a visibility graph for all cells
        """
        show_Message("...Create visibility graphs:")
        visGraphsAll = {}
        cellContoursAll = {}
        for label in range(2, labels+1):
            show_Message("......Graph " + str(label-1) + ' of ' + str(labels-1))
            visGraph, cellContour = self.create_visibility_graph(labeledImage, label, resolution)
            visGraphsAll[label-1] = visGraph
            cellContoursAll[label-1] = cellContour
            visGraphsPickle = open(self.outputFolder + '/visibilityGraphs.gpickle', 'ab')
            pickle.dump(visGraph, visGraphsPickle)
            visGraphsPickle.close()
            cellContoursPickle = open(self.outputFolder + '/cellContours.gpickle', 'ab')
            pickle.dump(cellContour, cellContoursPickle)
            cellContoursPickle.close()
        return(visGraphsAll, cellContoursAll)

    def create_visibility_graph(self, labeledImage, label, resolution):
        """
        create visibilit graph from cell contour
        """
        visGraph = nx.Graph()
        pixelDistance = calculate_pixel_distance(resolution)
        cases = ['FFFF0F212','0FFF0F212','1FFF0F212','F0FF0F212','00FF0F212','10FF0F212','F1FF0F212']
        contourImage, cellContourOrdered = self.extract_cell_contour(label, labeledImage)
        if len(cellContourOrdered) != 0:
            pixelsOnContour = interpolate_contour_pixels(cellContourOrdered, pixelDistance)
            for key in pixelsOnContour:
                visGraph.add_node(key, pos=(pixelsOnContour[key][0], pixelsOnContour[key][1]))
            visGraph = self.add_edges_to_visGraph(pixelsOnContour, visGraph, cases)
        return(visGraph, cellContourOrdered)

    def extract_cell_contour(self, label, labeledImage):
        """
        extract the contour of a specified cell
        """
        cellImage = labeledImage == label
        contourImage = invert(cellImage)
        cellContour = find_contour_of_object(cellImage)
        if (0 not in cellContour) and (cellImage.shape[0] not in cellContour[:, 0]) and (cellImage.shape[1] not in cellContour[:, 1]):
            cellContourOrdered = marching_squares(cellContour, cellImage)
            for xPos, yPos in cellContourOrdered:
                contourImage[xPos, yPos] = 1
        else:
            cellContourOrdered = []
            for xPos, yPos in cellContour:
                contourImage[xPos, yPos] = 1
        return(contourImage, cellContourOrdered)

    def add_edges_to_visGraph(self, pixelsOnContour, visGraph, cases):
        """
        add edge to visGraph if the edge between two nodes lies inside the cell (concave)
        """
        Polygon = shapely.geometry.Polygon([[pixelsOnContour[key][1], pixelsOnContour[key][0]] for key in pixelsOnContour])
        Boundary = shapely.geometry.LineString(list(Polygon.exterior.coords))
        combs = itertools.combinations(range(len(pixelsOnContour)), 2)
        for node1, node2 in list(combs):
            line = shapely.geometry.LineString(((pixelsOnContour[node1][1], pixelsOnContour[node1][0]), (pixelsOnContour[node2][1], pixelsOnContour[node2][0])))
            DE9IM = line.relate(Polygon)
            if DE9IM in cases:
                intersection = Boundary.intersection(line)
                if DE9IM == '10FF0F212' and len(intersection) <= 3:
                    visGraph.add_edge(node1, node2, length=euclidean(pixelsOnContour[node1], pixelsOnContour[node2]))
                if DE9IM == 'F1FF0F212' and intersection.geom_type == 'LineString':
                    visGraph.add_edge(node1, node2, length=euclidean(pixelsOnContour[node1], pixelsOnContour[node2]))
                if DE9IM in cases[:5]:
                    visGraph.add_edge(node1, node2, length=euclidean(pixelsOnContour[node1], pixelsOnContour[node2]))
        return(visGraph)

    def add_data_to_table(self, visGraphsAll, cellContoursAll, labeledImage, labels, junctions, resolution):
        """
        summarize all results in a table
        """
        for label in range(1, labels):
            cellContour = cellContoursAll[label]
            visGraph = visGraphsAll[label]
            cell = labeledImage == label
            if visGraph.number_of_nodes() != 0:
                cellJunctions = self.find_number_of_cell_junctions(cellContour)
                lobes, necks = self.count_lobes_and_necks(visGraph)
                correlatedJunctions = self.correlate_junctions_and_lobes(visGraph, lobes, necks, cellJunctions)
                self.calculate_lobe_and_neck_properties(label, visGraph, cellContour, cellJunctions, lobes, necks, correlatedJunctions, resolution)
                sigma = self.compute_graph_complexity(visGraph)
                area = np.sum(cell)
                circ = 4 * np.pi * area / len(cellContour) ** 2
                dataAppend = [label, len(lobes), len(necks), len(cellJunctions), len(correlatedJunctions), sigma, circ, area, np.sum(cellContour)]
            else:
                dataAppend = [label, 0,0,0,0,0,0]
            self.shapeResultsTable.loc[0] = dataAppend
            if not os.path.isfile(self.outputFolder + '/ShapeResultsTable.csv'):
                shapeResultsTable.to_csv(self.outputFolder + '/ShapeResultsTable.csv', mode='a', index=False)
            else:
                shapeResultsTable.to_csv(self.outputFolder + '/ShapeResultsTable.csv', mode='a', index=False, header=False)

    def find_number_of_cell_junctions(self, cellContour):
        """
        find all junctions on a cell contour, allowing for small derivations
        """
        cellJunctions = []
        for index in range(len(self.junctions)):
            foundPositions = find_index_of_coordinates(self.junctions[index], cellContour, [0,1,-1], 'coordinates')
            if len(foundPositions) != 0:
                cellJunctions.append(self.junctions[index])
        return(cellJunctions)

    def count_lobes_and_necks(self, visGraph):
        """
        count the number of lobes and necks according to closeness centrality of visibility graph nodes
        """
        closenessCentrality = nx.closeness_centrality(visGraph, distance='length')
        closenessCentralityArray = np.asarray(list(closenessCentrality.values()))
        lobes, necks = find_local_extrema(closenessCentralityArray)
        return(lobes, necks)

    def correlate_junctions_and_lobes(self, visGraph, lobes, necks, cellJunctions):
        """
        correlate detected lobes and necks with detected tri-cellular junctions
        """
        nodePositions = nx.get_node_attributes(visGraph, 'pos')
        detectedJunctions = []
        positions = np.asarray([nodePositions[idx] for idx in itertools.chain(lobes, necks)])
        if len(positions) != 0:
            for index in range(len(cellJunctions)):
                foundPositions = find_index_of_coordinates(cellJunctions[index], positions, [0, 1, -1, 2, -2, 3, -3], 'coordinates')
                if len(foundPositions) != 0:
                    xShift, yShift = foundPositions[0][0], foundPositions[0][1]
                    junction = (cellJunctions[index][0] + xShift, cellJunctions[index][1] + yShift)
                    key = get_key_from_value(nodePositions, junction)
                    detectedJunctions.append(key)
        return(detectedJunctions)

    def calculate_lobe_and_neck_properties(self, key, visGraph, cellContour, cellJunctions, lobes, necks, correlatedJunctions, resolution):
        """
        calculate the neck width and lobe length for a selected pavement cell and create a graphic output for lobe and neck positions
        """
        pos = nx.get_node_attributes(visGraph, 'pos')
        for index in range(len(necks)):
            if index == len(necks) - 1:
                neck1, neck2 = necks[index], necks[0]
                nodes = np.append(np.arange(neck1, visGraph.number_of_nodes(), 1), np.arange(0, neck2, 1))
                lobe = self.find_lobe_between_necks(lobes, nodes)
            else:
                neck1, neck2 = necks[index], necks[index + 1]
                nodes = np.arange(neck1, neck2 + 1, 1)
                lobe = self.find_lobe_between_necks(lobes, nodes)
            if len(lobe) == 0:
                lobe1 = 'no lobe found'
                lobelength = 0
            elif len(lobe) > 2:
                lobe1 = 'more than one lobe found'
                lobelength = 0
            else:
                lobe1 = lobe[0]
                lobelength = self.calculate_lobe_length(neck1, neck2, lobe1, pos)
            neckwidth = euclidean(pos[neck1], pos[neck2])
            dataLobes = [key, lobe1, neck1, neck2, lobelength * resolution, neckwidth * resolution]
            self.lobeParameters.loc[0] = dataLobes
            if not os.path.isfile(self.outputFolder + '/LobeParameters.csv'):
                shapeResultsTable.to_csv(self.outputFolder + '/LobeParameters.csv', mode='a', index=False)
            else:
                shapeResultsTable.to_csv(self.outputFolder + '/LobeParameters.csv', mode='a', index=False, header=False)
        self.create_visual_output(key, visGraph, cellContour, cellJunctions, lobes, necks, correlatedJunctions, pos)

    def find_lobe_between_necks(self, lobes, nodes):
        """
        find the adjacent necks of a lobe
        """
        matchedLobe = []
        for lobe in lobes:
            if lobe in nodes:
                matchedLobe.append(lobe)
        return(matchedLobe)

    def calculate_lobe_length(self, neck1, neck2, lobe1, pos):
        """
        calculate the length of a lobe based on its adjacent necks
        """
        pos1, pos2, posL = pos[neck1], pos[neck2], pos[lobe1]
        if pos2[0] - pos1[0] == 0:
            basePointX = pos1[0]
            basePointY = posL[1]
        elif pos2[1] - pos1[1] == 0:
            basePointX = pos1[1]
            basePointY = posL[0]
        else:
            slopeBase = (pos2[1] - pos1[1]) / (pos2[0] - pos1[0])
            interceptBase = pos1[1] - slopeBase * pos1[0]
            slopeLobe = -1 / slopeBase
            interceptLobe = posL[1] - slopeLobe * posL[0]
            basePointX = (interceptLobe - interceptBase) / (slopeBase - slopeLobe)
            basePointY = slopeBase * basePointX + interceptBase
        lobeLength = euclidean(posL, (basePointX, basePointY))
        return(lobeLength)

    def create_visual_output(self, key, visGraph, contour, junctions, lobes, necks, correlatedJunctions, pos):
        """
        create a visual output for the positions of detected lobes, necks and tri-cellular junctions
        """
        xmin, xmax, ymin, ymax = np.min(contour[:, 0]), np.max(contour[:, 0]), np.min(contour[:, 1]), np.max(contour[:, 1])
        xminB, yminB = bounds(xmin, 0, xmin - 10), bounds(ymin, 0, ymin - 10)
        contourImage = np.zeros(((xmax + 10) - xminB, (ymax + 10) - yminB))
        for x, y in contour:
            contourImage[x - xminB, y - yminB] = 1

        legend_elements = [matplotlib.patches.Circle(([0], [0]), radius=5, ec='gray', fc='None', lw=2, label='Junction'),
                       matplotlib.patches.Circle(([0], [0]), radius=3, ec='#56b4e9', fc='None', lw=2, label='Lobe'),
                       matplotlib.patches.Circle(([0], [0]), radius=3, ec='#e69f00', fc='None', lw=2, label='Neck')]

        fig, ax = plt.subplots(1, 1)
        plt.imshow(contourImage, cmap='gray_r', interpolation='None')
        ax.tick_params(axis='both', which='both', top='off', right='off')
        ax.set_xlabel('Pixel')
        ax.set_ylabel('Pixel')
        ax.set_title('Cell ' + str(key))
        for junc in junctions:
            circ = plt.Circle((junc[1] - yminB, junc[0] - xminB), radius=5, ec='gray', fc='None', lw=2)
            ax.add_patch(circ)
        for neck in necks:
            posNeck = pos[neck]
            circ = plt.Circle((posNeck[1] - yminB, posNeck[0] - xminB), radius=3, ec='#e69f00', fc='None', lw=2)
            ax.add_patch(circ)
            ax.text(posNeck[1] - yminB + 4, posNeck[0] - xminB + 3, neck, color='#af7900', fontsize=7)
        for lobe in lobes:
            posLobe = pos[lobe]
            circ = plt.Circle((posLobe[1] - yminB, posLobe[0] - xminB), radius=3, ec='#56b4e9', fc='None', lw=2)
            ax.add_patch(circ)
            ax.text(posLobe[1] - yminB + 4, posLobe[0] - xminB + 3, lobe, color='#136492', fontsize=7)
        ax.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.4), fancybox=False, shadow=False, ncol=3, fontsize=7, handler_map={matplotlib.patches.Circle: HandlerEllipse()})
        if os.path.exists(self.outputFolder + '/resultsGraVis'):
            fig.savefig(self.outputFolder + '/resultsGraVis/Cell' + str(key) + '_detectedFeatures.png', bbox_inches='tight', dpi=300)
        else:
            fig.savefig(self.outputFolder + '/Cell' + str(key) + '_detectedFeatures.png', bbox_inches='tight', dpi=300)


    def compute_graph_complexity(self, visGraph):
        """
        compute the complexity of the graph using the relative density of the clique
        """
        edgesCompleteGraph = (visGraph.number_of_nodes() * (visGraph.number_of_nodes() - 1)) * 0.5
        delta = visGraph.number_of_edges() / edgesCompleteGraph
        return(delta)

class VisGraphOther:

    def __init__(self, selectedImage, resolution, outputFolder, inputType, fileList):
        self.selectedImage = selectedImage
        self.outputFolder = outputFolder
        self.resolution = float(resolution)
        self.inputType = inputType
        self.fileList = fileList
        self.shapeResultsTable = pd.DataFrame(columns=['File', 'LabeledImage', 'GraphNumber', '#Nodes', '#Edges', 'Complexity'])
        if os.path.isfile(self.outputFolder + '/visibilityGraphs.gpickle'):
            os.remove(self.outputFolder + '/visibilityGraphs.gpickle')
            os.remove(self.outputFolder + '/cellContours.gpickle')
            os.remove(self.outputFolder + '/shapeResultsTable.csv')

        if self.inputType == 'image':
            show_Message("...Load binary image.")
            self.labeledImage, self.labels = self.label_binary_image(self.selectedImage)
            show_Message("...Create visibility graphs:")
            self.visibilityGraphsOther = self.visibility_graphs_other(self.labeledImage, self.labels, self.resolution)
            for graph in self.visibilityGraphsOther.keys():
                self.add_data_to_table(self.visibilityGraphsOther[graph], self.selectedImage, graph, 'LabeledShapes.png')
            self.plot_labeled_image(self.labeledImage, self.outputFolder, self.labels, 'image', 1)
        else:
            graphIndex = 1
            self.visibilityGraphsOther = {}
            for fileIndex, file in enumerate(self.fileList):
                show_Message("...Load binary image " + str(fileIndex+1) + " of " + str(len(self.fileList)))
                self.labeledImage, self.labels = self.label_binary_image(file)
                show_Message("...Create visibility graphs:")
                self.visibilityGraph = self.visibility_graphs_other(self.labeledImage, self.labels, self.resolution)
                labeledFile = self.plot_labeled_image(self.labeledImage, self.outputFolder, self.labels, 'folder', graphIndex)
                if len(self.visibilityGraph) == 1:
                    self.visibilityGraphsOther[graphIndex] = list(self.visibilityGraph.values())[0]
                    self.add_data_to_table(list(self.visibilityGraph.values())[0], file, graphIndex, labeledFile)
                    graphIndex += 1
                else:
                    for graph in self.visibilityGraph.keys():
                        self.visibilityGraphsOther[graphIndex] = self.visibilityGraph[graph]
                        self.add_data_to_table(self.visibilityGraph[graph], file, graphIndex, labeledFile)
                        graphIndex += 1
        show_Message("\nGraVis is done!")

    def label_binary_image(self, selectedImage):
        """
        check if input is binary image and label all objects (white)
        """
        rawImage = skimage.io.imread(selectedImage)
        if len(rawImage.shape) == 2:
            if len(np.unique(rawImage)) == 2:
                binaryImage = rawImage > 0
                if (1 in binaryImage[0, :]) or (1 in binaryImage[-1, :]) or (1 in binaryImage[:, 0]) or (1 in binaryImage[:, -1]):
                    show_Message("...Detected objects at image border. Added padding to binary image.")
                    binaryImage = np.pad(binaryImage, pad_width=3, mode='constant', constant_values=0)
                labeledImage, labels = sp.ndimage.label(binaryImage, np.ones((3,3)))
                return(labeledImage, labels)
            else:
                messagebox.showinfo("Error", "The input image is not binary.")
        else:
            messagebox.showinfo("Error", "The input image is not binary.")

    def visibility_graphs_other(self, labeledImage, labels, resolution):
        """
        create a visibility graph for all cells
        """
        visGraphsAll = {}
        cellContoursAll = {}
        for label in range(1, labels+1):
            show_Message("......Graph " + str(label) + " of " + str(labels))
            visGraph, cellContour = self.create_visibility_graph(labeledImage, label, resolution)
            if visGraph != None:
                visGraphsAll[label] = visGraph
                visGraphsOtherPickle = open(self.outputFolder + '/visibilityGraphs.gpickle', 'ab')
                pickle.dump(visGraph, visGraphsOtherPickle)
                visGraphsOtherPickle.close()
                cellContoursOtherPickle = open(self.outputFolder + '/vcellContours.gpickle', 'ab')
                pickle.dump(cellContour, cellContoursOtherPickle)
                cellContoursOtherPickle.close()
        return(visGraphsAll)

    def create_visibility_graph(self, labeledImage, label, resolution):
        """
        create visibilit graph from cell contour
        """
        visGraph = nx.Graph()
        cases = ['FFFF0F212','0FFF0F212','1FFF0F212','F0FF0F212','00FF0F212','10FF0F212','F1FF0F212']
        contourImage, cellContourOrdered = self.extract_cell_contour(label, labeledImage)
        if len(cellContourOrdered) != 0:
            pixelsOnContour = interpolate_contour_pixels(cellContourOrdered, resolution)
            if len(pixelsOnContour) != 0:
                for key in pixelsOnContour:
                    visGraph.add_node(key, pos=(pixelsOnContour[key][0], pixelsOnContour[key][1]))
                visGraph = self.add_edges_to_visGraph(pixelsOnContour, visGraph, cases)
            else:
                visGraph, cellContourOrdered = None, None
        else:
            visGraph, cellContourOrdered = None, None
        return(visGraph, cellContourOrdered)

    def extract_cell_contour(self, label, labeledImage):
        """
        extract the contour of a specified cell
        """
        cellImage = labeledImage == label
        contourImage = invert(cellImage)
        if np.all([np.all(cellImage[..., 0:, 0] == 0), np.all(cellImage[..., 0, 0:] == 0), np.all(cellImage[..., 0:, -1] == 0), np.all(cellImage[..., -1, 0:] == 0),]):
            cellContour = find_contour_of_object(cellImage)
            cellContourOrdered = marching_squares(cellContour, cellImage)
        else:
            cellImageBuffer = np.pad(cellImage, pad_width=2, mode='constant', constant_values=0)
            cellContour = find_contour_of_object(cellImageBuffer)
            cellContourOrdered = marching_squares(cellContour, cellImageBuffer)
        for xPos, yPos in cellContourOrdered:
            contourImage[xPos, yPos] = 1
        return(contourImage, cellContourOrdered)

    def add_edges_to_visGraph(self, pixelsOnContour, visGraph, cases):
        """
        add edge to visGraph if the edge between two nodes lies inside the cell (concave)
        """
        Polygon = shapely.geometry.Polygon([[pixelsOnContour[key][1], pixelsOnContour[key][0]] for key in pixelsOnContour])
        Boundary = shapely.geometry.LineString(list(Polygon.exterior.coords))
        combs = itertools.combinations(range(len(pixelsOnContour)), 2)
        for node1, node2 in list(combs):
            line = shapely.geometry.LineString(((pixelsOnContour[node1][1], pixelsOnContour[node1][0]), (pixelsOnContour[node2][1], pixelsOnContour[node2][0])))
            DE9IM = line.relate(Polygon)
            if DE9IM in cases:
                intersection = Boundary.intersection(line)
                if DE9IM == '10FF0F212' and len(intersection) <= 3:
                    visGraph.add_edge(node1, node2, length=euclidean(pixelsOnContour[node1], pixelsOnContour[node2]))
                if DE9IM == 'F1FF0F212' and intersection.geom_type == 'LineString':
                    visGraph.add_edge(node1, node2, length=euclidean(pixelsOnContour[node1], pixelsOnContour[node2]))
                if DE9IM in cases[:5]:
                    visGraph.add_edge(node1, node2, length=euclidean(pixelsOnContour[node1], pixelsOnContour[node2]))
        return(visGraph)

    def add_data_to_table(self, visGraph, file, index, labeledFile):
        """
        summarize all results in a table
        """
        fileName = file.split('/')[-1]
        sigma = self.compute_graph_complexity(visGraph)
        dataAppend = [fileName, labeledFile, index, visGraph.number_of_nodes(), visGraph.number_of_edges(), sigma]
        self.shapeResultsTable.loc[0] = dataAppend
        if not os.path.isfile(self.outputFolder + '/ShapeResultsTable.csv'):
            shapeResultsTable.to_csv(self.outputFolder + '/ShapeResultsTable.csv', mode='a', index=False)
        else:
            shapeResultsTable.to_csv(self.outputFolder + '/ShapeResultsTable.csv', mode='a', index=False, header=False)

    def compute_graph_complexity(self, visGraph):
        """
        compute the complexity of the graph using the relative density of the clique
        """
        edgesCompleteGraph = (visGraph.number_of_nodes() * (visGraph.number_of_nodes() - 1)) * 0.5
        delta = visGraph.number_of_edges() / edgesCompleteGraph
        return(delta)

    def plot_labeled_image(self, labeledImage, outputFolder, labels, fileType, index):
        """
        plot the labeled image with labels
        """
        textPositions = []
        textString = []
        for idx in range(1, labels + 1):
            label = labeledImage == idx
            cmx, cmy = sp.ndimage.measurements.center_of_mass(label)
            textPositions.append([cmx, cmy])
            graphNumber = idx + index - 1
            textString.append(str(graphNumber))

        fig, axs = plt.subplots(1, 1, figsize=(10, 10))
        plt.imshow(labeledImage, cmap='viridis')
        axs.axes.get_yaxis().set_visible(False)
        axs.axes.get_xaxis().set_visible(False)
        for idx in range(len(textString)):
            plt.text(textPositions[idx][1], textPositions[idx][0], textString[idx], fontsize=8, color='white')
        if fileType == 'image':
            fig.savefig(outputFolder + '/LabeledShapes.png', bbox_inches='tight', dpi=300)
        else:
            fig.savefig(outputFolder + '/LabeledShapes_' + str(index) + '.png', bbox_inches='tight', dpi=300)
            return('LabeledShapes_' + str(index) + '.png')

class Comparison:

    def __init__(self, outputFolder, pathToVisibilityGraphs, entries, plotPCA, plotDendrogram):
        self.pathToVisibilityGraphs = list(pathToVisibilityGraphs.values())
        if len(entries) != 0:
            self.inputLabels = []
            for key in entries.keys():
                self.inputLabels.append(entries[key].get())
        self.outputFolder = outputFolder

        self.plotPCA = plotPCA
        self.plotDendrogram = plotDendrogram
        self.resultsTable = pd.DataFrame(columns=['File', 'Graph', 'Label', 'Color'])
        self.colorList = ['#0077bb', '#ee3377', '#ee7733', '#009988', '#33bbee', '#cc3311', '#bbbbbb']

        self.visibilityGraphsAll = []
        if len(self.pathToVisibilityGraphs) == 1:
            self.visibilityGraphs = {}
            graphCounter = 1
            with open(self.pathToVisibilityGraphs[0], 'rb') as pickleFile:
                try:
                    while True:
                        obj = pickle.load(pickleFile)
                        try:
                            items = obj.items()
                            self.visibilityGraphs = obj
                        except (AttributeError, TypeError):
                            self.visibilityGraphs[graphCounter] = obj
                            graphCounter += 1
                except EOFError:
                    pass
            self.inputLabels = np.arange(1, len(self.visibilityGraphs) + 1, 1)
            for indexKey, key in enumerate(self.visibilityGraphs.keys()):
                self.visibilityGraphsAll.append(self.visibilityGraphs[key])
                dataAppend = [self.pathToVisibilityGraphs[0].split('/')[-1], indexKey+1, indexKey+1, 'gray']
                self.resultsTable.loc[len(self.resultsTable)] = dataAppend
        else:
            for index, graphSet in enumerate(self.pathToVisibilityGraphs):
                self.visibilityGraphs = {}
                graphCounter = 1
                with open(graphSet, 'rb') as pickleFile:
                    try:
                        while True:
                            obj = pickle.load(pickleFile)
                            try:
                                items = obj.items()
                                self.visibilityGraphs = obj
                            except (AttributeError, TypeError):
                                self.visibilityGraphs[graphCounter] = obj
                                graphCounter += 1
                    except EOFError:
                        pass
                for indexKey, key in enumerate(self.visibilityGraphs.keys()):
                    self.visibilityGraphsAll.append(self.visibilityGraphs[key])
                    dataAppend = [graphSet.split('/')[-1], indexKey+1, self.inputLabels[index], self.colorList[index]]
                    self.resultsTable.loc[len(self.resultsTable)] = dataAppend

        if len(self.visibilityGraphsAll) <= 200:
            self.distanceMatrix = self.calculate_distance_matrix(self.visibilityGraphsAll)
            np.save(self.outputFolder + "/distanceMatrix.npy", self.distanceMatrix)
            self.resultsTable.to_csv(self.outputFolder + "/annotationsDistanceMatrix.csv")
            if self.plotPCA == True:
                self.plot_PCA(self.distanceMatrix, self.resultsTable)
            if self.plotDendrogram == True:
                self.plot_Dendrogram(self.distanceMatrix, self.resultsTable)
        else:
            messagebox.showinfo("Warning", "The number of graphs you selected is too large.")

    def calculate_distance_matrix(self, visibilityGraphs):
        """
        calculate the distance matrix of the input visibility graphs
        """
        show_Message("...Calculate distance matrix.")
        self.distanceMatrix = np.zeros((len(visibilityGraphs), len(visibilityGraphs)))
        for index in range(len(visibilityGraphs)):
            graph1 = visibilityGraphs[index]
            for pair in range(len(visibilityGraphs)):
                graph2 = visibilityGraphs[pair]
                distance = self.calculate_Laplacian(graph1, graph2)
                self.distanceMatrix[index, pair] = distance
        return(self.distanceMatrix)

    def calculate_Laplacian(self, graph1, graph2):
        """
        calculate the distance between two graphs using the Kolmogorov-Smirnov statistic of the eigenvalue distributions of the Laplacian matrices
        """
        laplacianGraph1 = nx.laplacian_matrix(graph1).toarray()
        laplacianGraph2 = nx.laplacian_matrix(graph2).toarray()
        eigenvaluesGraph1 = np.linalg.eig(laplacianGraph1)[0]
        normalizedEigenvaluesGraph1 = eigenvaluesGraph1 / np.max(eigenvaluesGraph1)
        eigenvaluesGraph2 = np.linalg.eig(laplacianGraph2)[0]
        normalizedEigenvaluesGraph2 = eigenvaluesGraph2 / np.max(eigenvaluesGraph2)
        distance = sp.stats.ks_2samp(normalizedEigenvaluesGraph1, normalizedEigenvaluesGraph2)[0]
        return(distance)

    def plot_PCA(self, distanceMatrix, resultsTable):
        """
        plot a PCA from the provided distance matrix and labels
        """
        if resultsTable['Label'].dtype == 'float':
            labels = [int(element) for element in resultsTable['Label']]
        else:
            labels = list(resultsTable['Label'])
        colors = resultsTable['Color']
        pca = sklearn.decomposition.PCA(n_components=2)
        principalComponents = pca.fit_transform(distanceMatrix)

        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        ax.set_xlabel('PC1 (' + str(np.round(pca.explained_variance_ratio_[0] * 100, 1)) + '%)')
        ax.set_ylabel('PC2 (' + str(np.round(pca.explained_variance_ratio_[1] * 100, 1)) + '%)')
        if len(np.unique(colors)) == 1:
            ax.scatter(principalComponents[:, 0], principalComponents[:, 1], c=colors, s=50, marker='o')
            for index, text in enumerate(labels):
                ax.annotate(text, (principalComponents[index][0]+0.03, principalComponents[index][1]))
        else:
            start, stop  = 0, 0
            for index, color in enumerate(np.unique(colors)):
                stop = len(resultsTable[resultsTable['Color'] == color]) + stop
                selectedPC1, selectedPC2 = principalComponents[start:stop, 0], principalComponents[start:stop, 1]
                ax.scatter(selectedPC1, selectedPC2, c=color, s=50, marker='o', label=labels[start])
                start += len(resultsTable[resultsTable['Color'] == color])
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), fancybox=True, shadow=True, ncol=5)
        fig.savefig(self.outputFolder + '/PCA_DistanceMatrix.png', bbox_inches='tight', dpi=300)

    def plot_Dendrogram(self, distanceMatrix, resultsTable):
        """
        plot the dendrogram of the calculated distance matrix using complete linkage hierarchical clustering
        """
        if resultsTable['Label'].dtype == 'float':
            labels = [int(element) for element in resultsTable['Label']]
        else:
            labels = list(resultsTable['Label'])
        upperTriangle = sp.spatial.distance.squareform(distanceMatrix)
        linked = sp.cluster.hierarchy.linkage(upperTriangle, 'complete')

        fig = plt.figure(figsize=(5, 3))
        sp.cluster.hierarchy.dendrogram(linked, orientation='top', labels=labels, distance_sort='descending', show_leaf_counts=True)
        plt.xticks(fontsize=7, rotation=45)
        plt.yticks(fontsize=7)
        fig.savefig(self.outputFolder + '/Dendrogram_DistanceMatrix.png', bbox_inches='tight', dpi=300)

##### general functions #####
def show_Message(msg):
    logging.info(msg)

def keep_labels_on_border(labeledImage):
    """
    modified version of skimage.segmentation.clear_border to keep only labels touching the image border
    """
    image = labeledImage
    # create borders with buffer_size
    borders = np.zeros_like(image, dtype=np.bool_)
    ext = 1
    slstart = slice(ext)
    slend   = slice(-ext, None)
    slices  = [slice(s) for s in image.shape]
    for d in range(image.ndim):
        slicedim = list(slices)
        slicedim[d] = slstart
        borders[tuple(slicedim)] = True
        slicedim[d] = slend
        borders[tuple(slicedim)] = True

    labels = skimage.measure.label(image, background=0)
    number = np.max(labeledImage) + 1
    # determine all objects that are connected to borders
    borders_indices = np.unique(labeledImage[borders])
    indices = np.arange(number + 1)
    # mask all label indices that are not connected to borders
    label_mask = ~np.in1d(indices, borders_indices)
    mask = label_mask[labeledImage.ravel()].reshape(labeledImage.shape)
    image[mask] = 0
    return(image)

def find_edge_contour(image):
    """
    extract contour of artificial edges
    """
    # add buffer to image to detect contour also on borders
    bufferedImage = skimage.util.pad(image, pad_width=2, mode='constant')
    edgeContour = find_contour_of_object(bufferedImage)
    return(edgeContour)

def find_contour_of_object(cellObject):
    """
    find contour of an object
    """
    contour = []
    coord = np.transpose(np.where(cellObject != 0))
    lenX, lenY = cellObject.shape[0] - 1, cellObject.shape[1] - 1
    for x,y in coord:
        xmin,xmax = bounds(x-1, 0, lenX), bounds(x+1, 0, lenX)
        ymin,ymax = bounds(y-1, 0, lenY), bounds(y+1, 0, lenY)
        if xmax != x and xmin != x and ymax != y and ymin != y:
            if cellObject[xmin, y] == 0 and [xmin, y] not in contour:
                    contour.append([xmin, y])
            if cellObject[x, ymin] == 0 and [x, ymin] not in contour:
                    contour.append([x, ymin])
            if cellObject[x, ymax] == 0 and [x, ymax] not in contour:
                    contour.append([x, ymax])
            if cellObject[xmax, y] == 0 and [xmax, y] not in contour:
                    contour.append([xmax, y])
        else:
            if [x, y] not in contour:
                contour.append([x, y])
    return(np.asarray(contour))

def bounds(x,xmin,xmax):
    """
    define bounds of image window
    """
    if (x <= xmin): #if x is smaller than xmin, set x to xmin
        x = xmin
    elif ( x >= xmax):   #if x is larger than xmax, set x to xmax
        x = xmax
    return(x)

def contour_orientation(window):
    """
    define the orientatin of the image pixel window
    """
    orient = []
    if np.sum(window[:, 0] > 0) == 3:
        orient.append('left')
    if np.sum(window[:, 2] > 0) == 3:
        orient.append('right')
    if np.sum(window[0, :] > 0) == 3:
        orient.append('top')
    if np.sum(window[2, :] > 0) == 3:
        orient.append('bottom')
    return(orient)

def measure_intensity_along_contour(image, x, y, orientation, listOfCorrectedPixels):
    """
    measure intensity along contour to detect intensity gradients
    """
    lx, ly = image.shape[0] - 1, image.shape[1] - 1
    if 'top' in orientation:
        xmin, xmax = bounds(x-10, 0, lx), bounds(x+1, 0, lx)
        ymin, ymax = bounds(y-1, 0, ly), bounds(y+2, 0, ly)
        new_window = image[xmin:xmax, ymin:ymax].astype('int')
        window_means = np.mean(new_window, axis=1)[::-1]

    if 'right' in orientation:
        xmin, xmax = bounds(x-1, x, lx), bounds(x+2, 0, lx)
        ymin, ymax = bounds(y, 0, ly), bounds(y+11, 0, ly)
        new_window = image[xmin:xmax, ymin:ymax].astype('int')
        window_means = np.mean(new_window, axis=0)

    if 'bottom' in orientation:
        xmin, xmax = bounds(x, 0, lx), bounds(x+11, 0, lx)
        ymin, ymax = bounds(y-1, 0, ly), bounds(y+2, 0, ly)
        new_window = image[xmin:xmax, ymin:ymax].astype('int')
        window_means = np.mean(new_window, axis=1)

    if 'left' in orientation:
        xmin, xmax = bounds(x-1, 0, lx), bounds(x+2, 0, lx)
        ymin, ymax = bounds(y-10, 0, ly), bounds(y+1, 0, ly)
        new_window = image[xmin:xmax, ymin:ymax].astype('int')
        window_means = np.mean(new_window, axis=0)[::-1]

    if len(window_means) > 5:
        window_percentage = window_means[1:] * 100 / window_means[0]
        if window_percentage[2] > 25 and [x, y] not in listOfCorrectedPixels:
            listOfCorrectedPixels.append([x, y])
    return(listOfCorrectedPixels)

def tube_filter(image, sigma):
    """
    enhance tube-like structures
    """
    if Version(skimage.__version__) < Version('0.14'):
        imH=skimage.feature.hessian_matrix(image, sigma=sigma, mode='reflect')
        imM=skimage.feature.hessian_matrix_eigvals(imH[0], imH[1], imH[2])
    else:
        imH=skimage.feature.hessian_matrix(image, sigma=sigma, mode='reflect', order='xy')
        imM=skimage.feature.hessian_matrix_eigvals(imH)
    imR = -1.0 * imM[1]
    imT = 255.0 * (imR - imR.min()) / (imR.max() - imR.min())
    imT = imT.astype('int')
    return(imT)

def correct_gaps_in_skeleton(skeletonImage):
    """
    find gaps in the skeleton and close them if the gap is small and both ends have the same direction/angle
    """
    skeletonImage = skeletonImage * 1
    correctedSkeletonImage = skeletonImage.copy()
    endpoints = detect_crossings_and_endpoints(skeletonImage, mode='endpoints', output='list')
    if len(endpoints) != 0:
        distanceBins = sort_coordinate_distances(endpoints)
        correctingEndpoints = np.transpose(np.where(distanceBins==1))
        imageEndpointsCrossings = detect_crossings_and_endpoints(skeletonImage, mode='both', output='image')

        for xPos, yPos in correctingEndpoints:
            angles, rows, columns = evaluate_angle(xPos, yPos, endpoints, imageEndpointsCrossings)
            if len(angles) != 0 and (np.max(angles) - np.min(angles) < 20):
                correctedSkeletonImage[rows, columns] = 2
                #print("Correction added: ", str(xPos), str(yPos))
    return(correctedSkeletonImage)

def evaluate_angle(x, y, endpoints, image):
    """
    evaluate whether the angles of both endpoints are similar
    """
    allAngles = []
    xPos1, yPos1 = endpoints[x]
    xPos2, yPos2 = endpoints[y]
    rows, columns = skimage.draw.line(xPos1, yPos1, xPos2, yPos2)
    if np.sum(image[rows[1:-1], columns[1:-1]]) == 0:
        angleEndpoint1 = measure_angle_of_endpoints(xPos1, yPos1, image)
        angleEndpoint2 = measure_angle_of_endpoints(xPos2, yPos2, image)
        if xPos2 < xPos1:
            angleBetweenEndpoints = angle180([yPos2 - yPos1, xPos2 - xPos1])
        else:
            angleBetweenEndpoints angle180([yPos1 - yPos2, xPos1 - xPos2])
        allAngles = [angleEndpoint1, angleEndpoint2, angleBetweenEndpoints]
    return(allAngles, rows, columns)

def create_window(image, x, y, xUp, xDown, yLeft, yRight):
    """
    create a window from the specified coordinates in the image
    """
    lx, ly = image.shape[0] - 1, image.shape[1] - 1
    xmin, xmax = bounds(x - xUp, 0, lx), bounds(x + xDown, 0, lx)
    ymin, ymax = bounds(y - yLeft, 0, ly), bounds(y + yRight, 0, ly)
    window = image[xmin:xmax, ymin:ymax].copy()
    return(window, [xmin, xmax, ymin, ymax])

def sort_coordinate_distances(points):
    """
    sort the distances of different points into bins
    """
    distance = sp.spatial.distance_matrix(points, points)
    bins = [0, 1, 10, 20, 50, 100, 500, 1000, 9999]
    distance_bins = np.zeros((len(points), len(points))).astype('int')
    for i, (b1, b2) in enumerate(zip(bins[:-1], bins[1:])):
        ida = (distance >= b1) * (distance < b2)
        distance_bins[ida] = i
    distance_bins = np.tril(distance_bins)
    return(distance_bins)

def detect_crossings_and_endpoints(skeletonImage, mode='both', output='image'):
    """
    detect crossings and endpoints of the skeleton
    """
    skeletonImage = skeletonImage * 1
    detected_nodes = skeletonImage.copy()
    node_list = []
    coord = np.transpose(np.where(skeletonImage == 1))
    for x, y in coord:
        window, winBounds = create_window(skeletonImage, x, y, 1, 2, 1, 2)
        window[x - winBounds[0], y - winBounds[2]] = 0
        labeledWindow, L = sp.ndimage.label(window)
        if mode == 'both' or mode == 'endpoints':
            if L == 1 or L == 0:
                detected_nodes[x, y] = 3
                node_list.append([x, y])
        if mode == 'both' or mode == 'crossings':
            if L == 3 or L == 4:
                detected_nodes[x, y] = 2
                node_list.append([x, y])
            if L == 2:
                windowDetected, _ = create_window(dtected_nodes, x, y, 1, 2, 1, 2)
                windowDetected[x - winBounds[0], y - winBounds[2]] = 0
                labeledWindowConnectivity, Lconnectivity = sp.ndimage.label(windowDetected, np.ones((3, 3)))
                if 2 not in windowDetected and Lconnectivity == 1:
                    detected_nodes[x, y] = 2
                    node_list.append([x, y])
    if output == 'image':
        return(detected_nodes)
    else:
        return(np.asarray(node_list))

def angle180(dxy):
    """
    calculate the angle between two points in 180 degree range
    """
    dx, dy = dxy
    rad2deg = 180.0 / np.pi
    angle = np.mod(np.arctan2(-dx, -dy) * rad2deg + 360.0, 360.0)
    if angle >= 270:
        angle = 360 - angle
    return(angle)

def measure_angle_of_endpoints(x, y, image):
    """
    measure the angle between two endpoint of the skeleton
    """
    window, winBounds = create_window(image, x, y, 5, 6, 5, 6)
    cleanedWindow = (window > 0) * 1
    labeledWindow, labelsWindow = sp.ndimage.label(cleanedWindow, np.ones((3, 3)))
    labelSkeleton = labeledWindow[x - winBounds[0], y - winBounds[2]]
    coordLabel = np.transpose(np.where(labeledWindow == labelSkeleton))
    newWindow = window.copy() * 0
    for s, t in coordLabel:
        newWindow[s, t] = window[s, t]

    if 2 in newWindow:
        coord = np.transpose(np.where(newWindow == 2))
        dista = []
        for s, t in coord:
            dista.append(euclidean([s, t], [x - winBounds[0], y - winBounds[2]]))
        w = np.argmin(dista)
        if x < coord[w][0] + winBounds[0]:
            angle = angle180([y - (coord[w][1] + winBounds[2]), x - (coord[w][0] + winBounds[0])])
        else:
            angle = angle180([(coord[w][1] + winBounds[2]) - y, (coord[w][0] + winBounds[0]) - x])
    else:
        coord = np.transpose(np.where(window == 1))
        dista = []
        for s, t in coord:
            dista.append(euclidean([s, t], [x - winBounds[0], y - winBounds[2]]))
        if len(dista) != 0:
            w = np.argmax(dista)
            if x < coord[w][0] + winBounds[0]:
                angle = angle180([y - (coord[w][1] + winBounds[2]), x - (coord[w][0] + winBounds[0])])
            else:
                angle = angle180([(coord[w][1] + winBounds[2]) - y, (coord[w][0] + winBounds[0]) - x])
        else:
            angle = 0
    return(angle)

def euclidean(x, y):
    """
    calculate the Euclidean distance between two points
    """
    dist = math.sqrt(((int(x[0]) - int(y[0])) ** 2) + ((int(x[1]) - int(y[1])) ** 2))
    return(dist)

def detect_branches(skeletonImage, mode='remove'):
    """
    remove skeleton branches by tracking from endpoints back to crossings
    """
    detected_nodes = detect_crossings_and_endpoints(skeletonImage, mode='both', output='image')
    branch_filament = (detected_nodes == 3).sum()
    while branch_filament > 0:
        branchless = track_or_remove_branches(detected_nodes, mode=mode)
        detected_nodes = detect_crossings_and_endpoints(branchless, mode='both', output='image')
        branch_filament = (detected_nodes == 3).sum()
    if mode == 'remove':
        return(detected_nodes > 0)
    else:
        return(detected_nodes)

def track_or_remove_branches(detected_nodes, mode):
    """
    depending on the mode either remove or track detected branches
    """
    branch_filament = (detected_nodes==3).sum()
    while branch_filament > 0:
        coord = np.transpose(np.where(detected_nodes==3))
        for x, y in coord:
            window, winBounds = create_window(detected_nodes, x, y, 1, 2, 1, 2)
            label_counts = np.sum(np.unique(window) > 0)
            label_sum = np.sum(window)
            label_number = np.sum(window > 0)
            if mode == 'remove':
                if label_counts == 2:
                    detected_nodes[winBounds[0]:winBounds[1], winBounds[2]:winBounds[3]] = np.where(window == 1, 3, window)
                detected_nodes[x, y] = 0
            else:
                if (label_counts <= 3 and label_sum < 9) or (label_sum == 9 and label_number == 4):
                    detected_nodes[winBounds[0]:winBounds[1], winBounds[2]:winBounds[3]] = np.where(window == 1, 3, window)
                detected_nodes[x, y] = 4
        branch_filament = (detected_nodes == 3).sum()
    if mode == 'remove':
        return(detected_nodes > 0)
    else:
        return(detected_nodes)

def create_labeled_and_tracked_image(skeletonImage, labeledImage):
    """
    create a labeled image, where background=0, skeleton=1, tracked branches=2 and cell labels>=3
    """
    labeledTrackedImage = labeledImage.copy() + 3
    trackedImage = detect_branches(skeletonImage, mode='track')
    trackedPixels = np.transpose(np.where(trackedImage ==4))
    skeletonPixels = np.transpose(np.where(labeledTrackedImage == 3))
    backgroundPixels = np.transpose(np.where(labeledTrackedImage == 4))

    labeledTrackedImage[backgroundPixels[:,0], backgroundPixels[:,1]] = 0
    labeledTrackedImage[skeletonPixels[:,0], skeletonPixels[:,1]] = 1
    labeledTrackedImage[trackedPixels[:,0], trackedPixels[:,1]] = 2
    return(labeledTrackedImage)

def marching_squares(contour, cellImage):
    """
    sort contour coordinates using marchin squares algorithm
    """
    contourCopy = contour.copy()
    orderedContour = np.empty(shape = [0, 2])
    xRight,yRight = find_rightmost_point(contour)
    contourImage = cellImage.copy() * 2
    contourImage[contour[:, 0], contour[:, 1]] = 1
    timeout = 120
    startTime = time.time()
    while len(contourCopy) > 0:
        timeDelta = time.time() - startTime
        if timeDelta >= timeout:
            show_Message('......Encountered timeout error while sorting the contour coordinates.')
            break
        window = contourImage[xRight:xRight+2, yRight:yRight+2]
        nextWindow, nextContourPixel = orientation(window)
        if len(nextContourPixel) > 0:
            for pixel in range(len(nextContourPixel)):
                xPos, yPos = xRight + nextContourPixel[pixel][0], yRight + nextContourPixel[pixel][1]
                arrayPosition = np.where((orderedContour == [xPos, yPos]).all(axis=1))[0]
                if len(arrayPosition) == 0:
                    index = find_index_of_coordinates([xPos, yPos], contourCopy, [0], 'index')
                    if len(index) != 0:
                        orderedContour = np.append(orderedContour, [[xPos, yPos]], axis=0)
                        contourCopy = np.delete(contourCopy, index[0], 0)
                        'orderedContour'
                else:
                    contourCopy = []
        if nextWindow == 'left':
            yRight = yRight - 1
        elif nextWindow == 'right':
            yRight = yRight + 1
        elif nextWindow == 'up':
            xRight = xRight- 1
        elif nextWindow == 'down':
            xRight = xRight + 1
    if len(orderedContour) != len(contour):
        clockwise = []
    else:
        clockwise = np.append([orderedContour[0]], orderedContour[-1:0:-1], axis=0)
        clockwise = clockwise.astype('int')
    return(clockwise)

def find_rightmost_point(contour):
    """
    return the rightmost point of a list of coordinates
    """
    index = np.where(contour[:, 1] == np.max(contour[:, 1]))[0]
    return(contour[index[0]][0], contour[index[0]][1])

def orientation(window):
    """
    define the direction of the shift for the next window according to the marching square algorithm
    """
    orient=''
    nextContourPixel = []
    if np.sum(window > 0) == 0:
        orient = 'right'
    elif np.sum(window > 0) == 1:
        if window[0, 0] != 0:
            orient = 'up'
        elif window[0, 1] != 0:
            orient = 'right'
        elif window[1, 0] != 0:
            orient = 'left'
        elif window[1, 1] != 0:
            orient = 'down'
    elif np.sum(window > 0) == 2:
        if window[0, 1] != 0 and window[1, 1] != 0:
            orient = 'down'
            nextContourPixel = [[1, 1]]
        elif window[0, 0] != 0 and window[0, 1] != 0:
            orient = 'right'
            nextContourPixel = [[0, 1]]
        elif window[0, 0] != 0 and window[1, 0] != 0:
            orient = 'up'
            nextContourPixel = [[0, 0]]
        elif window[1, 0] != 0 and window[1, 1] != 0:
            orient = 'left'
            nextContourPixel = [[1, 0]]
        elif window[0, 0] != 0 and window[1, 1] != 0:
            orient = 'up'
            nextContourPixel = [[0, 0]]
        elif window[0, 1] != 0 and window[1, 0] != 0:
            orient = 'left'
            nextContourPixel = [[1, 0]]
    elif np.sum(window > 0) == 3:
        if window[0, 0] != 0 and window[0, 1] != 0 and window[1, 1] != 0:
            orient = 'down'
            if window[0, 1] == 1:
                nextContourPixel = [[0, 1], [1, 1]]
            else:
                nextContourPixel = [[1, 1]]
        elif window[0, 0] != 0 and window[1, 0] != 0 and window[1, 1] != 0:
            orient = 'up'
            if window[1, 0] == 1:
                nextContourPixel = [[1, 0], [0, 0]]
            else:
                nextContourPixel = [[0, 0]]
        elif window[0, 1] != 0 and window[1, 0] != 0 and window[1, 1] != 0:
            orient = 'left'
            if window[1, 1] == 1:
                nextContourPixel = [[1, 1], [1, 0]]
            else:
                nextContourPixel = [[1, 0]]
        elif window[0, 0] != 0 and window[0, 1] != 0 and window[1, 0] != 0:
            orient = 'right'
            if window[0, 0] == 1:
                nextContourPixel = [[0, 0], [0, 1]]
            else:
                nextContourPixel = [[0, 1]]
    else:
        print('Error: too many pixels in window.')
    return(orient, nextContourPixel)

def find_index_of_coordinates(point, array, radius, output):
    """
    find position of point coordinates around radius in an array
    """
    foundPositions = []
    combinations = list(itertools.product(radius, repeat=2))
    for xRadius, yRadius in combinations:
        w = np.where((point[0]+xRadius == array[:, 0]) & (point[1]+yRadius == array[:, 1]))[0]
        if len(w) > 0:
            if output == 'index':
                foundPositions.append(w[0])
            else:
                foundPositions.append([xRadius, yRadius])
    return(foundPositions)

def calculate_pixel_distance(resolution):
    """
    calculate the optimal pixel distance between nodes along the contour from the image resolution
    """
    pixelDistance = int(np.round(1 / (resolution * 0.65)))
    return(pixelDistance)

def interpolate_contour_pixels(cellContour, pixelDistance):
    """
    determine all cell contour pixels which will be assigned as nodes according to the optimal pixel distance
    """
    pixelsOnContour = {}
    contourLength = len(cellContour)
    contourIndices = np.round(np.linspace(0, contourLength - pixelDistance, (contourLength - pixelDistance) / pixelDistance)).astype('int')
    pixels = np.asarray(cellContour[contourIndices])
    for idx in range(len(pixels)):
        pixelsOnContour[idx] = (pixels[idx][0], pixels[idx][1])
    return(pixelsOnContour)

def invert(image):
    """
    invert image
    """
    if image.dtype == 'bool':
        return ~image
    else:
        return dtype.dtype_limits(image, clip_negative=False)[1] - image

def find_local_extrema(array):
    """
    find local minima and maxima in array
    """
    reverseArray = array[::-1]
    array = np.append(array, array[:1])
    reverseArray = np.append(reverseArray, reverseArray[:1])
    signsArray = calculate_consecutive_difference(array)
    signsReverseArray = calculate_consecutive_difference(reverseArray)[::-1]
    neckIndices = []
    lobeIndices = []
    for idx, sign in enumerate(signsArray):
        if sign == '-' and signsReverseArray[idx] == sign:
            lobeIndices.append(idx)
        elif sign == '+' and signsReverseArray[idx] == sign:
            neckIndices.append(idx)
    return(lobeIndices, neckIndices)

def calculate_consecutive_difference(sequence):
    """
    calculate the difference of consecutive elements in an array
    """
    difference = [elem1 - elem2 for elem1, elem2 in zip(sequence[:-1], sequence[1:])]
    signedDifference = np.sign(difference)
    signedSequence = convert_to_sign(signedDifference)
    return(signedSequence)

def convert_to_sign(sequence):
    """
    convert signed numbers into + and - signs
    """
    signs = []
    for idx in range(len(sequence)):
        if sequence[idx] > 0:
            signs.extend('+')
        elif sequence[idx] < 0:
            signs.extend('-')
        else:
            signs.extend('0')
    return(''.join(signs))

def get_key_from_value(dictionary, value):
    """
    get the dictionary key of a specified value
    """
    for key, val in dictionary.items():
        if val == value:
            return(key)
