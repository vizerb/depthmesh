import bpy
import sys

bl_info = {
    "name": "Depth Mesh Pro",
    "blender": (4, 0, 0),
    "category": "Import-Export",
    "author": "Flare",
	"description": "Generates a mesh from an image using monocular depth estimation",
    "version": (1, 0, 0),
}

from . import depth_mesh_pro, download_operator, install_modules_operator

classes = (
    download_operator.DownloadPropertyGroup,
    download_operator.DownloadFileOperator,
    install_modules_operator.InstallModulesOperator,
    depth_mesh_pro.DMPPropertyGroup,
	depth_mesh_pro.DMPPanel,
    depth_mesh_pro.DepthPredict,
)



def register():
    #import site
    #sys.path.append(site.getusersitepackages())
    
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.DMPprops = bpy.props.PointerProperty(
        type=depth_mesh_pro.DMPPropertyGroup
        )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.DMPprops
    

if __name__ == "__main__":
    register()
