import bpy

import bpy
from bpy_extras import view3d_utils
from mathutils import Vector
import math
import gpu
from gpu_extras.batch import batch_for_shader
import array
import blf

from ..utils import math_utils as MU, view_utils as VU

shader_2d = None
draw_handler = None
drawer = None
                
def draw_callback_px(self, context):
    """
    The main POST_PIXEL draw handler entry point. 
    Routes visibility settings to the drawing logic.
    """
    circles_visability = bpy.context.window_manager.ttc_yiws_st.circles_view
    if circles_visability != 'HIDE_ALL':
        draw_callback(circles_visability)

def draw_callback(circles_visability='SHOW_ALL'):
    """
    Collects and formats all geometric data (circles, lines, colors, depth) for the Gizmos,
    and pushes the compiled data to the GPU Uniform Buffer for batch rendering.
    """
    context = bpy.context
    region = context.region
    rv3d = context.space_data.region_3d
    st = context.window_manager.ttc_yiws_st
            
    prev_circles = []
    if st.circles_size_mode:
        if drawer.creating_gizmo is None:
            current_circles = VU.keep_gizmo_size(context, drawer.circles, drawer.ui_scale)
        else:
            current_circles = drawer.circles
        if circles_visability  == 'SHOW_ALL':
            prev_circles = VU.keep_gizmo_size(context, drawer.previous_circles, drawer.ui_scale)
    else:
        current_circles = drawer.circles
        if circles_visability  == 'SHOW_ALL':
            prev_circles = drawer.previous_circles
    drawer.scaled_circles = current_circles
    drawer.scaled_prev_circles = prev_circles

    all_circles = [[loc, color] for loc, color in zip(current_circles, drawer.colors)] + [[loc, color] for loc, color in zip(prev_circles, drawer.previous_colors)]  # create all circles location and color list

    all_lines = [] # creat lines from circles
    clip_start = context.space_data.clip_start
    for loc, color in zip(current_circles[1:], drawer.colors[1:]):
        VU.crop_line(drawer, clip_start, region, rv3d, current_circles[0], loc, color, all_lines)  # shape_type = 1
    for loc, color in zip(prev_circles[1:], drawer.previous_colors[1:]):
        VU.crop_line(drawer, clip_start, region, rv3d, prev_circles[0], loc, color, all_lines)
    for loc1, loc2, color in drawer.constraints_lines:
        VU.crop_line(drawer, clip_start, region, rv3d, loc1, loc2, color, all_lines, 2)

    all_elements = []
    for circle in all_circles:
        all_elements.append((*circle, 'circle'))
    for line in all_lines:
        all_elements.append((*line, 'line'))
    for circle in drawer.constraints_points:
        if len(circle) == 2:
            circle.append(2)
        all_elements.append((*circle, 'constraint'))

    max_shapes = 32  # max shapes amount for the drawing
    color_type_data = [0.0] * (max_shapes * 4)  # Allocate arrays for the shapes; each shape has 4 floats per vec4.
    geometry_data = [0.0] * (max_shapes * 4)
    depth_data = [0.0] * (max_shapes * 4)
    num_shapes = 0
    for element in all_elements:
        if num_shapes >= max_shapes:
            break
        if element[-1] == 'line':  # Handle lines
            color = element[2]
            start_coord = element[0]
            end_coord = element[1]
            if start_coord and end_coord:
                st_loc = (start_coord[0], start_coord[1])
                ed_loc = (end_coord[0], end_coord[1])
                geometry_data[num_shapes*4:num_shapes*4+4] = [st_loc[0], st_loc[1], ed_loc[0], ed_loc[1]]
                color_type_data[num_shapes*4:num_shapes*4+4] = [*color[:3], 0]
                depth_data[num_shapes*4:num_shapes*4+4] = [element[3], element[4], 0.0, 0.0]
                num_shapes += 1
        elif element[-1] == 'circle':  # Handle circles as lines
            color = element[1]
            coord = view3d_utils.location_3d_to_region_2d(region, rv3d, element[0])
            z_value = VU.get_z_in_view_space(rv3d, element[0])
            if coord:
                loc = (coord[0], coord[1])
                shape_type = 1
                if drawer.creating_gizmo == color:
                    radius = drawer.creating_radius
                elif color in {drawer.colors[0], drawer.previous_colors[0]}:
                    radius = drawer.center_radius
                else:
                    radius = drawer.small_radius
                    shape_type = 2
                geometry_data[num_shapes*4:num_shapes*4+4] = [*loc, radius, 0]
                color_type_data[num_shapes*4:num_shapes*4+4] = [*color[:3], shape_type]  # the color and shape, 0 for line, 1 for ring, 2 for solid circle
                depth_data[num_shapes*4:num_shapes*4+4] = [z_value, 0.0, 0.0, 0.0]
                num_shapes += 1
        elif element[-1] == 'constraint':  # Handle solid constraint circles
            coord = view3d_utils.location_3d_to_region_2d(region, rv3d, element[0])
            if coord:
                color = element[1]
                z_value = VU.get_z_in_view_space(rv3d, element[0])
                loc = (coord[0], coord[1])
                shape_type = element[2]
                if shape_type == 2:
                    radius = drawer.small_radius
                else:
                    radius = drawer.con_radius
                geometry_data[num_shapes*4:num_shapes*4+4] = [*loc, radius, 0]
                color_type_data[num_shapes*4:num_shapes*4+4] = [*color[:3], shape_type]
                depth_data[num_shapes*4:num_shapes*4+4] = [z_value, 0.0, 0.0, 0.0]
                num_shapes += 1
    
    ubo_data = color_type_data + geometry_data + depth_data  # Concatenate the data arrays: first color_type_data, then geometry_data, then depth_data
    ubo_array = array.array('f', ubo_data)  # Convert the list of floats to a bytes-like object
    ubo_buffer = gpu.types.GPUUniformBuf(ubo_array.tobytes())
    draw_batch(ubo_buffer,  num_shapes)

def draw_batch(ubo_buffer, num_shapes):
    """
    Binds the custom 2D shader, uniform buffers, and properties, then 
    dispatches the actual GPU draw call to render the gizmos to the viewport.
    """
    gpu.state.blend_set('ALPHA')
    screen_coord = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    batch = batch_for_shader(shader_2d, 'TRI_FAN', {"position": screen_coord})
    
    shader_2d.bind()
    shader_2d.uniform_float("global_thickness", drawer.global_thickness)
    shader_2d.uniform_int("num_shapes", num_shapes)
    shader_2d.uniform_block("shapesBlock", ubo_buffer)
    
    batch.draw(shader_2d)
    gpu.state.blend_set('NONE')

class TTCYIWS_CircleDrawer:
    """
    A persistent session class that stores the runtime state of the gizmos.
    Holds the locations, colors, history stack, and UI scaling data required 
    for drawing and transforming.
    """
    def __init__(self):
        self.ui_scale = bpy.context.preferences.system.ui_scale * (bpy.context.preferences.view.gizmo_size / 75)  # calculating the ui scale for the auto zoom, by multiplying the ui scale with the gizmo size scale ratio, 75 is the default value
        self.global_thickness = 3 * self.ui_scale
        self.pre_cursor = None
        self.pre_cursor_scale = None
        self.show_HUD = False
        self.start_point = False
        self.constrains_pre_cursor_loc = None
        
        self.blender_transformation_orientation = None  # create the current settings variables
        self.blender_transformation_pivot = None
        
        self.circles = []
        self.previous_circles = []
        self.scaled_circles = []
        self.scaled_prev_circles = []
        self.colors = [(0.8, 0.8, 0.8), (1.0, 0.0331, 0.0844), (0.2582, 0.63, 0.0), (0.0212, 0.2789, 1.0)]
        self.previous_colors = [(0.02, 0.02, 0.02), (0.34, 0.011, 0.0281), (0.086, 0.2836, 0.0), (0.007, 0.093, 0.34)]

        self.circles_history = [[[],[]]]
        self.num_history = 0

        self.constraints_points = []
        self.constraints_lines = []
        self.constraints_3d_circles = []
        self.con_col = [(0.0, 0.8, 0.8), (0.8, 0.5, 0.0), (0.8, 0.0, 0.8), (0.8, 0.0, 0.0)]

        self.center_radius = 9 * self.ui_scale
        self.small_radius = 5.33 * self.ui_scale
        self.con_radius = 9.6 * self.ui_scale
        self.creating_radius = 15 * self.ui_scale
        self.creating_gizmo = None

        self.selection_modal_message = "Make a selection & press ENTER or Right-click to continue (or ESC to stop)"  # the waiting selection modal displayed message

        self.original_use_snap = False
        self.original_snap_elements = set()
        self.original_align_rotation = False
        self.original_use_snap_self = False
        self.original_use_snap_edit = False
        self.original_use_snap_nonedit = False

    def cleanup(self):
        self.pre_cursor = None
        self.start_point = False
        self.constrains_pre_cursor_loc = None
        
        self.blender_transformation_orientation = None
        self.blender_transformation_pivot = None
        
        self.circles = []
        self.previous_circles = []
        self.scaled_circles = []
        self.scaled_prev_circles = []

        self.circles_history = [[[],[]]]
        self.num_history = 0

        self.constraints_points = []
        self.constraints_lines = []
        self.constraints_3d_circles = []

        self.creating_gizmo = None

        self.original_snap_elements = set()