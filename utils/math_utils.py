from mathutils import Vector, Matrix

def get_xyz_from_2_vectors(x_axis, y_axis, to_get='Z'):
    """
    Derives three orthogonal (perpendicular) axes from two directional vectors.
    Includes fallback logic to prevent zero-vectors if the input axes are parallel.
    """
    x_axis = x_axis.normalized()  # normalize the x_axis

    z_dir = x_axis.cross(y_axis).normalized()  # get the perpendicular direction as the cross product of x_axis and y_axis
    if z_dir.length < 0.5:  # thats meaning the x_axis and y_axis are parallel
        axes_map = {'X': 0, 'Y': 1, 'Z': 2}
        mat = Matrix.Identity(3)
        z_dir = mat.col[axes_map[to_get]]  # get the global axis instead
        if abs(z_dir.dot(x_axis)) >= 1 - 1e-6:  # check if the x_axis is parallel to the global y axis
            z_dir = mat.col[(axes_map[to_get] + 1) % 3]  # get the next global axis in the cycle

    y_axis = z_dir.cross(x_axis).normalized()  # recalculate the y_axis to be perpendicular to the x_axis and the calculated perpendicular direction
    z_axis = x_axis.cross(y_axis).normalized()  # get the z_axis as the cross product of y_axis and x_axis

    if to_get == 'Y':
        z_axis *= -1  # flip the y_axis direction if it is Y axis

    return x_axis, y_axis, z_axis

def create_custom_matrix(x_axis, y_axis, z_axis, location=Vector(), scale_factor=1):
    """
    Constructs a complete 4x4 transformation matrix (LocRotScale) from 
    individual positional, directional, and scale components.
    """
    scale = Vector((scale_factor, scale_factor, scale_factor))
    rotation_mat = Matrix((x_axis, y_axis, z_axis)).transposed()
    matrix = Matrix.LocRotScale(location, rotation_mat, scale)
    return matrix

def calculate_transformation_matrix(circles):
    """
    Calculates the 4x4 transformation matrix representing a Gizmo's state, 
    derived directly from the 3D coordinates of its 4 defining circles.
    """
    center = circles[0]
    x_axis = (circles[1] - center).normalized()
    z_axis = (circles[3] - center).normalized()
    y_axis = z_axis.cross(x_axis).normalized()

    return create_custom_matrix(x_axis, y_axis, z_axis, center, scale_factor=1)

# --- Circles Functions ---

def add_circle(context, session):
    """
    gizmo creation state function.
    If a gizmo is complete (4 circles), it stores the current state as 'Previous'
    and starts a new 'Active' gizmo at the cursor's location.
    """
    cursor_location = context.scene.cursor.location.copy()
    if len(session.circles) >= 4:  # create a new gizmo
        session.pre_cursor = calculate_transformation_matrix(session.circles)  # store the gizmo matrix
        session.pre_cursor_scale = (session.circles[1] - session.circles[0]).length  # store the gizmo scale
        if context.window_manager.ttc_yiws_st.update_prev_gizmo:  # if the previous gizmo is not locked, or in create & transform mode
            session.previous_circles = session.circles  # make the current gizmo the previous gizmo
        session.circles = [cursor_location]  # start a new gizmo
    else:  # continue the current gizmo creation
        session.circles.append(cursor_location)
    session.creating_gizmo = session.colors[(len(session.circles)-1)]
    if len(session.circles) == 3:  # check if the green circle has been added
        session.circles.append(cursor_location)  # auto add the blue circle

def update_circle(circles, new_loc):
    """
    Updates the active gizmo's circle positions in real-time during mouse movement.
    Automatically calculates the orthogonal Y and Z circles based on the distance 
    and direction of the X (red) circle from the center.
    """
    if len(circles) <= 2:
        circles[-1] = new_loc  # real-time update the white or red circles
    else:
        circles[-2] = new_loc  # real-time update the green circle
        white_circle = circles[0]
        x_vec = circles[1] - white_circle
        y_vec = circles[2] - white_circle
        z_vec = x_vec.cross(y_vec)
        circles[3] = white_circle + z_vec.normalized() * x_vec.length  # real-time update the blue circle
        
def update_circles_history(context, session, update="append"):
    """
    Manages the Undo/Redo stack specifically for the Gizmo's internal states,
    allowing users to step back through previous Gizmo placements.
    """
    if update == "append":
        if session.num_history < len(session.circles_history)-1:  # check if the current circle is the not the last one in the history list
            del session.circles_history[session.num_history +1:]  # remove the beyond value/s to replace it with the new one
        session.circles_history.append([[v.copy() for v in session.circles], [v.copy() for v in session.previous_circles]])  # update it with the current gizmos
        if len(session.circles_history) > 64:
            del session.circles_history[:len(session.circles_history) - 64]  # prevent circles history list from exceed 64
        session.num_history = len(session.circles_history)-1  # update the current circle place in the history list
    else:
        if update == "undo_gizmos" and session.num_history >= 1:
            session.num_history -= 1   # Move back one step in the history (to the previous state).
            session.circles = [v.copy() for v in session.circles_history[session.num_history][0]]  # Restore its next state's
            session.previous_circles = [v.copy() for v in session.circles_history[session.num_history][1]]
        elif update == "redo_gizmos" and session.num_history < len(session.circles_history)-1:
            session.num_history += 1  # Move forward one step in the history (to the next state).
            session.circles = [v.copy() for v in session.circles_history[session.num_history][0]]  # same as above
            session.previous_circles = [v.copy() for v in session.circles_history[session.num_history][1]]
    st = context.window_manager.ttc_yiws_st
    if len(session.circles) >= 4 and st.use_cursor:
        context.scene.cursor.matrix = calculate_transformation_matrix(session.circles)  # update the cursor matrix