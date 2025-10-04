def preprocess_image(input_image, input_size):
    import numpy as np
    
    image_mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    image_std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    
    image = input_image.convert("RGB")
    
    image = image.resize(input_size)  # Resize to the model's expected input size
    
    image = np.array(image, dtype=np.float32)[:,:,:3]
    image /= 255.0  # Normalize to [0, 1]
    image = (image - image_mean) / image_std

    image = np.transpose(image, (2, 0, 1))  # Change data layout from HWC to CHW
    image = np.expand_dims(image, axis=0)  # Add batch dimension

    return image


class Inference():
    model = None
    ort_session = None
    execution_provider = ""
    input_size = (1536, 1536)
    
    def __init__(self, execution_provider):
        self.execution_provider = execution_provider
    
    def unloadModel(self):
        if hasattr(self, 'ort_session'):
            del self.ort_session
    
    def loadModel(self):       
        import onnxruntime as ort
        import os
        
        model_file_name = "model.onnx"

        model_dir = os.path.dirname(__file__)
        model_path = os.path.join(model_dir, model_file_name)
        
        providers = ["CPUExecutionProvider"]
        if self.execution_provider == "CUDA":
            providers.insert(0,"CUDAExecutionProvider")
        elif self.execution_provider == "DIRECTML":
            providers.insert(0,"DmlExecutionProvider")        
        
        # Only log errors
        ort.set_default_logger_severity(3)
        sess_options = ort.SessionOptions()
        self.ort_session = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)
        
        
    def infer(self, input_image):
        try:
            onnx_input = preprocess_image(input_image, self.input_size)
            input_name = self.ort_session.get_inputs()[0].name
            outputs = self.ort_session.run(None, {input_name: onnx_input})
            depth = outputs[0].squeeze()  # Depth in [m].
            focallength_px = outputs[1][0][0]  # Focal length in pixels.
        except Exception as e:
            self.unloadModel()
            if ("Failed to allocate memory" in str(e)) or ("std::bad_alloc" in str(e)) or ("Not enough memory" in str(e)):
                raise MemoryError("Device ran out of memory while running inference")
            else:
                raise  # re-raise other errors
            
        return depth,focallength_px
