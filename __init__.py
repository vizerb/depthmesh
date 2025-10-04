import bpy

bl_info = {
    "name": "Depth Mesh Pro",
    "blender": (4, 2, 0),
    "category": "Import-Export",
    "author": "Flare",
	"description": "Generates a mesh from an image using monocular metric depth estimation",
}

from . import depth_mesh_pro, align_camera_op

classes = (
    depth_mesh_pro.DMPPropertyGroup,
	depth_mesh_pro.DMPPanel,
    depth_mesh_pro.DepthPredict,
    align_camera_op.AlignCameraOperator,
)

def _cleanup_props():
    # Safely remove the pointer property if it exists
    if hasattr(bpy.types.Scene, "DMPprops"):
        try:
            del bpy.types.Scene.DMPprops
        except Exception:
            try:
                delattr(bpy.types.Scene, "DMPprops")
            except Exception:
                pass

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Only add the PointerProperty if it doesn't already exist
    if not hasattr(bpy.types.Scene, "DMPprops"):
        bpy.types.Scene.DMPprops = bpy.props.PointerProperty(
            type=depth_mesh_pro.DMPPropertyGroup
        )

def unregister():
    # Unregister classes in reverse order, ignore errors if already unregistered
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

    # Remove addon-level properties/state
    _cleanup_props()

if __name__ == "__main__":
    register()