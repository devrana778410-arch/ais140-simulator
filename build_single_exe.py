import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--name=AIS140-Simulator-Portable",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--noupx",
    "--onefile",
    "--manifest=" + os.path.join(BASE_DIR, "app.manifest"),
    "--version-file=" + os.path.join(BASE_DIR, "version_info.txt"),
    "--add-data=src;src",
    os.path.join(BASE_DIR, "main.py")
]

subprocess.run(cmd, cwd=BASE_DIR)
