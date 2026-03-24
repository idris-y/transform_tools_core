import bpy
from ..core import main_engine as CR

class TTCYIWS_PT_TransformToolsPanel(bpy.types.Panel):
    bl_idname = "TTCYIWS_PT_transform_tools"
    bl_label = "Transform Tools Core"  # The label inside the expanded panel
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TTools C" # The label of the TAB

    def draw(self, context):
        layout = self.layout
        st = context.window_manager.ttc_yiws_st
        active_gizmo = bool(len(CR.drawer.circles) >= 4)
        prev_gizmo = bool(len(CR.drawer.previous_circles) >= 4)

        enable_buttons = active_gizmo and prev_gizmo

        # --- Gizmo Section ---
        box = layout.box()
        row = box.row(align=True)
        row.prop(st, "gizmo_fold", emboss=False, icon="DOWNARROW_HLT" if st.gizmo_fold else "RIGHTARROW", icon_only=True)
        row.label(text="Operations")
        if st.gizmo_fold:
            col = box.column(align=True)
            row = col.row(align=True)

            row = col.row(align=True)
            row.operator("ttc_yiws_op.wrapper_move_snap_cursor", text="Create")

            row.prop(st, "update_prev_gizmo", toggle=True,icon="ORIENTATION_PARENT", icon_only=True)
            row.prop(st, "use_cursor", toggle=True, icon="CURSOR", icon_only=True)
            row.prop(st, "use_addon_snap_settings", toggle=True,icon="SNAP_ON" if st.use_addon_snap_settings else "SNAP_ON" if context.tool_settings.use_snap else "SNAP_OFF", icon_only=True)

            row = col.row(align=True)
            sub_col = row.column(align=True)
            sub_col.enabled = CR.drawer.num_history >= 1  # Only enable if there's a state to undo to it
            op = sub_col.operator("ttc_yiws_op.swap_cursors", icon='LOOP_BACK')
            op.operation = "undo_gizmos"
            sub_col = row.column(align=True)
            sub_col.enabled = CR.drawer.num_history < len(CR.drawer.circles_history)-1  # Enable if there's a "next" state available
            op = sub_col.operator("ttc_yiws_op.swap_cursors", icon='LOOP_FORWARDS')
            op.operation = "redo_gizmos"
            row.operator("ttc_yiws_op.toggle_transform_orientation", text="Cursor Pivot")
            row.prop(st, "circles_size_mode", toggle=True, icon="FIXED_SIZE", icon_only=True)

            op = row.operator("ttc_yiws_op.swap_cursors", icon="HIDE_OFF" if st.circles_view == 'SHOW_ALL' else "VIS_SEL_10" if st.circles_view == 'SHOW_ACTIVE' else "HIDE_ON")
            op.operation = "Show_Hide"

            # transform operation
            col = box.column(align=True)
            row = col.row(align=True)
            row.enabled = enable_buttons
            row.operator("ttc_yiws_op.transformation_ops", text="Transform")

        # --- Options Section ---
        box = layout.box()
        row = box.row(align=True)
        row.prop(st, "options_fold", emboss=False, icon="DOWNARROW_HLT" if st.options_fold else "RIGHTARROW", icon_only=True)
        row.label(text="Options")

        if st.options_fold:
            col = box.column(align=True)
            row = col.row(align=True)
            row.prop(st, "scale_checkbox")
            row.prop(st, "flip_checkbox")
            row = col.row(align=True)
            row.prop(st, "duplicate_checkbox")
            row.prop(st, "make_instance" if context.mode == 'OBJECT' else "extrude_checkbox")
