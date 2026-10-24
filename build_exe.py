# Build Standalone Windows Executable (.exe) for AIS-140 Simulator
# Configured specifically to avoid Windows Defender false positives:
#  1. --noupx: Disables UPX packing (UPX triggers heuristic detections)
#  2. app.manifest: Declares standard asInvoker execution level
#  3. version_info.txt: Complete Windows PE version info struct
#  4. Windowed: Clean GUI application mode
import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def build():
    print("==================================================")
    print("Building AIS-140 Simulator Desktop Executable (.exe)")
    print("==================================================")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=AIS140-Simulator",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--noupx",
        "--manifest=" + os.path.join(BASE_DIR, "app.manifest"),
        "--version-file=" + os.path.join(BASE_DIR, "version_info.txt"),
        "--add-data=src;src",
        os.path.join(BASE_DIR, "main.py")
    ]

    print("Running PyInstaller command:")
    print(" ".join(cmd))
    res = subprocess.run(cmd, cwd=BASE_DIR)
    if res.returncode == 0:
        dist_exe = os.path.join(BASE_DIR, "dist", "AIS140-Simulator", "AIS140-Simulator.exe")
        print("\n[SUCCESS] Build completed!")
        print(f"Executable output path:\n  {dist_exe}")
    else:
        print(f"\n[ERROR] PyInstaller failed with code {res.returncode}")
        sys.exit(res.returncode)

if __name__ == "__main__":
    build()
