import subprocess
import sys

def test_opencv_import():
    import cv2
    print(cv2.__version__)
    try:
        result = subprocess.run(
            [sys.executable, r"C:\dev\projects\depthmesh\testing\test_opencv_import.py"], #[sys.executable, '-c', 'import cv2; print("OpenCV imported successfully")'],
            capture_output=True,
            text=True
        )
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_opencv_import()