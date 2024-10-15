from . import utils
from . import global_vars
from typing import Tuple, Dict, List
import numpy as np

def prepare_input(
    rgb_image: np.ndarray, input_size: Tuple[int, int]
) -> Tuple[Dict[str, np.ndarray], List[int]]:
    import cv2
    
    h, w = rgb_image.shape[:2]
    scale = min(input_size[0] / h, input_size[1] / w)
    # rgb = cv2.resize(
        # rgb_image, (input_size[1], input_size[0]), interpolation=cv2.INTER_LINEAR
    # )
    rgb = cv2.resize(
        rgb_image, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_LINEAR
    )


    padding_color = [123.675, 116.28, 103.53]
    h, w = rgb.shape[:2]
    pad_h = input_size[0] - h
    pad_w = input_size[1] - w
    pad_h_half = pad_h // 2
    pad_w_half = pad_w // 2
    rgb: np.ndarray = cv2.copyMakeBorder(
        rgb,
        pad_h_half,
        pad_h - pad_h_half,
        pad_w_half,
        pad_w - pad_w_half,
        cv2.BORDER_CONSTANT,
        value=padding_color,
    )
    pad_info = [pad_h_half, pad_h - pad_h_half, pad_w_half, pad_w - pad_w_half]
    #pad_info = [0, 0, 0, 0]

    #cv2.imshow("rgb", rgb)
    #cv2.waitKey(0)

    onnx_input = {
        "pixel_values": np.ascontiguousarray(
            np.transpose(rgb, (2, 0, 1))[None], dtype=np.float32
        ),  # 1, 3, H, W
    }
    return onnx_input, pad_info


class Inference():
    model_configs = {
        'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
        'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
        'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
        'vitg': {'encoder': 'vitg', 'features': 384, 'out_channels': [1536, 1536, 1536, 1536]}
    }
    encoder = 'vitl'
    model_config = model_configs[encoder]
    device = "cpu"
    model = None
    
    cache_dir = utils.get_cache_directory()
    
    def loadModel(self):
        import onnxruntime as ort
        import os
        
        model_file_name = "metric3d_vit_large.onnx"
        
        if "vit" in model_file_name:
            self.input_size = (616, 1064)  # [H, W]
        else:
            self.input_size = (544, 1216)  # [H, W]
        
        #self.device = "cuda" if torch.cuda.is_available() else "cpu"
        #model_file_name = global_vars.models[0][0]
        model_dir = os.path.dirname(__file__)
        #model_path = os.path.join(self.cache_dir, model_file_name)
        model_path = os.path.join(model_dir, model_file_name)
        
        providers = ["CUDAExecutionProvider"]
        sess_options = ort.SessionOptions()
        self.ort_session = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)
        
        #self.ort_session = ort.InferenceSession(model_path)
        
    def infer(self, input_image):
        onnx_input, pad_info = prepare_input(input_image, self.input_size)
        outputs = self.ort_session.run(None, onnx_input)
        depth = outputs[0].squeeze()  # [H, W]

        # Reshape the depth to the original size
        depth = depth[
            pad_info[0] : self.input_size[0] - pad_info[1],
            pad_info[2] : self.input_size[1] - pad_info[3],
        ]
            
        return depth
