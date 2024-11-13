import bpy

bl_info = {
    "name": "Depth Mesh Pro",
    "blender": (4, 2, 0),
    "category": "Import-Export",
    "author": "Flare",
	"description": "Generates a mesh from an image using monocular metric depth estimation",
    "version": (1, 0, 0),
}

from . import depth_mesh_pro, align_camera_op

classes = (
    depth_mesh_pro.DMPPropertyGroup,
	depth_mesh_pro.DMPPanel,
    depth_mesh_pro.DepthPredict,
    align_camera_op.AlignCameraOperator,
)



def register():   
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
