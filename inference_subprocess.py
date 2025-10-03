import sys
import traceback

# Script to be called as subprocess from addon to run inference on linux
EXEC_PROVIDER = "CUDA"

def _send_result(obj, exit_code=0):
    try:
        pickle.dump(obj, sys.stdout.buffer, protocol=pickle.HIGHEST_PROTOCOL)
        sys.stdout.buffer.flush()
    except BrokenPipeError:
        # parent closed pipe; nothing to do
        pass
    except Exception:
        print("Failed to send result to parent", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    finally:
        # Ensure the subprocess exits with a non-zero code on error
        sys.exit(exit_code)


if len(sys.argv) < 2:
    raise ValueError("Input file path not provided")

input_filepath = sys.argv[1]

# Append the extensions modules to path
extension_sp = sys.argv[2]
sys.path.append(extension_sp)

try:
    from PIL import Image
    import pickle
    from inference import Inference
except ImportError as e:
    print(f"Failed to import required packages\n{e}")
    exit()

inference = Inference(EXEC_PROVIDER)
inference.loadModel()

try:
    input_image = Image.open(input_filepath)
except Exception as e:
    _send_result({
        "status": "error",
        "message": "Failed to open image",
        "type": e.__class__.__name__,
        "traceback": traceback.format_exc()
    }, exit_code=4)

try:
    depth, focallength_px = inference.infer(input_image)
    _send_result({
        "status": "ok",
        "depth": depth,
        "focal_length": focallength_px
    }, exit_code=0)
except Exception as e:
    _send_result({
        "status": "error",
        "message": "Inference failed",
        "type": e.__class__.__name__,
        "traceback": traceback.format_exc()
    }, exit_code=5)