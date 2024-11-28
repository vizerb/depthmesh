import gpu

vendors = {
    "AMD": "ATI_AMD.csv",
    "NVIDIA": "NVIDIA.csv",
    "INTEL": "INTEL.csv",
}

def get_cpu_mflops():
    import psutil
    
    cpu_count = psutil.cpu_count(logical=False)
    cpu_freq = psutil.cpu_freq()
    cpu_mflops = cpu_count * cpu_freq.max * 4
    
    return cpu_mflops


def get_gpu_mflops():
    import pandas as pd
    import os
    gpu_name_full = gpu.platform.renderer_get()
    vendor = gpu_name_full.split(" ")[0] # example: NVIDIA
    gpu_name = gpu_name_full.split("/")[0].split(" ")[1:] # example: GeForce RTX 3060 Ti
    
    delim = " "
    gpu_name = delim.join(gpu_name)
    
    file_dir = os.path.dirname(__file__)
    file_name = vendors[vendor]
    
    df = pd.read_csv(os.path.join(file_dir,file_name))
    
    # Filter rows by the value of their first column
    filtered_df = df[df.iloc[:, 0] == gpu_name]
    if not filtered_df.empty:
        print(filtered_df.iloc[0, 9])
        return int(filtered_df.iloc[0, 9])
    else:
        print("No matching rows found.")
        return 1000000


def load_shared_libraries_from_folder(folder_path):
    """
    Loads all .so files from the specified folder using ctypes.cdll.LoadLibrary.
    """
    import os
    from ctypes import cdll
    
    if not os.path.isdir(folder_path):
        raise ValueError(f"{folder_path} is not a valid directory.")
    
    loaded_libraries = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".so"):
            full_path = os.path.join(folder_path, file_name)
            try:
                print(f"Loading library: {full_path}")
                library = cdll.LoadLibrary(full_path)
                loaded_libraries.append(library)
            except OSError as e:
                print(f"Failed to load {full_path}: {e}")
    
    return loaded_libraries