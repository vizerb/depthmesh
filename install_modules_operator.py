import bpy
from . import global_vars
from . import utils

class InstallModulesOperator(bpy.types.Operator):
    """Download and install python modules"""
    bl_idname = "dmp.install_modules"
    bl_label = "Install modules"

    def execute(self, context):
        bpy.context.window.cursor_set('WAIT')
        success = utils.ensure_modules()
        bpy.context.window.cursor_set('DEFAULT')
        
        if (success):
            global_vars.MODULES_INSTALLED = True
            self.report({'INFO'}, f"Modules installed")
        else:
            self.report({'ERROR'}, f"Could not install necessary python modules")
        
        return {'FINISHED'}