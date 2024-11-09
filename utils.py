import os


def get_cpu_mflops():
    import psutil
    
    cpu_count = psutil.cpu_count(logical=False)
    cpu_freq = psutil.cpu_freq()
    cpu_mflops = cpu_count * cpu_freq.max * 4
    
    return cpu_mflops
