import bpy
import os
import threading

from . import future
from . import global_vars
from . import utils
from .inference import Inference

inference = Inference(global_vars.EXEC_PROVIDER)
running = False
focal_length_mm = 0
resolution = [0,0]

# Check for buggy blender releases
bad_blender_version = bpy.app.version in [(4,2,4),(4,3,0)]

class DMPPropertyGroup(bpy.types.PropertyGroup):
    inputPath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        name="Selected image",
        description="Path for input image",
        default=bpy.path.abspath(""),
        maxlen=1024,
    ) # type: ignore
    inference_progress: bpy.props.FloatProperty(
        name="Progress",
        subtype="PERCENTAGE",
        default=0,
        soft_min=0, 
        soft_max=100, 
    ) # type: ignore

class DMPPanel(bpy.types.Panel):
    bl_label = "Depth Mesh Pro"
    bl_idname = "OBJECT_PT_dmp"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Depth Mesh Pro"
        
    def draw(self, context):
        global running
        global focal_length_mm
        global resolution
        props = context.scene.DMPprops
        
        layout = self.layout
        
        # Bad blender version
        if bad_blender_version:
            layout.alert = True
            r = layout.row()
            r.label(text="Unsupported Blender version.")
            r2 = layout.row()
            r2.label(text="4.2.4 and 4.3.0 are not supported.")
            return
        
        
        # Input
        dp_path = layout.row()
        dp_path.prop(props, "inputPath")
        layout.separator()
        
        # Depth mesh generation
        dp_op = layout.row()
        dp_op.enabled = not running
        op = dp_op.operator(DepthPredict.bl_idname, text="Generate depth mesh", icon='FILE_3D')
        
        # Align camera operator
        cam_op_row = layout.row()
        cam_op_row.enabled = bool(not running and resolution != [0,0] and focal_length_mm != 0)
        op = cam_op_row.operator("dmp.align_cam", text="Align active camera", icon='VIEW_CAMERA')
        op.resolution = resolution
        op.focal_length = focal_length_mm
        
        # Progress bar
        if (props.inference_progress > 0):
            layout.separator()
            progress_row = layout.row()
            progress_row.progress(factor = props.inference_progress/100, type = 'BAR', text = "Generating...")


class DepthPredict(bpy.types.Operator):
    """Depth prediction and mesh generation"""      # Tooltip
    bl_idname = "dmp.depthpredict"                  # Unique identifier
    bl_label = "Predict depth for image"            # Display name
    bl_options = {'UNDO'}
    
    timer = None
    future_output = None
    input_filepath = None
    input_image = None
    depth = None
    focal_length = None
    time_elapsed = 0
    duration_estimate = 0
    
    def invoke(self, context, event):
        if not self.execute(context):
            return {'CANCELLED'}
        
        wm = context.window_manager
        self.timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    
    
    def execute(self, context):
        global running
        running = True
        props = context.scene.DMPprops
        
        # Inference init
        if (global_vars.count == 0 and global_vars.EXEC_PROVIDER=="CUDA"):
            utils.add_nvidia_dlls_to_path()
        
        if not (global_vars.EXEC_PROVIDER == "CUDA" and global_vars.OS == "LINUX"):
            inference.loadModel()

        mflops = utils.get_device_mflops(global_vars.EXEC_PROVIDER)
        self.duration_estimate = (global_vars.model_mflops / mflops)
        
        import numpy as np
        from PIL import Image
        
        # Getting input property
        self.input_filepath = props.inputPath
        if (self.input_filepath == ""):
            self.report({'ERROR'}, "You did not select an input image")
            self.finished(context)
            return False
        self.input_filepath = bpy.path.abspath(self.input_filepath)
        
        if not os.path.isfile(self.input_filepath):
            self.report({'ERROR'}, "Selected file does not exist")
            self.finished(context)
            return False
        
        # Loading image
        self.input_image = Image.open(self.input_filepath)

        # Failed to load image
        if self.input_image is None:
            self.report({'ERROR'}, "Failed to load image")
            self.finished(context)
            return False
        global resolution
        resolution = [self.input_image.size[0], self.input_image.size[1]]

        # Inference
        self.future_output = future.Future()
        # Run the async task in a separate thread
        threading.Thread(target=self.async_inference).start()
        
        return True
    
    
    def async_inference(self):
        try:
            if not (global_vars.OS == "LINUX" and global_vars.EXEC_PROVIDER == "CUDA"):
                output = inference.infer(self.input_image)
            else:
                # Special case: On linux updating LD_LIBRARY_PATH 
                # doesnt take effect if a process is already running
                # so a subprocess is used to run inference
                import os
                import sys
                import subprocess
                
                dir = os.path.dirname(__file__)
                script_path = os.path.join(dir, "inference_subprocess.py")
                
                # Pass the extensions site-packages to the subprocess
                extensions = bpy.utils.user_resource('EXTENSIONS')
                local_dir = os.path.join(extensions, ".local")
                extension_sp = os.path.join(local_dir, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
                args = [sys.executable, script_path, self.input_filepath, extension_sp]
                
                output = subprocess.run(args, capture_output=True)
            
            self.future_output.add_response(output)
        except Exception as e:
            self.future_output.set_exception(e)
        finally:
            self.future_output.set_done()
            
    
    def finished(self, context):
        global running
        running = False
        if self.timer is not None:
            context.window_manager.event_timer_remove(self.timer)

    
    def makeMesh(self, context):
        import numpy as np
        
        original_width, original_height = self.input_image.size[0],self.input_image.size[1]
        out_width, out_height = int(self.depth.shape[1]), int(self.depth.shape[0])
        
        # Add plane
        bpy.ops.mesh.primitive_plane_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
        obj = bpy.context.object
        obj.name = "DMPObject"
        # Save depth as image inside blender
        depth_name = obj.name + "_depth"
        depth_image = bpy.data.images.new(depth_name, width=out_width, height=out_height, float_buffer=True)
        depth_image.alpha_mode = 'NONE'
        # Flatten the numpy array and assign it to the image pixels
        mirrored_pred = self.depth[::-1, :]
        rgba_data = np.stack([mirrored_pred]*4, axis=-1)
        depth_image.pixels = rgba_data.flatten()
        depth_image.pack()
        
        self.applyGeoAndMaterial(obj, depth_image, (original_width, original_height))

        if not (global_vars.EXEC_PROVIDER == "CUDA" and global_vars.OS == "LINUX"):
            inference.unloadModel()
        
        self.cleanup()

        global_vars.count += 1
        self.report({'INFO'}, "Depth mesh generated")
    
    
    # Appends object from the included nodes.blend file
    def appendToScene(self, inner_path, object_name):
        model_dir = os.path.dirname(__file__)
        blend_file = os.path.join(model_dir, "nodes.blend")
        
        # This appends the geonodes group and also the material because the node group uses it
        bpy.ops.wm.append(
            filepath=os.path.join(blend_file,inner_path,object_name),
            directory=os.path.join(blend_file,inner_path),
            filename=object_name
        )
    
    
    def applyGeoAndMaterial(self, obj, depth_image, image_size):
        node_tree = bpy.data.node_groups.get("DMPprojectmesh")
        if not node_tree:
            self.appendToScene("NodeTree", "DMPprojectmesh")
            node_tree = bpy.data.node_groups.get("DMPprojectmesh")
            if not node_tree:
                raise Exception("Couldn't append the geonodes tree from nodes.blend")

        
        material = bpy.data.materials.get("DMPMaterial")
        if not material:
            self.appendToScene("Material", "DMPMaterial")
            material = bpy.data.materials.get("DMPMaterial")
            if not material:
                raise Exception("Couldn't append the material from nodes.blend")
        
        # Load the image texture
        texture_image = bpy.data.images.load(self.input_filepath)
        
        # Rename it so it doesn't collide with the next one
        filename = os.path.basename(self.input_filepath).split(".")[0]
        material.name = filename

        # Create an image texture node
        tex_image = material.node_tree.nodes.get('Image Texture')
        tex_image.image = texture_image
        # Assign the material to the object for the user to easily access it later (geo nodes assignment is where it actually gets assigned)
        obj.data.materials.append(material)        
        
        geo = obj.modifiers.new(name="GeometryNodes", type='NODES')
        geo.node_group = node_tree
        
        # The focal length input socket
        geo["Socket_7"] = float(self.focal_length)
        
        # DepthMap
        geo["Socket_14"] = depth_image
        # Width
        geo["Socket_15"] = image_size[0]
        # Height
        geo["Socket_16"] = image_size[1]
        # Material
        geo["Socket_17"] = material
        
    
    def modal(self, context, event):
        if event.type == 'TIMER':
            self.time_elapsed += 0.05
            props = context.scene.DMPprops
            props.inference_progress = min(85, (self.time_elapsed / self.duration_estimate)*100)
            
            # Update UI
            wm = context.window_manager
            for w in wm.windows:
                for area in w.screen.areas:
                    area.tag_redraw()

            if self.future_output.done:
                try:
                    props = context.scene.DMPprops
                    props.inference_progress = 100
                    if (global_vars.OS == "LINUX" and global_vars.EXEC_PROVIDER == "CUDA"):
                        import pickle
                        out_dict = pickle.loads(self.future_output.result().stdout)
                        self.depth,self.focal_length = out_dict["depth"],out_dict["focal_length"]
                    else:
                        self.depth,self.focal_length = self.future_output.result()
                    
                    # Convert self.focal_length to mm and set global focal_length to be used by addcamera operator
                    global focal_length_mm
                    sensor_width_mm = 36.0
                    focal_length_px = self.focal_length
                    self.focal_length = (focal_length_px / 1536) * sensor_width_mm
                    focal_length_mm = self.focal_length
                    
                    self.makeMesh(context)
                    
                    props.inference_progress = 0
                except Exception as e:
                    self.report({'ERROR'}, f"Inference failed: {e}")
                    
                self.finished(context)
                return {'FINISHED'}
                
        return {'PASS_THROUGH'}
            

    def cleanup(self):
        # Release resources and clean up variables
        if self.future_output is not None:
            del self.future_output
            self.future_output = None
        
        if self.input_filepath is not None:
            del self.input_filepath
            self.input_filepath = None
        
        if self.input_image is not None:
            del self.input_image
            self.input_image = None
        
        if self.depth is not None:
            del self.depth
            self.depth = None
        
        if self.focal_length is not None:
            del self.focal_length
            self.focal_length = None