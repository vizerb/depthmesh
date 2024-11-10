import bpy
import math

class AlignCameraOperator(bpy.types.Operator):
    """Sets the focal length position and rotation of the active camera to match the image"""
    bl_idname = "dmp.align_cam"
    bl_label = "Align the active camera"
    bl_options = {'UNDO'}

    focal_length: bpy.props.FloatProperty(
        name="Focal Length",
        description="Focal length for the camera",
        default=50.0,
        min=1.0,
        max=500.0
    ) # type: ignore
    resolution: bpy.props.IntVectorProperty(
        name="Resolution",
        description="Resolution for the scene",
        default=(1920, 1080),
        size=2,
        min=1,
        max=10000
    ) # type: ignore

    def execute(self, context):
        # Set the resolution
        context.scene.render.resolution_x = self.resolution[0]
        context.scene.render.resolution_y = self.resolution[1]
        
        # # Check if there is an active object and if it is a camera
        # if context.object and context.object.type == 'CAMERA':
        #     camera = context.object
        
        # Check if there is an active camera
        if context.scene.camera is not None:
            camera = context.scene.camera
        else:
            # Add a new camera
            bpy.ops.object.camera_add()
            camera = context.object
            # Set the new camera as the active camera
            context.scene.camera = camera
        
        # Set the camera's rotation
        camera.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        camera.location = (0,0,0)

        # Set the focal length
        camera.data.lens = self.focal_length

        # Set sensor fit mode
        camera.data.sensor_fit = 'HORIZONTAL'
        
        self.report({'INFO'}, "Camera aligned")
        return {'FINISHED'}