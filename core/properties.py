
import bpy
from bpy.props import BoolProperty, EnumProperty

from ..utils.shared_data import transformation_options_properties as TOP

def update_circles_visibility(self, context):  # dont remove, its working as it is
    pass

class TTCYIWS_PG_Settings(bpy.types.PropertyGroup):
    bl_idname = "ttc_yiws_op.my_transform_tool_settings"

    scale_checkbox: BoolProperty(**TOP["scale_checkbox"])
    flip_checkbox: BoolProperty(**TOP["flip_checkbox"])
    duplicate_checkbox: BoolProperty(**TOP["duplicate_checkbox"])
    extrude_checkbox: BoolProperty(**TOP["extrude_checkbox"])
    make_instance: BoolProperty(**TOP["make_instance"])

    circles_size_mode: BoolProperty(
        name="Fixed Visual Size",
        description="Keep the gizmo size fixed relative to screen space. Note: This only affects the visual size of the gizmos",
        default=False
    )
    update_prev_gizmo: BoolProperty(
        name="Auto-Update Previous Gizmo",
        description="Whenever the Active Gizmo is created/updated, the Previous Gizmo automatically takes the state of the former Active Gizmo",
        default=True
    )
    use_addon_snap_settings: BoolProperty(
        name="Snap",
        description="Use addon snapping settings instead of the default ones",
        default=True
    )
    use_cursor: BoolProperty(
        name="3D Cursor Orientation",
        description="Use the 3D cursor's orientation when automatically creating the gizmo, and automatically align the cursor to the gizmo whenever the gizmo updates",
        default=True
    )
    circles_view: EnumProperty(
        name="",
        description="",
        items=[
            ('SHOW_ALL', "Show All", "Show all gizmos"),
            ('SHOW_ACTIVE', "Show active Only", "Show only the active gizmo"),
            ('HIDE_ALL', "Hide All", "Hide all gizmos")
        ],
        default='SHOW_ALL',
        update=update_circles_visibility
    )

    gizmo_fold: BoolProperty(default=True)
    options_fold: BoolProperty(default=True)