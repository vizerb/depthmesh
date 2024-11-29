
def preprocess_image(input_image, input_size):
    import cv2
    import numpy as np
    image_mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    image_std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    
    image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
    
    image = cv2.resize(image, input_size)  # Resize to the model's expected input size
    
    image = np.array(image, dtype=np.float32)
    image /= 255.0  # Normalize to [0, 1]
    image = (image - image_mean) / image_std

    image = np.transpose(image, (2, 0, 1))  # Change data layout from HWC to CHW
    image = np.expand_dims(image, axis=0)  # Add batch dimension

    return image


import sys
import site

if len(sys.argv) < 2:
    raise ValueError("Input file path not provided")

input_filepath = sys.argv[1]

extension_sp = sys.argv[2]
# Move the extension site-packages to the top of sys.path otherwise the wrong numpy version is imported
if extension_sp in sys.path:
    sys.path.remove(extension_sp)
sys.path.insert(0, extension_sp)


import onnxruntime as ort
import os
import cv2
import numpy as np

model_file_name = "model.onnx"

input_size = (1536, 1536)

model_dir = os.path.dirname(__file__)
model_path = os.path.join(model_dir, model_file_name)

providers = [
    ('CUDAExecutionProvider', {
        'device_id': 0,
        'arena_extend_strategy': 'kNextPowerOfTwo',    #'kNextPowerOfTwo',kSameAsRequested
        'gpu_mem_limit': 5 * 1024 * 1024 * 1024,
        'cudnn_conv_algo_search': 'EXHAUSTIVE',
        'cudnn_conv_use_max_workspace': 0,
    }),
    'CPUExecutionProvider',
]

# Only log errors
ort.set_default_logger_severity(3)
sess_options = ort.SessionOptions()
ort_session = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)

input_image = cv2.imread(input_filepath)
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
