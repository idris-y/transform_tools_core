bl_info = {
    "name": "Transform Tools Core",
    "author": "Yasser Idris",
    "version": (0, 9, 6),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > View > TTools C",
    "description": "Define and apply precise transformations using custom gizmos.",
    "warning": "",
    "wiki_url": "",
    "category": "3D View"
}

import bpy
from bpy.props import PointerProperty

from .utils import view_utils as VU
from .core import properties as PR, preferences as PF, main_engine as CR
from .ui_modules import operators as OP, panels as UI

classes = [
    OP.TTCYIWS_OT_MoveSnapCursor,
    OP.TTCYIWS_OT_ModalSnappingReporter,
    OP.TTCYIWS_OT_CircleUpdater,
    OP.TTCYIWS_OT_Wrapper,
    OP.TTCYIWS_OT_AutoAddCircle,
    OP.TTCYIWS_OT_Transformation,
    OP.TTCYIWS_OT_SwapCursors,
    OP.TTCYIWS_OT_ToggleTransformOrientation,
    PR.TTCYIWS_PG_Settings,
    PF.TTCYIWS_TransformToolsPreferences,
    UI.TTCYIWS_PT_TransformToolsPanel
]

def register():
    for cls in classes: # Register classes
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.ttc_yiws_st = PointerProperty(type=PR.TTCYIWS_PG_Settings)

    if not bpy.app.background: # Checking Blender is NOT in background mode.
        if CR.shader_2d is None:
            CR.shader_2d = VU.create_shader_2d()

        if CR.draw_handler is None:
            CR.draw_handler = bpy.types.SpaceView3D.draw_handler_add(CR.draw_callback_px, (None, None), 'WINDOW', 'POST_PIXEL')

    if CR.drawer is None:
        CR.drawer = CR.TTCYIWS_CircleDrawer()

def unregister():
    del bpy.types.WindowManager.ttc_yiws_st
    for cls in classes: # Unregister classes
        bpy.utils.unregister_class(cls)
    
    if CR.shader_2d is not None:
        CR.shader_2d = None

    if CR.draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(CR.draw_handler, 'WINDOW')
        CR.draw_handler = None

    if CR.drawer is not None:
        if hasattr(CR.drawer, 'cleanup'):  # check if drawer has the cleanup method
            CR.drawer.cleanup()  # clean up the drawer variable
        CR.drawer = None

if __name__ == "__main__":
    register()