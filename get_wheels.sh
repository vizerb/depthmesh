#!/bin/bash

modules=("numpy" "onnxruntime-gpu" "opencv-python-headless" "psutil")
cmd="pip download "

for module in "${modules[@]}"; do
    cmd+=" ${module}"
done

# selected OS (default windows)
OS_TYPE=$1
platform="win_amd64"

if [ "$OS_TYPE" == "linux" ]; then
  platform="manylinux_2_28_x86_64"
fi

cmd+=" --dest ./wheels --only-binary=:all: --python-version=3.11 --platform=${platform}"

