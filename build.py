#!/bin/python3

import subprocess
import sys
import glob
import zipfile
import os

# pip download {modules} --dest ./wheels --only-binary=:all: --python-version=3.11 --platform {platform}
def build_wheel_command(modules, os_type, python_version="3.11"):
    cmd = "pip3 download "

    for module in modules:
        cmd += f'"{module}"' + " "

    cmd += f" --dest ./wheels --only-binary=:all: --python-version={python_version}"
    
    if os_type == "linux_x64":
        cmd += " --platform manylinux_2_27_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_12_x86_64"
    elif os_type == "windows_x64":
        cmd += " --platform win_amd64"
    elif os_type == "macos_arm64":
        cmd += " --platform macosx_13_0_universal2 --platform macosx_11_0_arm64"
    elif os_type == "macos_x64":
        cmd += " --platform macosx_13_0_universal2 --platform macosx_10_10_x86_64 --platform macosx_10_9_x86_64"
    else:
        raise ValueError("Unsupported OS_TYPE. Supported types are 'linux_x64', 'windows_x64', 'macos_x64' and 'macos_arm64'.")

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

def remove_directory(directory):
    if os.path.exists(directory):
        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(directory)

def try_call(cmd, stage):
    print(f"\n\n{stage}\n\n")
    ret = subprocess.run(cmd, shell=True)
    print (ret.returncode)
    if ret.returncode != 0:
        print(f"Error {stage}")
        sys.exit(1)



def build(os_type, exec_provider="cpu", python_version="3.11"):
    ##
    ## Write the exec_provider to global_vars
    ##
    with open("global_vars.py", "r") as f:
        content = f.read()

    start = content.find("EXEC_PROVIDER = '") + len("EXEC_PROVIDER = '")
    end = content.find("'", start)

    content = content[:start] + exec_provider.upper() + content[end:]

    with open("global_vars.py", "w") as f:
        f.write(content)


    ###
    ### Download wheels for the specified modules
    ###
    # Delete old wheels folder
    remove_directory("wheels")

    # MODULES
    modules = [
        "numpy",
        "pillow",
        "psutil",
    ]

    if exec_provider == "cpu":
        modules.append("onnxruntime<=1.22")
    elif exec_provider == "directml":
        modules.append("onnxruntime-directml")
    elif exec_provider == "cuda":
        cuda_modules = [
            "onnxruntime-gpu",
            "nvidia-cudnn-cu12",
            "nvidia-cuda-runtime-cu12",
            "nvidia-cufft-cu12",
            "nvidia-cudnn-cu12",
            "nvidia-curand-cu12",       # Needed for linux only
            "nvidia-cuda-nvrtc-cu12",   # Needed for linux only
        ]
        modules.extend(cuda_modules)
        
    cmd = build_wheel_command(modules, os_type, python_version)
    try_call(cmd, "Downloading wheels")

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
        print("Downloading model")
        download_file("https://huggingface.co/onnx-community/DepthPro-ONNX/resolve/main/onnx/model_q4f16.onnx?download=true", "model.onnx")

    ###
    ### Zip the addon
    ###

    # Get the addon id and version from manifest
    start = content.find('id = "') + len('id = "')
    end = content.find('"', start)
    id = content[start:end]
    start = content.find('\nversion = "') + len('\nversion = "')
    end = content.find('"', start)
    version = content[start:end]
    platform = os_type

    excluded_dirs = ["cpu_wheels", "models", "release", "testing", ".git", ".gitea"]
    excluded_patterns = ["*.save", "*.zip", "*.blend1", "*.sh", ".*", "build.py"]
    zip_name = f"{id}-{version}-{platform}-{exec_provider}.zip"

    zip_directory(zip_name, excluded_dirs, excluded_patterns)





##
## Arguments
##
SKIP_MODEL = False  # Skip downloading the model file (its too large for ci)
PYTHON_VERSION = "3.11"  # the version blender(4.2) uses
OS_TYPE = "linux"  # linux, mac, windows, mac(experimental)
EXEC_PROVIDER = "cpu"  # cpu, directml, cuda, rocm(not yet supported)
BUILDALL = False
for arg in sys.argv:
    if arg.startswith("os="):
        OS_TYPE = arg.split("=")[1]
    elif arg.startswith("ep="):
        EXEC_PROVIDER = arg.split("=")[1]
    elif arg.startswith("py="):
        PYTHON_VERSION = arg.split("=")[1]
    elif arg == "skip_model":
        SKIP_MODEL = True
    elif arg == "buildall":
        BUILDALL = True


build_configs = [
    ["windows_x64","cpu"],
    ["windows_x64","directml"],
    ["windows_x64","cuda"],
    ["linux_x64","cpu"],
    ["linux_x64","cuda"],
    ["macos_x64","cpu"],
    ["macos_arm64","cpu"],
]

if BUILDALL:
    for bc in build_configs:
        build(*bc,PYTHON_VERSION)    
else:
    build(OS_TYPE, EXEC_PROVIDER, PYTHON_VERSION)

print("\n\nDone\n\n")