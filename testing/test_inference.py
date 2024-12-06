import numpy as np
import os
import sys
#from PIL import Image

def progress_bar(count, total, status=''):
    bar_length = 40
    filled_length = int(bar_length * count / total)
    percent = round(100.0 * count / total, 1)
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f'\r[{bar}] {percent}% {status}')
    sys.stdout.flush()

def download_file(url, destination):
    import urllib.request

    if os.path.exists(destination):
        print(f"File {destination} already exists, skipping download.")
        return

    try:
        response = urllib.request.urlopen(url)
        total_size = int(response.headers['Content-Length'])
        downloaded_size = 0
        block_size = 8192
        with open(destination, 'wb') as f:
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                downloaded_size += len(buffer)
                f.write(buffer)
                progress_bar(downloaded_size, total_size, status='Downloading')
        print(f"\nDownloaded file from {url} to {destination}.")
    except Exception as e:
        print(f"Error downloading file from {url}: {str(e)}")



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
    
    def loadModel(self):
        import onnxruntime as ort    
        import os
        
        model_file_name = "model_q4f16.onnx"

        self.input_size = (1536, 1536)  # [H, W, C]        
        
        #self.device = "cuda" if torch.cuda.is_available() else "cpu"
        #model_file_name = global_vars.models[0][0]
        model_dir = os.path.dirname(__file__)
        #model_path = os.path.join(self.cache_dir, model_file_name)
        model_path = os.path.join(model_dir, model_file_name)
        
        providers = [
            "CPUExecutionProvider",
            ]
        sess_options = ort.SessionOptions()
        self.ort_session = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)
        print("Execution Providers:", self.ort_session.get_providers())
        
    def infer(self, input_image):
        onnx_input = preprocess_image(input_image, self.input_size)
        input_name = self.ort_session.get_inputs()[0].name
        outputs = self.ort_session.run(None, {input_name: onnx_input})

        depth = outputs[0].squeeze()  # Depth in [m].
        focallength_px = outputs[1][0][0]  # Focal length in pixels.
        
        return depth


def run_inference(image_path):
    from PIL import Image

    # Load the image
    input_image = Image.open(image_path)
    if input_image is None:
        raise ValueError(f"Image at path {image_path} could not be loaded.")

    # Create an instance of the Inference class and load the model
    inference = Inference()
    inference.loadModel()

    # Run inference
    depth = inference.infer(input_image)

    print(depth)
    # Save the depth map to a file
    #depth_map_path = image_path.replace(".jpg", "_depth.npy")
    #np.save(depth_map_path, depth)

    #print(f"Depth map saved to {depth_map_path}")


download_file("https://huggingface.co/onnx-community/DepthPro-ONNX/resolve/main/onnx/model_q4f16.onnx?download=true", "model_q4f16.onnx")

run_inference("test_img.jpg")
