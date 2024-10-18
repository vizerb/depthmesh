#import time
#start = time.time()


import os


def get_cpu_mflops():
    import psutil
    
    cpu_count = psutil.cpu_count(logical=False)
    cpu_freq = psutil.cpu_freq()
    cpu_mflops = cpu_count * cpu_freq.max * 4
    
    return cpu_mflops


def are_modules_installed():
    import sys
    import subprocess
    import pkg_resources

    required = {"opencv-python-headless", "onnxruntime-gpu","psutil"}
    installed = {pkg.key for pkg in pkg_resources.working_set}
    #print(list(required - installed))
    
    return not (required - installed)

def ensure_modules():
    if are_modules_installed():
        return True
    else:
        modules = ["opencv-python-headless==4.10.0.82","onnxruntime-gpu","psutil"]
        return install_modules(modules)


def install_modules(modules):
    if (modules == []):
        return
    import sys
    import subprocess

    pyexe = sys.executable
    command = [pyexe,'-m','pip','install','--user'] + modules
    #command = [pyexe,"-m","pip","install","--target", target] + modules
    try:
        res = subprocess.check_call(command)
        return res==0
    except:
        raise Exception("Could not install necessary python modules")
    

def get_cache_directory():
    home_dir = os.path.expanduser("~")
    cache_dir = os.path.join(home_dir, ".depthmeshpro_cache")
    
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    return cache_dir


def create_triangles(h, w, mask=None):
    """
    Reference: https://github.com/google-research/google-research/blob/e96197de06613f1b027d20328e06d69829fa5a89/infinite_nature/render_utils.py#L68
    Creates mesh triangle indices from a given pixel grid size.
        This function is not and need not be differentiable as triangle indices are
        fixed.
    Args:
    h: (int) denoting the height of the image.
    w: (int) denoting the width of the image.
    Returns:
    triangles: 2D numpy array of indices (int) with shape (2(W-1)(H-1) x 3)
    """
    import numpy as np
    x, y = np.meshgrid(range(w - 1), range(h - 1))
    tl = y * w + x
    tr = y * w + x + 1
    bl = (y + 1) * w + x
    br = (y + 1) * w + x + 1
    triangles = np.array([tl, bl, tr, br, tr, bl])
    triangles = np.transpose(triangles, (1, 2, 0)).reshape(
        ((w - 1) * (h - 1) * 2, 3))
    if mask is not None:
        mask = mask.reshape(-1)
        triangles = triangles[mask[triangles].all(1)]
    return triangles


#print(f"Utils time: {time.time()-start}")
