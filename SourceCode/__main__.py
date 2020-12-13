import sys
from tkinter import Tk
from GraVis.ShapeGUI import ShapeGui

def main():
    master = Tk()
    my_gui = ShapeGui(master)
    master.mainloop()
