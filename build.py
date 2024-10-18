#!/bin/python3

import subprocess
import sys

def build_wheel_command(modules, os_type):
    cmd = "pip download "

    for module in modules:
        cmd += module + " "

    cmd += " --dest ./wheels --only-binary=:all: --python-version=3.11"
    
    if os_type == "linux":
        cmd += " --platform manylinux2014_x86_64"
    elif os_type == "windows":
        cmd += " --platform win_amd64"
    else:
        raise ValueError("Unsupported OS_TYPE. Supported types are 'linux' and 'windows'.")

    return cmd

def build_zip_command(excluded_dirs, excluded_patterns):
    cmd = "7za u -mx=0 -mmt=on dm.zip ./*"

    # Add exclusions for file types
    for pattern in excluded_patterns:
        cmd += f" -x'!{pattern}'"

    # Add exclusions for directories
    for dir in excluded_dirs:
        cmd += f" -xr'!./{dir}'"

    return cmd

###
### Downloading wheels for the specified modules
###

# MODULES
modules = [
    "numpy",
    "onnxruntime-gpu",
    "opencv-python-headless",
    "psutil",
]

# OS TYPE
OS_TYPE = "linux"  # linux, mac, windows (mac not supported yet)
if len(sys.argv) > 1:
    OS_TYPE = sys.argv[1]
else:
    OS_TYPE = "linux"  # Default to linux if no argument is provided

cmd = build_wheel_command(modules, OS_TYPE)

subprocess.run(cmd, shell=True)

###
### Zip the addon
###
excluded_dirs = ["cpu_wheels", "models", "release", "testing", ".git"]
excluded_patterns = ["*.zip", "*.blend1", "*.sh", ".*", "build.py"]

cmd = build_zip_command(excluded_dirs, excluded_patterns)

subprocess.run(cmd, shell=True)
