# depthmesh 
<img src="https://public-files.gumroad.com/97pe3bb08dj5mf6yuptt6bloc6qt" alt="banner"/>

## Description

Depth Mesh Pro is a Blender add-on that creates a metrically accurate mesh from a single image.

Requires blender 4.2+
Blender 4.2.4 and 4.3.0 (current releases as of writing) have a bug that prevents the extension from installing correctly. To work around this issue you can use older or newer versions.

Supported on windows, linux and mac

## Examples

<img src="https://public-files.gumroad.com/b5dhuxll5s0h6x0xf78tp6hmtw4k" width="620"/> <img src="https://public-files.gumroad.com/ajh454am84t987qs3rq4r7lpgmct" alt="example2 result" width="620"/>

<img src="https://public-files.gumroad.com/kp7s762d8iwchabbb8f4ceizt4nm" alt="example3 original" width="620"/> <img src="https://public-files.gumroad.com/ml8b5tek3e7jcaw1a94bkoizuk23" alt="example3 result" width="620"/>

<img src="https://public-files.gumroad.com/ceojenxok35xza2sq4dhuikedzu9" width="620"/> <img src="https://public-files.gumroad.com/i4aybofq6nnh56hpg8o3emk457pt" alt="example1 result" width="620"/>

## Usage

1. Choose an image
2. Click the "Make depth mesh" button
3. Use the "Align the active camera" button to match the focal length and resolution of the image and move the camera to the world origin.

<img src="https://public-files.gumroad.com/afl8quc6y3hpsjzj2ai0wwwf3c8k" alt="usage1" width="620"/><br>


You can modify the mesh by changing the parameters in the geo nodes modifier:

<img src="https://public-files.gumroad.com/begmldzgnazahjsdhtfca9uxp4kn" alt="usage2" width="620"/>

## Versions:
* CUDA version for NVIDIA GPUs
* DirectML version for DirectX12 capable GPUs (windows only)
* CPU version

## Requirements:

* For GPU versions: 4GB VRAM
* For CPU version: 8GB RAM and a fairly modern 64bit CPU (e.g. Intel Core i5 8400 or AMD Ryzen 2600)
