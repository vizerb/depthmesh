#!/bin/python3

import subprocess
import sys
import glob
import zipfile
import os
import sys

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

                    
def progress_bar(count, total, status=''):
    bar_length = 40
    filled_length = int(bar_length * count / total)
    percent = round(100.0 * count / total, 1)
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f'\r[{bar}] {percent}% {status}')
    sys.stdout.flush()

def download_file(url, destination):
    import urllib.request

    if os.path.exists(destination):
        print(f"File {destination} already exists, skipping download.")
        return

    try:
        response = urllib.request.urlopen(url)
        total_size = int(response.headers['Content-Length'])
        downloaded_size = 0
        block_size = 8192
        with open(destination, 'wb') as f:
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                downloaded_size += len(buffer)
                f.write(buffer)
                progress_bar(downloaded_size, total_size, status='Downloading')
        print(f"\nDownloaded file from {url} to {destination}.")
    except Exception as e:
        print(f"Error downloading file from {url}: {str(e)}")


def build_model_command():
    #cmd = "wget -O model.onnx -nc https://huggingface.co/onnx-community/DepthPro-ONNX/resolve/main/onnx/model_fp16.onnx?download=true"
    cmd = "wget -O model.onnx -nc https://huggingface.co/onnx-community/DepthPro-ONNX/resolve/main/onnx/model_q4f16.onnx?download=true"
    
    return cmd

def try_call(cmd, stage):
    print(f"\n\n{stage}\n\n")
    ret = subprocess.run(cmd, shell=True)
    print (ret.returncode)
    if ret.returncode == 1:
        print("Model already downloaded or error occured, skipping")
    elif ret.returncode != 0:
        print(f"Error {stage}")
        sys.exit(1)


SKIP_MODEL = False  # Skip downloading the model file (its too large for ci)
PYTHON_VERSION = "3.11"  # the version blender(4.2) uses
OS_TYPE = "linux"  # linux, mac, windows (mac not supported yet)
for arg in sys.argv:
    if arg.startswith("py="):
        PYTHON_VERSION = arg.split("=")[1]
    elif arg == "skip_model":
        SKIP_MODEL = True
    elif arg.startswith("os="):
        OS_TYPE = arg.split("=")[1]

###
### Download wheels for the specified modules
###
# MODULES
# Delete old wheels folder and addon zip
cmd = "rm -rf wheels"
try_call(cmd, "Deleting old wheels")

modules = [
    "numpy",
    "opencv-python-headless",
    "psutil",
    "pandas",   # Could use built-in csv module and csv files
    "onnxruntime-directml",
]

cmd = build_wheel_command(modules, OS_TYPE, PYTHON_VERSION)
try_call(cmd, "Downloading wheels")
#cmd_linux = build_wheel_command(modules, "linux", PYTHON_VERSION)
#cmd_win = build_wheel_command(modules, "windows", PYTHON_VERSION)

#try_call(cmd_linux, "Downloading linux wheels")
#try_call(cmd_win, "Downloading windows wheels")


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
    wheel_path = wheel.replace("\\", "/")
    wheels_str += f'\t"{wheel_path}",\n'
content = content[:start] + wheels_str + content[end:]

with open("blender_manifest.toml", "w") as f:
    f.write(content)

###
### Download the model if not skipped
###
if not SKIP_MODEL:
    # cmd = build_model_command()
    # try_call(cmd, "Downloading model")
    print("Downloading model")
    download_file("https://huggingface.co/onnx-community/DepthPro-ONNX/resolve/main/onnx/model_q4f16.onnx?download=true", "model.onnx")

###
### Zip the addon
###
# Get the addon id and version from manifest

start = content.find('id = "') + len('id = "')
end = content.find('"', start)
id = content[start:end]
start = content.find('version = "') + len('version = "')
end = content.find('"', start)
version = content[start:end]

excluded_dirs = ["cpu_wheels", "models", "release", "testing", ".git", ".gitea"]
excluded_patterns = ["*.save", "*.zip", "*.blend1", "*.sh", ".*", "build.py"]
zip_name = f"{id}-{version}.zip"

zip_directory(zip_name, excluded_dirs, excluded_patterns)



print("\n\nDone\n\n")