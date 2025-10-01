# Script to be called as subprocess from addon to run inference on linux
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
    print(f"Failed to import required packages\n{e}")
    exit()

inference = Inference(EXEC_PROVIDER)
inference.loadModel()

try:
    input_image = Image.open(input_filepath)
except Image.DecompressionBombError:
    print(f"Image size exceeds limit of {Image.MAX_IMAGE_PIXELS*2} pixels")
    exit()
except Exception as e:
    print(f"Failed to load image\n{e}")
    exit()

depth, focallength_px = inference.infer(input_image)

out_dict = {
    "depth": depth,
    "focal_length": focallength_px
}
pickle.dump(out_dict, sys.stdout.buffer)