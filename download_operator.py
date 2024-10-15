import bpy
import os
import requests
from . import global_vars
import threading
from . import future

class DownloadPropertyGroup(bpy.types.PropertyGroup):
    url: bpy.props.StringProperty()
    path: bpy.props.StringProperty()

class DownloadFileOperator(bpy.types.Operator):
    """Download the depth prediction model"""
    bl_idname = "dmp.download_model"
    bl_label = "Download File"
    
    download_list: bpy.props.CollectionProperty(type=DownloadPropertyGroup)
    total_files: bpy.props.IntProperty()
    current_file_index: bpy.props.IntProperty()
    
    future_chunk = None
    
    _timer = None

    def execute(self, context):
        if self.current_file_index >= self.total_files:
            self.report({'INFO'}, "Download complete")
            return {'FINISHED'}
        
        url = self.download_list[self.current_file_index].url
        self.file_path = self.download_list[self.current_file_index].path
        
        self._response = requests.get(url, stream=True)
        self._response.raise_for_status()
        
        self._total_size = int(self._response.headers.get('content-length', 0))
        self._block_size = 1024 * 1000
        self._downloaded = 0
        
        self._file = open(self.file_path, 'wb')
        
        
        # Start async download
        self.future_chunk = future.Future()
        
        # Run the async task in a separate thread
        threading.Thread(target=self.async_download_chunk).start()
        
        
        
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        if global_vars.MODELS_CACHED: return {'FINISHED'}
        if event.type == 'TIMER':
            props = context.scene.DMPprops
            
            # Update UI
            wm = context.window_manager
            for w in wm.windows:
                for area in w.screen.areas:
                    area.tag_redraw()
            
            # Download next chunk
            try:
                if self.future_chunk.done:
                    chunk = self.future_chunk.result()
                    self.future_chunk = future.Future()
                    threading.Thread(target=self.async_download_chunk).start()
                else:
                    return {'PASS_THROUGH'}
                if not chunk:
                    return self._finish_file(context)
                
                self._file.write(chunk)
                self._downloaded += len(chunk)
                props.download_progress = 100*((self.current_file_index + self._downloaded / self._total_size) / self.total_files)
                
            except StopIteration:
                return self._finish_file(context)
            
            except Exception as e:
                self.report({'ERROR'}, str(e))
                return self._cancel(context)
            
        return {'PASS_THROUGH'}
    
    
    def async_download_chunk(self):
        try:
            chunk = next(self._response.iter_content(self._block_size))
            self.future_chunk.add_response(chunk)
        except Exception as e:
            self.future_chunk.set_exception(e)
        finally:
            self.future_chunk.set_done()
    
    
    def _close_file(self):
        if hasattr(self, '_file') and not self._file.closed:
            self._file.close()
    
    def _finish_file(self, context):
        self._close_file()
        
        self.current_file_index += 1
        if self.current_file_index < self.total_files:
            return self.execute(context)
        else:
            return self._finish(context)
    
    def _finish(self, context):
        context.window_manager.event_timer_remove(self._timer)
        self.report({'INFO'}, "Download complete")
        global_vars.MODELS_CACHED = True
        
        return {'FINISHED'}
    
    def _cancel(self, context):
        self._close_file()
        
        for i in range(self.total_files):
            file_path = self.download_list[i].path
            os.remove(file_path)
            
        context.window_manager.event_timer_remove(self._timer)
        
        return {'CANCELLED'}

    def invoke(self, context, event):
        props = context.scene.DMPprops
        props.download_progress = 0.0
        self.current_file_index = 0
        self.total_files = len(self.download_list)
        
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, window=context.window)
        
        wm.modal_handler_add(self)
        
        return self.execute(context)