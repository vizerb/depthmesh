import bpy
import os
import threading
#import time

from . import future
from . import global_vars
from . import utils
from .inference import Inference

#start = time.time()


models = global_vars.models
inference = Inference()

class DMPPropertyGroup(bpy.types.PropertyGroup):
    inputPath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        name="Selected image",
        description="Path for input image",
        default=bpy.path.abspath(""),
        maxlen=1024,
    ) # type: ignore
    download_progress: bpy.props.FloatProperty(
        name="Progress",
        subtype="PERCENTAGE",
        default=0,
        soft_min=0, 
        soft_max=100, 
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
    
    cache_dir = utils.get_cache_directory()
    
    def draw(self, context):
        props = context.scene.DMPprops
        layout = self.layout
        
        if global_vars.MODULES_INSTALLED == None:
            global_vars.MODULES_INSTALLED = True#utils.are_modules_installed()
        
        
        dp_path = layout.row()
        dp_path.prop(props, "inputPath")
        layout.separator()
        dp_op = layout.row()
        op = dp_op.operator(DepthPredict.bl_idname, text="Make depth mesh", icon='FILE_3D')
        
        if (props.inference_progress > 0):
            layout.separator()
            progress_row = layout.row()
            if (bpy.app.version >= (4,0,0)):    
                progress_row.progress(factor = props.inference_progress/100, type = 'BAR', text = "Inference progress")
            else:
                progress_row.prop(props,"inference_progress")
        
        dp_path.enabled = global_vars.MODELS_CACHED and global_vars.MODULES_INSTALLED
        dp_op.enabled = global_vars.MODELS_CACHED and global_vars.MODULES_INSTALLED
        
        
        if (not global_vars.MODULES_INSTALLED):
            layout.operator("dmp.install_modules", text="Install necessary python modules", icon='TRIA_DOWN')
        else:    
            if (global_vars.MODELS_CACHED):
                layout.label(text="Model cached")
            else:
                download_model_row = layout.row()
                download_model_op = download_model_row.operator("dmp.download_model", text="Download model file", icon='TRIA_DOWN')
                download_model_op.download_list.clear()  # Clear existing items
                for name,url in models:
                    item = download_model_op.download_list.add()
                    item.url = url
                    item.path = os.path.join(self.cache_dir,name)
                if 0.0 < props.download_progress:
                    download_model_row.enabled = False
                    if (bpy.app.version >= (4,0,0)):
                        layout.progress(factor = props.download_progress/100, type = 'BAR', text = "Downloading")
                    else:
                        progress_bar = layout.row()
                        progress_bar.prop(props,"download_progress")
        
        



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
    
    # Appends the selected object from the extensions nodes.blend file
    def appendToScene(self, inner_path, object_name):
        model_dir = os.path.dirname(__file__)
        blend_file = os.path.join(model_dir, "nodes.blend")
        
        # This appends the geonodes group and also the material because the node group uses it
        bpy.ops.wm.append(
            filepath=os.path.join(blend_file,inner_path,object_name), #str(blend_file / inner_path / object_name),
            directory=os.path.join(blend_file,inner_path),#str(blend_file / inner_path),
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
        
        # # Get the appended material and copy it so that the original is available for the next usage
        # original_material = bpy.data.materials["DMPMaterial"]
        # original_material.use_fake_user = True  # Set fake user to keep the material in the file
        # material = original_material.copy()
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
        geo["Socket_7"] = int(self.focal_length)
        
        # DepthMap
        geo["Socket_14"] = depth_image
        # Width
        geo["Socket_15"] = image_size[0]
        # Height
        geo["Socket_16"] = image_size[1]
        # Material
        geo["Socket_17"] = material
        
    
    
    def invoke(self, context, event):
        wm = context.window_manager
        self.timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        
        return self.execute(context)
    
    
    def execute(self, context):
        props = context.scene.DMPprops
        
        # # First inference
        # if (global_vars.count == 0):
        #     #utils.ensure_modules()
        #     inference.loadModel()
        inference.loadModel()


        cpu_mflops = utils.get_cpu_mflops()
        self.duration_estimate = global_vars.model_mflops / cpu_mflops
        
        import cv2
        
        # Getting input property
        self.input_filepath = props.inputPath
        if (self.input_filepath == ""):
            raise Exception("You did not select an input image")
        self.input_filepath = bpy.path.abspath(self.input_filepath)
        # Loading image to numpy array
        self.input_image = cv2.imread(self.input_filepath)

        # Inference
        self.future_output = future.Future()
        def async_inference():
            try:
                output = inference.infer(self.input_image)
                self.future_output.add_response(output)
            except Exception as e:
                self.future_output.set_exception(e)
            finally:
                self.future_output.set_done()
        # Run the async task in a separate thread
        threading.Thread(target=async_inference).start()

        return {'RUNNING_MODAL'}


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
                    self.depth,self.focal_length = self.future_output.result()
                    #self.report({'INFO'}, f"Inference done")
                    self.makeMesh(context)
                    props.inference_progress = 0
                except Exception as e:
                    self.report({'ERROR'}, f"Inference failed: {e}")
                context.window_manager.event_timer_remove(self.timer)
                
                return {'FINISHED'}
            return {'PASS_THROUGH'}
        return {'PASS_THROUGH'}


    def makeMesh(self, context):
        import numpy as np
        
        original_width, original_height = self.input_image.shape[1],self.input_image.shape[0]
        out_width, out_height = int(self.depth.shape[1]), int(self.depth.shape[0])
        #aspect_ratio = original_width / original_height

        
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

        inference.unloadModel()

        global_vars.count += 1
        self.report({'INFO'}, "Depth mesh generation complete")
        

#print(f"depth_mesh_gen time: {time.time()-start}")