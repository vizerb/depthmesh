# Script to be called as subprocess from addon to run inference
EXEC_PROVIDER = "CUDA"

import sys

if len(sys.argv) < 2:
    raise ValueError("Input file path not provided")

input_filepath = sys.argv[1]

# Append the extensions modules to path
extension_sp = sys.argv[2]
sys.path.append(extension_sp)

try:
    from PIL import Image
    import pickle
    from inference import Inference
except ImportError as e:
    print(f"Failed to import required packages: {e}")

inference = Inference(EXEC_PROVIDER)
inference.loadModel()

input_image = Image.open(input_filepath)
if input_image is None:
    raise ValueError(f"Failed to load image from {input_filepath}")

[depth,focallength_px] = inference.infer(input_image)

out_dict = {
    "depth": depth,
    "focal_length": focallength_px
}
pickle.dump(out_dict, sys.stdout.buffer)