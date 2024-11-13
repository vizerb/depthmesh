#!/bin/python3

import subprocess
import sys
import glob
import zipfile
import os

def build_wheel_command(modules, os_type, python_version="3.11"):
    cmd = "pip download "

    for module in modules:
        cmd += module + " "

    cmd += f" --dest ./wheels --only-binary=:all: --python-version={python_version}"
    
    if os_type == "linux":
        cmd += ""#" --platform manylinux_2_17_x86_64"
    elif os_type == "windows":
        cmd += " --platform win_amd64"
    else:
        raise ValueError("Unsupported OS_TYPE. Supported types are 'linux' and 'windows'.")

    return cmd

# This requires 7zip to be installed so its not used for now
def build_zip_command(excluded_dirs, excluded_patterns):
    cmd = "7za u -mx=0 -mmt=on dm.zip ./*"

    # Add exclusions for file types
    for pattern in excluded_patterns:
        cmd += f" -x'!{pattern}'"

    # Add exclusions for directories
    for dir in excluded_dirs:
        cmd += f" -xr'!./{dir}'"

    return cmd

def zip_directory(zip_name, excluded_dirs, excluded_patterns):
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_STORED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for file in files:
                file_path = os.path.join(root, file)
                # Exclude patterns
                if not any(glob.fnmatch.fnmatch(file, pattern) for pattern in excluded_patterns):
                    zipf.write(file_path, os.path.relpath(file_path, '.'))

def build_model_command():
    #cmd = "wget -O model.onnx -nc https://huggingface.co/onnx-community/DepthPro-ONNX/resolve/main/onnx/model_fp16.onnx?download=true"
    cmd = "wget -O model.onnx -nc https://huggingface.co/onnx-community/DepthPro-ONNX/resolve/main/onnx/model_q4.onnx?download=true"
    
    return cmd

def try_call(cmd, stage):
    print(f"\n\n{stage}\n\n")
    ret = subprocess.run(cmd, shell=True)
    print (ret.returncode)
    if ret.returncode == 1:
        print("Model already downloaded, skipping")
    elif ret.returncode != 0:
        print(f"Error {stage}")
        sys.exit(1)


SKIP_MODEL = False  # Skip downloading the model file (its too large for ci)
PYTHON_VERSION = "3.11"  # the version blender(4.2) uses
for arg in sys.argv:
    if arg.startswith("py="):
        PYTHON_VERSION = arg.split("=")[1]
        break
    elif arg == "skip_model":
        SKIP_MODEL = True

###
### Download wheels for the specified modules
###
# MODULES
# Delete old wheels folder and addon zip
cmd = "rm -rf wheels dm.zip"
try_call(cmd, "Deleting old wheels")

modules = [
    "numpy",
    "opencv-python-headless",
    "psutil",
    "pandas",   # Could use built-in csv module and csv files
    "onnxruntime-directml",
]

cmd_win = build_wheel_command(modules, "windows", PYTHON_VERSION)

try_call(cmd_win, "Downloading windows wheels")


###
### Write the wheel locations to the blender manifest file
###
wheels = glob.glob("wheels/*.whl")
with open("blender_manifest_base.toml", "r") as f:
    content = f.read()

start = content.find("wheels = [") + len("wheels = [")
end = content.find("]", start)
wheels_str = "\n"
for wheel in wheels:
    wheels_str += f'\t"{wheel}",\n'
content = content[:start] + wheels_str + content[end:]

with open("blender_manifest.toml", "w") as f:
    f.write(content)

###
### Download the model if not skipped
###
if not SKIP_MODEL:
    cmd = build_model_command()
    try_call(cmd, "Downloading model")

###
### Zip the addon
###
excluded_dirs = ["cpu_wheels", "models", "release", "testing", ".git"]
excluded_patterns = ["*.save", "*.zip", "*.blend1", "*.sh", ".*", "build.py"]

zip_name = "dm.zip"
USE_7ZIP = False

if USE_7ZIP:
    cmd = build_zip_command(excluded_dirs, excluded_patterns)
    try_call(cmd, "Zipping files")
else:
    zip_directory(zip_name, excluded_dirs, excluded_patterns)



print("\n\nDone\n\n")