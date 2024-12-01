import numpy as np
from . import global_vars

def preprocess_image(input_image, input_size):
    import cv2
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


class Inference():
    model = None
    ort_session = None
    
    
    def unloadModel(self):
        if hasattr(self, 'ort_session'):
            del self.ort_session
        if hasattr(self, 'ort_session'):
            del self.ort_session
    
    def loadModel(self):       
        import onnxruntime as ort
        import os
        
        model_file_name = "model.onnx"

        self.input_size = (1536, 1536)
        self.input_size = (1536, 1536)
        
        model_dir = os.path.dirname(__file__)
        model_path = os.path.join(model_dir, model_file_name)
        
        providers = []
        if global_vars.VERSION == "CUDA":
            providers += "CUDAExecutionProvider"
        elif global_vars.VERSION == "DIRECTML":
            providers += "DmlExecutionProvider"
            
        providers += "CPUExecutionProvider"
        
        
        # Only log errors
        ort.set_default_logger_severity(3)
        sess_options = ort.SessionOptions()
        self.ort_session = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)
        
    def infer(self, input_image):
        onnx_input = preprocess_image(input_image, self.input_size)
        input_name = self.ort_session.get_inputs()[0].name
        
        outputs = self.ort_session.run(None, {input_name: onnx_input})        

        depth = outputs[0].squeeze()  # Depth in [m].
        focallength_px = outputs[1][0][0]  # Focal length in pixels.
        
        return depth,focallength_px
