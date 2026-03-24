import bpy

ADDON_ID = __package__.rsplit('.', 1)[0] if '.' in __package__ else __package__

class TTCYIWS_TransformToolsPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID
    def draw(self, context):
        layout = self.layout

        layout.label(text="Enabling GPU subdivision may cause a brief freeze the first time snapping is used in a complex scene.", icon='INFO')
        layout.label(text="To prevent this, you can disable it in Preferences > Viewport > Subdivision.")