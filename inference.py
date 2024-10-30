from . import utils
from . import global_vars
from typing import Tuple, Dict, List
import numpy as np
#from PIL import Image

def preprocess_image(input_image, input_size):
    import cv2
    image_mean=[0.5, 0.5, 0.5]
    image_std=[0.5, 0.5, 0.5]
    
    image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
    
    image = cv2.resize(image, input_size)  # Resize to the model's expected input size
    print(image.shape)
    image = np.array(image).astype('float32')
    image /= 255.0  # Normalize to [0, 1]
    image = (image - image_mean) / image_std

    image = np.transpose(image, (2, 0, 1))  # Change data layout from HWC to CHW
    image = np.expand_dims(image, axis=0)  # Add batch dimension

    image = np.array(image).astype('float32')

    return image


class Inference():
    model = None
    
    cache_dir = utils.get_cache_directory()
    
    def loadModel(self):
        import onnxruntime as ort
        import os
        
        model_file_name = "model.onnx"

        self.input_size = (1536, 1536)  # [H, W]
        
        #self.device = "cuda" if torch.cuda.is_available() else "cpu"
        #model_file_name = global_vars.models[0][0]
        model_dir = os.path.dirname(__file__)
        #model_path = os.path.join(self.cache_dir, model_file_name)
        model_path = os.path.join(model_dir, model_file_name)
        
        providers = ["CUDAExecutionProvider"]
        sess_options = ort.SessionOptions()
        self.ort_session = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)
        print("Model loaded")
        #self.ort_session = ort.InferenceSession(model_path)
        
    def infer(self, input_image):
        onnx_input = preprocess_image(input_image, self.input_size)
        input_name = self.ort_session.get_inputs()[0].name
        print("input_name: ", input_name)
        outputs = self.ort_session.run(None, {input_name: onnx_input})        

        depth = outputs[0].squeeze()  # Depth in [m].
        focallength_px = outputs[1][0][0]  # Focal length in pixels.
        
        return depth,focallength_px
