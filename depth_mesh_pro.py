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
        )
    download_progress: bpy.props.FloatProperty(
        name="Progress",
        subtype="PERCENTAGE",
        default=0,
        soft_min=0, 
        soft_max=100, 
    )
    inference_progress: bpy.props.FloatProperty(
        name="Progress",
        subtype="PERCENTAGE",
        default=0,
        soft_min=0, 
        soft_max=100, 
    )


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
            global_vars.MODULES_INSTALLED = utils.are_modules_installed()
        
        
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
    future_depth = None
    input_filepath = None
    input_image = None
    depth = None
    
    time_elapsed = 0
    
    duration_estimate = 0
    
    def geoNodesSetup(self, obj, depth_image, aspect_ratio):
        import numpy as np
        
        geo = obj.modifiers.new("",type='NODES')
        bpy.ops.node.new_geometry_node_group_assign()

        # Getting nodes
        input_node = geo.node_group.nodes.get("Group Input")
        subdiv_node = geo.node_group.nodes.new("GeometryNodeSubdivideMesh")
        setpos_node = geo.node_group.nodes.new("GeometryNodeSetPosition")
        uvmap_node = geo.node_group.nodes.new("GeometryNodeInputNamedAttribute")
        uvsubtract_node = geo.node_group.nodes.new("ShaderNodeVectorMath")
        uvmul_node = geo.node_group.nodes.new("ShaderNodeVectorMath")
        uvadd_node = geo.node_group.nodes.new("ShaderNodeVectorMath")
        imgtex_node = geo.node_group.nodes.new("GeometryNodeImageTexture")
        pos_node = geo.node_group.nodes.new("GeometryNodeInputPosition")
        sep_node = geo.node_group.nodes.new("ShaderNodeSeparateXYZ")
        div_focal_node = geo.node_group.nodes.new("ShaderNodeMath")
        div_xf_node = geo.node_group.nodes.new("ShaderNodeMath")
        div_yf_node = geo.node_group.nodes.new("ShaderNodeMath")
        mul_xz_node = geo.node_group.nodes.new("ShaderNodeMath")
        mul_yz_node = geo.node_group.nodes.new("ShaderNodeMath")
        negate_z_node = geo.node_group.nodes.new("ShaderNodeMath")
        com_node = geo.node_group.nodes.new("ShaderNodeCombineXYZ")
        transform_node = geo.node_group.nodes.new("GeometryNodeTransform")
        output_node = geo.node_group.nodes.get("Group Output")
        
        
        # Setting node values
        imgtex_node.inputs[0].default_value = depth_image
        
        uvmap_node.data_type = 'FLOAT_VECTOR'
        uvmap_node.inputs["Name"].default_value = "UVMap"

        # Fix for edge depth values not being correct
        uvsubtract_node.operation = 'SUBTRACT'
        uvmul_node.operation = 'MULTIPLY'
        uvadd_node.operation = 'ADD'
        uvsubtract_node.inputs[1].default_value = (0.5,0.5,0)
        uvmul_node.inputs[1].default_value = (0.998,0.998,0)
        uvadd_node.inputs[1].default_value = (0.5,0.5,0)
        
        div_focal_node.operation = 'DIVIDE'
        div_focal_node.inputs[1].default_value = 18.0
        div_xf_node.operation = 'DIVIDE'
        div_yf_node.operation = 'DIVIDE'
        mul_xz_node.operation = 'MULTIPLY'
        mul_yz_node.operation = 'MULTIPLY'
        negate_z_node.operation = 'MULTIPLY'
        negate_z_node.inputs[1].default_value = -1.0
        transform_node.inputs[2].default_value[0] = 90/180*np.pi
        transform_node.inputs[3].default_value[1] = 1.0/aspect_ratio

        
        # Creating group inputs
        if (bpy.app.version >= (4,0,0)):
            geo.node_group.interface.new_socket(name="Focal length", in_out='INPUT',socket_type="NodeSocketFloat")
            id = geo.node_group.interface.items_tree["Focal length"].identifier
            geo[id] = 30.0
            geo.node_group.interface.new_socket(name="Resolution", in_out='INPUT',socket_type="NodeSocketInt")
            id = geo.node_group.interface.items_tree["Resolution"].identifier
            geo[id] = 8
        else:
            geo.node_group.inputs.new("NodeSocketFloat","Focal length")
            geo["Input_2"] = 30.0
            geo.node_group.inputs.new("NodeSocketInt","Resolution")
            geo["Input_3"] = 8
        
        
        # Node links
        geo.node_group.links.new(input_node.outputs["Geometry"],subdiv_node.inputs['Mesh'])
        geo.node_group.links.new(input_node.outputs["Resolution"],subdiv_node.inputs['Level'])
        geo.node_group.links.new(input_node.outputs["Focal length"],div_focal_node.inputs[0])
        
        geo.node_group.links.new(uvmap_node.outputs[0],uvsubtract_node.inputs[0])
        geo.node_group.links.new(uvsubtract_node.outputs[0],uvmul_node.inputs[0])
        geo.node_group.links.new(uvmul_node.outputs[0],uvadd_node.inputs[0])
        geo.node_group.links.new(uvadd_node.outputs[0],imgtex_node.inputs['Vector'])
        
        geo.node_group.links.new(pos_node.outputs[0],sep_node.inputs[0])
        
        geo.node_group.links.new(sep_node.outputs[0],div_xf_node.inputs[0])
        geo.node_group.links.new(div_focal_node.outputs[0],div_xf_node.inputs[1])
        geo.node_group.links.new(sep_node.outputs[1],div_yf_node.inputs[0])
        geo.node_group.links.new(div_focal_node.outputs[0],div_yf_node.inputs[1])
        
        geo.node_group.links.new(div_xf_node.outputs[0],mul_xz_node.inputs[0])
        geo.node_group.links.new(imgtex_node.outputs[0],mul_xz_node.inputs[1])
        geo.node_group.links.new(div_yf_node.outputs[0],mul_yz_node.inputs[0])
        geo.node_group.links.new(imgtex_node.outputs[0],mul_yz_node.inputs[1])
        
        geo.node_group.links.new(imgtex_node.outputs[0], negate_z_node.inputs[0])
        
        geo.node_group.links.new(mul_xz_node.outputs[0], com_node.inputs[0])
        geo.node_group.links.new(mul_yz_node.outputs[0], com_node.inputs[1])
        geo.node_group.links.new(negate_z_node.outputs[0], com_node.inputs[2])
        
        geo.node_group.links.new(subdiv_node.outputs["Mesh"],setpos_node.inputs['Geometry'])
        geo.node_group.links.new(com_node.outputs[0], setpos_node.inputs["Position"])
        
        geo.node_group.links.new(setpos_node.outputs['Geometry'], transform_node.inputs['Geometry'])
        
        geo.node_group.links.new(transform_node.outputs['Geometry'],output_node.inputs['Geometry'])
    
    
    def invoke(self, context, event):
        wm = context.window_manager
        self.timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        
        return self.execute(context)
    
    
    def execute(self, context):
        props = context.scene.DMPprops
        
        # First inference
        if (global_vars.count == 0):
            utils.ensure_modules()
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
        self.future_depth = future.Future()
        def async_inference():
            try:
                depth = inference.infer(self.input_image)
                self.future_depth.add_response(depth)
            except Exception as e:
                self.future_depth.set_exception(e)
            finally:
                self.future_depth.set_done()
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
                    
            if self.future_depth.done:
                try:
                    props = context.scene.DMPprops
                    props.inference_progress = 100
                    self.depth = self.future_depth.result()
                    self.report({'INFO'}, f"Inference done")
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
        aspect_ratio = original_width / original_height

        
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
        
        
        # Geo nodes setup
        self.geoNodesSetup(obj, depth_image, aspect_ratio)
        

        # Load the texture image
        texture_image = bpy.data.images.load(self.input_filepath)
        # Create a new material
        material = bpy.data.materials.new(name="Material")
        material.use_nodes = True
        bsdf = material.node_tree.nodes["Principled BSDF"]
        # Create an image texture node
        tex_image = material.node_tree.nodes.new('ShaderNodeTexImage')
        tex_image.image = texture_image
        # Connect the image texture node to the base color of the Principled BSDF
        material.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
        bsdf.inputs["Roughness"].default_value = 0.95
        # Assign the material to the object
        obj.data.materials.append(material)

        global_vars.count += 1
        self.report({'INFO'}, "Depth mesh generation complete")
        

#print(f"depth_mesh_gen time: {time.time()-start}")