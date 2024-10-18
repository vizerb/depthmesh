#!/bin/bash

#Remove the zip if it exists
#rm dm.zip

# List of directories to exclude (e.g., "dir1 dir2 dir3")
excluded_dirs=("cpu_wheels" "models" "release" "testing" ".git")

# List of file types to exclude (e.g., "zip tar.gz bak")
excluded_file_types=("zip" "blend1" "sh")

# Base 7za command
cmd="7za u -mx=0 -mmt=on dm.zip ./* "

# Add exclusion for hidden files
cmd += " -x'!.*'"

# Add exclusions for file types
for file_type in "${excluded_file_types[@]}"; do
    cmd+=" -x'!*.${file_type}'"
done

# Add exclusions for directories
for dir in "${excluded_dirs[@]}"; do
    cmd+=" -xr'!./${dir}'"
done

# Add model file
cmd += " models/model_fp16.onnx"

# Execute the command
echo "Running: $cmd"
eval $cmd

