# AIS-140 CGM Client Simulator — Entry point
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.gui.app import SimulatorApp
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulatorApp(root)
    root.mainloop()
