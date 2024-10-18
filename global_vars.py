import os
import requests
from . import utils
#import time


def get_model_size_from_url(url):
    res = requests.get(url,stream=True)
    return int(res.headers['Content-length'])


CONST_SIZE = True

#start = time.time()


cache_dir = utils.get_cache_directory()
models = [
    ("model.pt","https://huggingface.co/Flare/dm/resolve/main/dm_epoch_110.pt?download=true"),
]
model_sizes = [
    1341420060,
    ]


MODELS_CACHED = True
for i in range(len(models)):
    model,url = models[i]
    
    model_path = os.path.join(cache_dir, model)
    model_exists = os.path.isfile(model_path)
    
    if not model_exists:
        MODELS_CACHED = False
        break
        
    model_size = model_sizes[i] if CONST_SIZE else get_model_size_from_url(url)
    model_is_whole = (os.stat(model_path).st_size == model_size)
    
    MODELS_CACHED = MODELS_CACHED and model_exists and model_is_whole
    if not MODELS_CACHED: break


model_mflops = 1338425.860968
#cpu_mflops = utils.get_cpu_mflops()
#duration_estimate = model_mflops / cpu_mflops

MODULES_INSTALLED = None

count = 0

#print(f"Globals time: {time.time()-start}")