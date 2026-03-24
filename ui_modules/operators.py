import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, StringProperty, IntProperty
from mathutils import Vector, Matrix
import math

from ..core import main_engine as CR
from ..utils import math_utils as MU, view_utils as VU, object_mesh_utils as OU
from ..utils.shared_data import transformation_options_properties as TOP
            
class TTCYIWS_OT_Wrapper(Operator):
    bl_idname = "ttc_yiws_op.wrapper_move_snap_cursor"
    bl_label = "Cursor transform"
    bl_description = "Creates a 3D gizmo with X, Y, and Z axes"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        if context.window_manager.ttc_yiws_st.circles_view == 'HIDE_ALL':
            context.window_manager.ttc_yiws_st.circles_view = "SHOW_ALL"

        if len(CR.drawer.circles) == 0 or len(CR.drawer.circles) >=4:
            CR.drawer.show_HUD = context.space_data.show_region_hud  # store the current HUD visibility state, to restore it after the gizmo creation
            if context.space_data.show_region_hud:  # check if the HUD is visible first, to avoid unnecessary changing to it
                context.space_data.show_region_hud = False  # hide it, to hide the redo panel

            CR.drawer.start_point = True
            if context.window_manager.ttc_yiws_st.use_addon_snap_settings:
                CR.drawer.original_use_snap = context.tool_settings.use_snap
                CR.drawer.original_snap_elements = context.tool_settings.snap_elements.copy()
                CR.drawer.original_align_rotation = context.tool_settings.use_snap_align_rotation
                CR.drawer.original_use_snap_self = context.tool_settings.use_snap_self
                CR.drawer.original_use_snap_edit = context.tool_settings.use_snap_edit
                CR.drawer.original_use_snap_nonedit = context.tool_settings.use_snap_nonedit
                context.tool_settings.use_snap = True
                context.tool_settings.snap_elements = {'VERTEX', 'EDGE', 'FACE', 'EDGE_MIDPOINT'}
                context.tool_settings.use_snap_align_rotation = True
                context.tool_settings.use_snap_self = True
                context.tool_settings.use_snap_edit = True
                context.tool_settings.use_snap_nonedit = True
        else:
            CR.drawer.start_point = False
        MU.add_circle(context, CR.drawer)  # Draw circle immediately
        bpy.ops.ttc_yiws_op.move_snap_cursor('INVOKE_DEFAULT', mouse_x=event.mouse_region_x, mouse_y=event.mouse_region_y)
        return {'FINISHED'}
        
class TTCYIWS_OT_MoveSnapCursor(Operator):
    """
    A background operator called to move the 3D cursor to the mouse's projected 
    3D location and trigger Blender's native snapping logic.
    """
    bl_idname = "ttc_yiws_op.move_snap_cursor"
    bl_label = "Move and Snap Cursor"
    bl_options = {'REGISTER', 'UNDO'}

    mouse_x: IntProperty()
    mouse_y: IntProperty()

    def execute(self, context):
        st = context.window_manager.ttc_yiws_st
        if CR.drawer.start_point:  # check if it's the start point to store the 3D cursor infos
            if not st.use_cursor and CR.drawer.pre_cursor:
                CR.drawer.pre_cursor.translation = context.scene.cursor.location.copy()
            else:
                CR.drawer.pre_cursor = context.scene.cursor.matrix.copy()
        context.scene.cursor.location = VU.move_cursor(context, self.mouse_x, self.mouse_y)
        bpy.ops.transform.translate('INVOKE_DEFAULT', cursor_transform=True)
        bpy.ops.ttc_yiws_op.modal_snapping_reporter('INVOKE_DEFAULT')
        return {'FINISHED'}

class TTCYIWS_OT_ModalSnappingReporter(Operator):
    """
    A modal operator that runs continuously during gizmo creation. 
    It tracks the mouse/cursor position to update the gizmo drawing in real-time, 
    and handles mouse clicks to finalize circle placements.
    """
    bl_idname = "ttc_yiws_op.modal_snapping_reporter"
    bl_label = "Modal Snapping Reporter"

    def modal(self, context, event):
        op = bpy.ops.ttc_yiws_op
        if (event.type == 'ESC' and event.value == 'RELEASE') or (event.type == 'RIGHTMOUSE' and event.value == 'RELEASE'):
            op.circle_updater('EXEC_DEFAULT', auto_update=True)
            op.auto_add_circle('INVOKE_DEFAULT')
            if CR.drawer.start_point:  # check if it's the start point
                CR.drawer.circles[-1] = CR.drawer.circles[-1].copy()  # stop the current circle location from being updated to the cursor location
            return {'FINISHED'}
        if (event.type == 'LEFTMOUSE' and event.value == 'RELEASE'):
            if CR.drawer.start_point:
                CR.drawer.circles[-1] = CR.drawer.circles[-1].copy()
                if not context.window_manager.ttc_yiws_st.use_cursor and CR.drawer.pre_cursor:
                    CR.drawer.pre_cursor.translation = context.scene.cursor.location.copy()  # store the 3D cursor location only
                else:
                    CR.drawer.pre_cursor = context.scene.cursor.matrix.copy()  # store the 3D cursor matrix
            if len(CR.drawer.circles) > 1:
                op.circle_updater('EXEC_DEFAULT')
            
            op.auto_add_circle('INVOKE_DEFAULT')
            return {'FINISHED'}
        MU.update_circle(CR.drawer.circles, context.scene.cursor.location)
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class TTCYIWS_OT_CircleUpdater(Operator):
    """
    Calculates the precise snapping locations for the secondary circles (X, Y, Z axes) 
    based on the initial center placement and the current cursor position.
    """
    bl_idname = "ttc_yiws_op.circle_updater"
    bl_label = "Circle Updater"
    auto_update: BoolProperty(default=False)

    def execute(self, context):
        dr = CR.drawer
        new_loc = context.scene.cursor.location.copy()
        white_circle = dr.circles[0]
        if len(dr.circles) == 1 : # checking if white circle is the current circle
            new_loc = dr.pre_cursor.translation  # white circle location
        elif len(dr.circles) == 2: # checking if red circle is the current circle
            if self.auto_update:  # check if red circle will be auto created
                dr.circles[1] = white_circle  # make red circle the same as white circle so it will be updated
            if (dr.circles[1] - white_circle).length < 1e-6:  # check if red circle is close to white circle
                if not context.window_manager.ttc_yiws_st.use_cursor and dr.pre_cursor_scale:
                    scale = dr.pre_cursor_scale
                else:
                    scale = max(1e-4, VU.get_zoom_factor(context, dr.ui_scale, white_circle))  # avoid making the scale too small
                new_loc = dr.pre_cursor @ (Vector((1, 0, 0)) * scale)  # computing red circle location
        else: # checking if green/blue circle is the current circle
            x_axis = dr.circles[1] - white_circle  # dont normalize x axis cause it have the scale value
            new_loc = dr.circles[2] # green circle location
            if self.auto_update:  # check if green circle will be auto created
                new_loc = white_circle
            if (new_loc - white_circle).length < 1e-6:  # check if green circle is close to the white circle
                y_dir = x_axis.normalized()  # make it parallel to x axis
            else:
                y_dir = (new_loc - white_circle).normalized()  # gettig y axis directly from green circle location
            if abs(x_axis.normalized().dot(y_dir)) >= 1 - 1e-6:  # check if y axis is parallel to x axis
                y_dir = dr.pre_cursor.to_3x3().col[2].cross(x_axis)
                if y_dir.length < 1e-6:  # this mean the previous z axis is parallel to x axis
                    y_dir = x_axis.cross(dr.pre_cursor.to_3x3().col[0])  # flipping the cross product order to get the correct y axis direction
            _, y_axis, _ = MU.get_xyz_from_2_vectors(x_axis, y_dir)
            new_loc = white_circle + y_axis.normalized() * x_axis.length

        MU.update_circle(dr.circles, new_loc)
        dr.creating_gizmo = None
        VU.tag_redraw_all_view3d()
        return {'FINISHED'}

class TTCYIWS_OT_AutoAddCircle(Operator):
    bl_idname = "ttc_yiws_op.auto_add_circle"
    bl_label = "Auto Add Circle"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event=None):
        op = bpy.ops.ttc_yiws_op
        if len(CR.drawer.circles) < 3:
            op.wrapper_move_snap_cursor('INVOKE_DEFAULT')  # Trigger the snapping and adding of the next circle
        else:
            st = context.window_manager.ttc_yiws_st
            # finishing the current gizmo creation
            CR.drawer.creating_gizmo = None  # reset the creating gizmo
            MU.update_circles_history(context, CR.drawer)
            context.scene.cursor.matrix = MU.calculate_transformation_matrix(CR.drawer.circles)  # align the 3d cursor with the current gizmo
            if st.use_addon_snap_settings:
                context.tool_settings.use_snap = CR.drawer.original_use_snap
                context.tool_settings.snap_elements = CR.drawer.original_snap_elements
                context.tool_settings.use_snap_align_rotation = CR.drawer.original_align_rotation
                context.tool_settings.use_snap_self = CR.drawer.original_use_snap_self
                context.tool_settings.use_snap_edit = CR.drawer.original_use_snap_edit
                context.tool_settings.use_snap_nonedit = CR.drawer.original_use_snap_nonedit
                
            VU.show_the_HUD(context, CR.drawer.show_HUD)  # show the HUD, and finish the circle creation

        return {'FINISHED'}
        
class TTCYIWS_OT_Transformation(Operator):
    """
    The core execution operator. Extracts settings from the UI/Redo panel, 
    calculates the relative matrix between the Previous and Active gizmos, 
    and delegates the transformation to the appropriate mesh/object utilities.
    """
    bl_idname = "ttc_yiws_op.transformation_ops"
    bl_label = "Transformation ops"
    bl_description = "Transform the selection from the Previous (Faded) Gizmo to the active (Bright) Gizmo"
    bl_options = {'REGISTER', 'UNDO'}
    
    complex_duplication: BoolProperty(
        name="Complex Dup",
        description="Handles complex object relationships (e.g., Booleans targeting other duplicated objects) more accurately. This mode may be slower. Enable if standard duplication causes issues with linked modifiers",
        default=True
        )
    reverse: BoolProperty(
        name="Reverse",
        description="inverts the transformation's direction. It makes the selection transform from the Active gizmo to the Previous gizmo, instead of the default direction of Previous to Active",
        default=False
        )
    
    scale_checkbox: BoolProperty(**TOP["scale_checkbox"])
    flip_checkbox: BoolProperty(**TOP["flip_checkbox"])
    duplicate_checkbox: BoolProperty(**TOP["duplicate_checkbox"])
    extrude_checkbox: BoolProperty(**TOP["extrude_checkbox"])
    make_instance: BoolProperty(**TOP["make_instance"])

    objects_matrices = []
    
    first_execution: bool = True
    cursor_matrix = Matrix.Identity(4)

    def execute(self, context):
        st = context.window_manager.ttc_yiws_st

        if self.first_execution:  # Detect redo by checking the internal flag
            self.cursor_matrix = context.scene.cursor.matrix
            self.first_execution = False  # Mark as already executed, at the very end

        # update the ui values with the redo menu ones
        st.scale_checkbox = self.scale_checkbox
        st.flip_checkbox = self.flip_checkbox
        st.duplicate_checkbox = self.duplicate_checkbox
        st.extrude_checkbox = self.extrude_checkbox
        
        # creating the current & previous matrices
        if len(CR.drawer.circles) < 4 or len(CR.drawer.previous_circles) < 4:
            return {'CANCELLED'}
        
        current_matrix = MU.calculate_transformation_matrix(CR.drawer.circles)   # use the previous & current gizmo as usual
        prev_matrix = MU.calculate_transformation_matrix(CR.drawer.previous_circles)
        current_x_axis = CR.drawer.circles[1]
        prev_x_axis = CR.drawer.previous_circles[1]

        if self.reverse:  # reverse the gizmos to reverse the transformation
            current_matrix, prev_matrix = prev_matrix, current_matrix
            current_x_axis, prev_x_axis = prev_x_axis, current_x_axis

        if self.flip_checkbox:
            prev_matrix @= Matrix.Rotation(math.radians(180), 4, 'Y')
        
        # creating the transformation matrix
        if self.scale_checkbox:
            current_matrix_scale = (current_x_axis - current_matrix.translation).length
            prev_matrix_scale = (prev_x_axis - prev_matrix.translation).length
            r = current_matrix_scale / prev_matrix_scale  # get the scale ratio
        else:
            r = 1
            
        scale_matrix = Matrix.Diagonal(Vector((r, r, r, 1.0)))  # creating a scale matrix using the scale factor
        scale_diff_matrix = prev_matrix @ scale_matrix @ prev_matrix.inverted()  # Scale relative to the prev matrix's local space
        transform_matrix = current_matrix @ prev_matrix.inverted() @ scale_diff_matrix

        # applying the transformation matrix to the selected element
        selected_obj = True  # flag to check if any object is selected, for the 3d cursor transformation, now its only works for object mode
        # Edit mode section
        if context.object and context.object.mode == 'EDIT':  # appling it in edit mode
            is_extrude = self.extrude_checkbox  # localization
            is_duplicate = self.duplicate_checkbox  # localization
            
            objects_in_mode = context.objects_in_mode
            object_type = context.object.type
            if context.object.type == 'MESH':
                OU.transform_mesh(objects_in_mode, transform_matrix, is_duplicate, is_extrude)

            elif object_type in {'CURVE', 'SURFACE'}:
                OU.transform_nurbs(objects_in_mode, transform_matrix, is_duplicate, is_extrude)

            if object_type == 'ARMATURE':
                OU.tranform_armature(objects_in_mode, transform_matrix, is_duplicate, is_extrude)

        # Object mode section
        elif context.selected_objects and context.mode == 'OBJECT':
            OU.transform_objects(context, self.objects_matrices, transform_matrix, self.duplicate_checkbox, self.complex_duplication, self.make_instance)

        else:
            selected_obj = False

        # applying the transformation matrix to the 3D cursor
        if selected_obj:  # check if cursor need to be transformed with selected elements from the previous gizmo position
            context.scene.cursor.matrix = current_matrix
        else:  # cursor will be transformed from its current position
            context.scene.cursor.matrix = transform_matrix @ self.cursor_matrix  # update the 3D cursor matrix
            
        return {'FINISHED'}

    def invoke(self, context, event):  # Initialize default values and store object matrices
        st = context.window_manager.ttc_yiws_st

        self.reverse = False

        properties_list = [
            "make_instance",
            "scale_checkbox",
            "flip_checkbox",
            "duplicate_checkbox",
            "extrude_checkbox"
        ]
        for prop_name in properties_list:
            prop_value = getattr(st, prop_name)
            setattr(self, prop_name, prop_value)

        self.objects_matrices = [(obj.name, obj.matrix_world.copy()) for obj in context.selected_objects]  # Store object names and their matrices

        return self.execute(context)

    def draw(self, context):  # Draw the redo panel UI
        is_object_mode = context.mode == 'OBJECT'
        layout = self.layout
        row = layout.row()
        split = row.split()
        subrow_1 = split.row()
        subrow_1.prop(self, "scale_checkbox")
        subrow_2 = split.row()
        subrow_2.prop(self, "flip_checkbox")

        row = layout.row()
        split = row.split()
        subrow = split.row()
        subrow.prop(self, "duplicate_checkbox")
        subrow.enabled = is_object_mode or not self.extrude_checkbox
        subrow = split.row()
        subrow.prop(self, "make_instance" if is_object_mode else "extrude_checkbox")
        subrow.enabled = self.duplicate_checkbox or not is_object_mode

        row = layout.row()
        split = row.split()
        subrow_1 = split.row()
        subrow_1.prop(self, "reverse")
        if is_object_mode:
            subrow_2 = split.row()
            subrow_2.prop(self, "complex_duplication")

class TTCYIWS_OT_SwapCursors(Operator):
    bl_idname = "ttc_yiws_op.swap_cursors"
    bl_label = ""
    operation: StringProperty()

    def execute(self, context):
        st = context.window_manager.ttc_yiws_st
        if self.operation == 'Show_Hide':
            values = ['SHOW_ALL', 'SHOW_ACTIVE', 'HIDE_ALL']
            current_index = values.index(st.circles_view)
            st.circles_view = values[(current_index + 1) % len(values)]
        else:  # undo/redo operation
            if st.circles_view == 'HIDE_ALL':
                st.circles_view  = "SHOW_ALL"
            
            MU.update_circles_history(context, CR.drawer, self.operation)
            VU.tag_redraw_all_view3d()
            
        return {'FINISHED'}

    @classmethod
    def description(cls, context, properties):  # Provide descriptions based on the operation value
        if properties.operation == 'SWAP':
            return "Swaps the two gizmos with each other"
        elif properties.operation == "cycle":
            return "Axes Cycling\nCycles the active gizmo axes: X → Z, Y → X, Z → Y"
        elif properties.operation == "rotate":
            return "Rotate\nRotate the active gizmo around its X-axis by 90 degrees"
        elif properties.operation == "global":
            return "Global Align\nAlign Active Gizmo to World: Resets the Active Gizmo's rotation to align its axes with the global X, Y, and Z axes. The gizmo's origin remains unchanged"
        elif properties.operation == "undo_gizmos":
            return "Undo gizmos"
        elif properties.operation == "redo_gizmos":
            return "Redo gizmos"
        elif properties.operation == "Show_Hide":
            desc = bpy.context.window_manager.bl_rna.properties["circles_view"].enum_items[bpy.context.window_manager.ttc_yiws_st.circles_view].description
            return f"Gizmos visibility options\ncurrent: {desc}"

class TTCYIWS_OT_ToggleTransformOrientation(Operator):
    bl_idname = "ttc_yiws_op.toggle_transform_orientation"
    bl_label = "Toggle Transform Orientation"
    bl_description = "Toggle between the 3D cursor and the last used transform orientation and pivot point"

    def invoke(self, context, event):
        scene = context.scene
        tool_settings = context.tool_settings

        current_orientation = scene.transform_orientation_slots[0].type # Store the current settings
        current_pivot = tool_settings.transform_pivot_point
        prev_orientation = CR.drawer.blender_transformation_orientation # get the previous settings from the drawer
        prev_pivot = CR.drawer.blender_transformation_pivot
        if current_orientation == 'CURSOR' or current_pivot == 'CURSOR':
            if prev_orientation and prev_pivot: # If the current settings are the custom settings, restore the previous settings
                scene.transform_orientation_slots[0].type = prev_orientation
                tool_settings.transform_pivot_point = prev_pivot
            else: # If no previous settings stored, set to default settings
                scene.transform_orientation_slots[0].type = 'LOCAL'
                tool_settings.transform_pivot_point = 'MEDIAN_POINT'
        else: # Store the current settings as previous settings
            CR.drawer.blender_transformation_orientation = current_orientation
            CR.drawer.blender_transformation_pivot = current_pivot
            scene.transform_orientation_slots[0].type = 'CURSOR' # Set to custom settings
            tool_settings.transform_pivot_point = 'CURSOR'
        return {'FINISHED'}