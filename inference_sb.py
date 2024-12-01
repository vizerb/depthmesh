def preprocess_image(input_image, input_size):
    import numpy as np
    
    image_mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    image_std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    
    #image = input_image.convert("RGB")
    image = input_image
    
    image = image.resize(input_size)  # Resize to the model's expected input size
    
    image = np.array(image, dtype=np.float32)
    image /= 255.0  # Normalize to [0, 1]
    image = (image - image_mean) / image_std

    image = np.transpose(image, (2, 0, 1))  # Change data layout from HWC to CHW
    image = np.expand_dims(image, axis=0)  # Add batch dimension

    return image


import sys
import os

if len(sys.argv) < 2:
    raise ValueError("Input file path not provided")

input_filepath = sys.argv[1]


extension_sp = sys.argv[2]
#print(extension_sp)
#print(sys.path[0])
if (sys.path[0] != extension_sp):
    #print("entered")
    sys.path.insert(0,extension_sp)
    pass
#sys.path.insert(0,"/home/flare/.config/blender/4.3/extensions/.local/lib/python3.11/site-packages")
#exit()
try:
    from PIL import Image
    import numpy as np
    import onnxruntime as ort
except ImportError as e:
    #pass
    print(f"Failed to import required packages: {e}")

model_file_name = "model.onnx"

input_size = (1536, 1536)

model_dir = os.path.dirname(__file__)
model_path = os.path.join(model_dir, model_file_name)


providers = [
    'CUDAExecutionProvider',
    #'CPUExecutionProvider',
]

# Only log errors
ort.set_default_logger_severity(3)
sess_options = ort.SessionOptions()
ort_session = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)

#input_image = cv2.imread(input_filepath)
input_image = Image.open(input_filepath)
if input_image is None:
    raise ValueError(f"Failed to load image from {input_filepath}")

onnx_input = preprocess_image(input_image, input_size)
input_name = ort_session.get_inputs()[0].name

outputs = ort_session.run(None, {input_name: onnx_input})        

depth = outputs[0].squeeze()  # Depth in [m].
focallength_px = outputs[1][0][0]  # Focal length in pixels.

import pickle

out_dict = {
    "depth": depth,
    "focal_length": focallength_px
}
pickle.dump(out_dict, sys.stdout.buffer)
