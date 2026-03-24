transformation_options_properties = {
    "make_instance": {
        "name": "Instance",
        "description": "Create linked instances instead of unique object duplicates",
        "default": True,
    },
    "scale_checkbox": {
        "name": "Scale",
        "description": "Use the scale of the Gizmos during the transformation. If disabled, Gizmos scale will be ignored",
        "default": False,
    },
    "flip_checkbox": {
        "name": "Flip",
        "description": "Flip the Previous gizmo Z direction, by rotating it 180 degrees at its Y-axis",
        "default": False,
    },
    "duplicate_checkbox": {
        "name": "Duplicate",
        "description": "Duplicate the selected before applying the transformation",
        "default": False,
    },
    "extrude_checkbox": {
        "name": "Extrude",
        "description": "Extrude the selected during the transformation, works in Edit Mode only",
        "default": False,
    }
}