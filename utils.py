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
    gpu_name_full = gpu.platform.renderer_get() # e.g. str:NVIDIA GeForce RTX 3060 Ti/PCIe/SSE2
    vendor = gpu_name_full.split(" ")[0] # e.g. str:NVIDIA
    gpu_name = gpu_name_full.split("/")[0].split(" ")[1:] # e.g. List:[GeForce,RTX,3060,Ti]
    
    delim = ""
    gpu_name = delim.join(gpu_name) # e.g. GeForceRTX3060Ti
    
    file_dir = os.path.dirname(__file__)
    file_name = vendors[vendor]
    
    df = pd.read_csv(os.path.join(file_dir,file_name))
    
    # Filter rows by the value of their first column also convert to lower case and remove spaces
    filtered_df = df[df.apply(lambda x: x.astype(str).str.lower().str.replace(" ","") == gpu_name.lower()).any(axis=1)]
    print(filtered_df)
    #filtered_df = df[df.iloc[:, 0] == gpu_name]
    if not filtered_df.empty:
        return int(filtered_df.iloc[0, 9])
    else:
        #print("No matching rows found.")
        return 1000000