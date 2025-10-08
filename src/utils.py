from . import global_vars

vendors = {
    "AMD": "ATI_AMD.csv",
    "NVIDIA": "NVIDIA.csv",
    "INTEL": "INTEL.csv",
}

def get_available_cpu_memory_gb():
    """
    Uses psutil to query available system memory in GB
    """
    import psutil
    mem = psutil.virtual_memory()
    return mem.available / (1024 ** 3)  # in GB

def get_cpu_mflops():
    import psutil
    
    cpu_count = psutil.cpu_count(logical=False)
    cpu_freq = psutil.cpu_freq() # max can be 0 if it cant be determined
    cpu_mflops = cpu_count * max(cpu_freq.max, cpu_freq.current) * 4
    
    return cpu_mflops


def get_gpu_mflops():
    """
    Tries to get the megaflops a gpu is capable of.
    In case of failure it will return a predefined number.
    """
    import gpu
    import os
    import csv
    
    try:
        gpu_name_full = gpu.platform.renderer_get()  # e.g. str:NVIDIA GeForce RTX 3060 Ti/PCIe/SSE2
        vendor = gpu_name_full.split(" ")[0]  # e.g. str:NVIDIA
        gpu_name = gpu_name_full.split("/")[0].split(" ")[1:]  # e.g. List:[GeForce,RTX,3060,Ti]
        
        delim = ""
        gpu_name = delim.join(gpu_name).lower().replace(" ", "")  # e.g. geforcertx3060ti
        
        file_dir = os.path.join(os.path.dirname(__file__),"gpudata")
        file_name = vendors[vendor]
        
        with open(os.path.join(file_dir, file_name), mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                row_name = row[0].lower().replace(" ", "")
                if row_name == gpu_name:
                    return int(row[9])

        return 10000000
    except:
        return 10000000


def get_device_mflops(exec_provider):
    if exec_provider == "CPU":
        mflops = get_cpu_mflops() / 2
    elif exec_provider == "DIRECTML":
        mflops = get_gpu_mflops() / 8
    elif exec_provider == "CUDA":
        mflops = get_gpu_mflops() / 8
    else:
        raise Exception("Unsupported exec provider value")
    
    return mflops


def add_nvidia_dlls_to_path():
    import os
    import importlib
    import nvidia
    
    nvidia_dir = os.listdir(nvidia.__path__[0])
    for folder in nvidia_dir:
        if (folder.startswith("__")):
            continue
        module = importlib.import_module(f"nvidia.{folder}")
        
        if global_vars.OS == "WIN32":
            os.add_dll_directory(os.path.join(module.__path__[0],"bin"))
            os.environ["PATH"] = os.path.join(module.__path__[0], "bin") + os.pathsep + os.environ["PATH"]
        elif global_vars.OS == "LINUX":
            os.environ["LD_LIBRARY_PATH"] = os.path.join(module.__path__[0], "lib") + os.pathsep + os.environ.get("LD_LIBRARY_PATH","")
