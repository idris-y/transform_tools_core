import bpy
import bmesh

def transform_objects(context, objects_matrices, transform_matrix, is_duplicate, is_complex_dup, is_instance):
    """
    Applies a transformation matrix to selected objects in Object Mode.
    Handles duplication internally. Uses low-level copy for standard duplication 
    and falls back to bpy.ops.object.duplicate for complex inter-object dependencies.
    """
    all_sel_objs = []
    if is_duplicate:
        if is_complex_dup:
            bpy.ops.object.duplicate(linked=is_instance)
            for obj in context.selected_objects:  # 3. loop through the objects
                obj.matrix_world = transform_matrix @ obj.matrix_world
                
                all_sel_objs.append(obj)

            bpy.ops.object.select_all(action='DESELECT')
            for obj in all_sel_objs:  # Select all duplicated and original objects
                obj.select_set(True)

        else:  # using the efficient method instead
            active_obj_last = None  # pre‑declare
            active_obj_name = context.object.name if context.object else None  # Store active object name

            for obj_name, matrix in objects_matrices:  # Use the cached object names and matrices
                obj = context.scene.objects.get(obj_name)  # need fix, repeated

                new_obj = obj.copy()
                if not is_instance:
                    new_obj.data = obj.data.copy()  # create a unique copy
                context.collection.objects.link(new_obj)  # Link the new object to the collection

                new_obj.matrix_world = transform_matrix @ matrix

                all_sel_objs.append(new_obj)  # Track all created objects
                        
                if obj_name == active_obj_name:  # If this is a duplicate of the active object, track its last instance
                    active_obj_last = new_obj  # store the last active object duplicate
                
            bpy.ops.object.select_all(action='DESELECT')
            for obj in all_sel_objs:  # Select all duplicated and original objects
                obj.select_set(True)
            
            # Set active object to the last duplicate of the original active object if it exists
            if active_obj_last:
                context.view_layer.objects.active = active_obj_last
            
    else:
        for obj_name, matrix in objects_matrices:  # Use the cached object names and matrices
            obj = context.scene.objects.get(obj_name)  # Retrieve object by name
            obj.matrix_world = transform_matrix @ matrix

def transform_mesh(objects_in_mode, transform_matrix, is_duplicate, is_extrude):
    """
    Applies a transformation matrix to the selected elements of a mesh in Edit Mode.
    """
    if is_extrude or is_duplicate:
        # 1. loop through the objects
        for obj in objects_in_mode:
            if obj.type != 'MESH':
                continue

            bm = bmesh.from_edit_mesh(obj.data)  # Enter the bmesh context for each object ONLY ONCE

            # 2. Get the selected elements FOR THIS OBJECT
            original_elements = [v for v in bm.verts if v.select] + \
                                [e for e in bm.edges if e.select] + \
                                [f for f in bm.faces if f.select]
            
            if is_extrude:
                current_elements = original_elements.copy()  # create current_elements now so it can be used in the 1st extrusion

            if not original_elements:
                continue  # If this object had nothing selected, skip to the next one

            # 3. Loop through your transformation definitions for this object
            all_created_elements = []  # Initialize the collector for this object
            # 4. Loop through each individual step's matrix
            local_op_matrix = obj.matrix_world.inverted() @ transform_matrix @ obj.matrix_world  # Calculate the local-space transformation matrix
            if is_extrude:
                # EXTRUDE the original elements within this object's bmesh
                created_data = bmesh.ops.extrude_face_region(bm, geom=current_elements)  # extrude the current elements to apply the relative transformation to it
            else:  # is duplicate
                # DUPLICATE the original elements within this object's bmesh
                created_data = bmesh.ops.duplicate(bm, geom=original_elements)  # duplicate the original elements to apply the full transformation to it
            
            if 'geom' in created_data:
                current_elements = created_data['geom']
                all_created_elements.extend(current_elements)  # 5. Get the new created elements
                
                verts_to_transform = list({v for elem in current_elements for v in getattr(elem, 'verts', [elem])})  # Get the vertices to transform from the new geometry
                if verts_to_transform:
                    # 6. Transform the elements
                    bmesh.ops.transform(bm, matrix=local_op_matrix, verts=verts_to_transform)

            # 7. Selecte the new elements
            if all_created_elements:
                # Deselect everything first for a clean slate
                for v in bm.verts: v.select = False
                for e in bm.edges: e.select = False
                for f in bm.faces: f.select = False
                
                # Select the all the newly created elements
                for elem in all_created_elements:
                    # Check if the element is still valid before trying to select it
                    if elem.is_valid:
                        elem.select = True
            
            # 8. Update the object mesh
            bmesh.update_edit_mesh(obj.data)
            bm.normal_update()

    else:
        for obj in objects_in_mode:
            if obj.type != 'MESH':
                continue

            bm = bmesh.from_edit_mesh(obj.data)
            selected_verts = [v for v in bm.verts if v.select]
            if selected_verts:
                local_op_matrix = obj.matrix_world.inverted() @ transform_matrix @ obj.matrix_world
                bmesh.ops.transform(bm, matrix=local_op_matrix, verts=selected_verts)

                bmesh.update_edit_mesh(obj.data)
                bm.normal_update()

def transform_nurbs(objects_in_mode, transform_matrix, is_duplicate, is_extrude):
    """
    Applies a transformation matrix to Curve and Surface control points in Edit Mode.
    """
    if is_extrude:
        bpy.ops.curve.extrude_move()
    elif is_duplicate:
        try:
            bpy.ops.curve.duplicate()
        except RuntimeError as e:
            return

    for obj in objects_in_mode:
        obj_xform_matrix = obj.matrix_world.inverted() @ transform_matrix @ obj.matrix_world
        for spline in obj.data.splines:
            if spline.type == 'BEZIER':
                for bp in spline.bezier_points:
                    if bp.select_control_point or bp.select_left_handle or bp.select_right_handle:
                        original_left_type = bp.handle_left_type  # Store original handle types
                        original_right_type = bp.handle_right_type
                        bp.handle_left_type = 'FREE'  # Temporarily unlock handles
                        bp.handle_right_type = 'FREE'

                        bp.co = obj_xform_matrix @ bp.co  # Apply transform
                        bp.handle_left = obj_xform_matrix @ bp.handle_left
                        bp.handle_right = obj_xform_matrix @ bp.handle_right

                        bp.handle_left_type = original_left_type  # Restore handle types
                        bp.handle_right_type = original_right_type
            else:
                for bp in spline.points:
                    if bp.select:
                        bp.co.xyz = obj_xform_matrix @ bp.co.xyz  # NURBS or Poly: just transform main point

def tranform_armature(objects_in_mode, transform_matrix, is_duplicate, is_extrude):
    """
    Applies a transformation matrix to Armature bones in Edit Mode.
    """
    if is_extrude:
        bpy.ops.armature.extrude_move()
    elif is_duplicate:
        bpy.ops.armature.duplicate()

    for obj in objects_in_mode:
        obj_xform_matrix = obj.matrix_world.inverted() @ transform_matrix @ obj.matrix_world

        arm = obj.data
        selected_bones = [b for b in arm.edit_bones if b.select_head or b.select_tail]
        if selected_bones:
            for bone in selected_bones:
                if bone.select_head:
                    bone.head = obj_xform_matrix @ bone.head
                if bone.select_tail:
                    bone.tail = obj_xform_matrix @ bone.tail