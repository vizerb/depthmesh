#from . import utils
#from . import global_vars
from typing import Tuple, Dict, List
import numpy as np
#from PIL import Image

def preprocess_image(input_image, input_size):
    import cv2
    image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
    
    image = cv2.resize(image, input_size)  # Resize to the model's expected input size
    print(image.shape)
    image = np.array(image).astype('float32')
    image = np.transpose(image, (2, 0, 1))  # Change data layout from HWC to CHW
    image = np.expand_dims(image, axis=0)  # Add batch dimension
    image /= 255.0  # Normalize to [0, 1]
    return image


class Inference():
    model = None
    
    #cache_dir = utils.get_cache_directory()
    
    def loadModel(self):
        import onnxruntime as ort
        import os
        
        model_file_name = "model.onnx"

        self.input_size = (1536, 1536)  # [H, W, C]        
        
        #self.device = "cuda" if torch.cuda.is_available() else "cpu"
        #model_file_name = global_vars.models[0][0]
        model_dir = os.path.dirname(__file__)
        #model_path = os.path.join(self.cache_dir, model_file_name)
        model_path = os.path.join(model_dir, model_file_name)
        
        providers = ["CPUExecutionProvider"]
        sess_options = ort.SessionOptions()
        self.ort_session = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)
        
    def infer(self, input_image):
        onnx_input = preprocess_image(input_image, self.input_size)
        input_name = self.ort_session.get_inputs()[0].name
        outputs = self.ort_session.run(None, {input_name: onnx_input})

        depth = outputs[0].squeeze()  # Depth in [m].
        focallength_px = outputs[1][0][0]  # Focal length in pixels.
        
        return depth


def run_inference(model_path, image_path):
    import cv2

    # Load the image
    input_image = cv2.imread(image_path)
    if input_image is None:
        raise ValueError(f"Image at path {image_path} could not be loaded.")

    # Create an instance of the Inference class and load the model
    inference = Inference()
    inference.loadModel()

    # Run inference
    depth = inference.infer(input_image)

    # Save the depth map to a file
    depth_map_path = image_path.replace(".jpg", "_depth.npy")
    np.save(depth_map_path, depth)

    print(f"Depth map saved to {depth_map_path}")

run_inference('model_fp16.onnx', "/home/flare/Pictures/ghostlyorseg.jpg")