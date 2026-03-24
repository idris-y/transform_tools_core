import bpy
import math
from mathutils import Vector
from bpy_extras import view3d_utils
import gpu
import blf

# creating the 2D shader
def create_shader_2d():
    """
    Compiles a custom GPU shader used for rendering the Gizmo UI in the 3D viewport.
    Handles anti-aliasing, thickness, and depth-sorting for circles and lines.
    """
    vertex_shader_2d = """
        void main() {
            pos = position;
            gl_Position = vec4(position, 0.0, 1.0);
        }
    """
    fragment_shader_2d = """
        float interpolate_depth(vec2 line_start, vec2 line_end, float start_depth, float end_depth, vec2 pixel_pos) {
            vec2 line_vector = line_end - line_start;
            vec2 pixel_vector = pixel_pos - line_start;
            float t = dot(pixel_vector, line_vector) / dot(line_vector, line_vector);
            t = clamp(t, 0.0, 1.0);
            return mix(start_depth, end_depth, t);
        }
        
        void main() {
            vec4 final_color = vec4(0.0);
            float aa_range = 0.75;
            
            struct ShapeData {
                vec4 color;
                float depth;
                float alpha;
            };
            ShapeData shapes[32];
            int valid_shapes = 0;
            
            for (int i = 0; i < num_shapes; i++) {
                vec4 color_type = shapesBlock.color_type[i];
                vec4 geometry = shapesBlock.geometry[i];
                vec4 depth = shapesBlock.depth_data[i];
                
                vec3 shape_color = color_type.xyz;
                float shape_type = color_type.w;
                float shape_alpha = 0.0;
                float pixel_depth = 0.0;
                
                if (shape_type > 0.5) {  // Circle types
                    vec2 circle_center = geometry.xy;
                    vec2 to_pixel = gl_FragCoord.xy - circle_center;
                    float dist = length(to_pixel);
                    float radius = geometry.z;
                    float outer_edge = 1.0 - smoothstep(radius - aa_range, radius + aa_range, dist);
                    float inner_edge = (shape_type < 1.5) ?
                        smoothstep(radius - global_thickness - aa_range, radius - global_thickness + aa_range, dist) :  // create a ring
                        1.0;  // create a solid circle
                    shape_alpha = outer_edge * inner_edge;
                    pixel_depth = depth.x;
                } else {  // Line (0.0)
                    vec2 line_start = geometry.xy;
                    vec2 line_end = geometry.zw;
                    vec2 line_vector = line_end - line_start;
                    vec2 frag_vector = gl_FragCoord.xy - line_start;
                    float projection = clamp(dot(frag_vector, line_vector) / dot(line_vector, line_vector), 0.0, 1.0);
                    vec2 closest = line_start + projection * line_vector;
                    float dist_to_line = distance(gl_FragCoord.xy, closest);
                    shape_alpha = 1.0 - smoothstep(global_thickness / 2.0 - 1.0, (global_thickness / 2.0 - 1.0) + aa_range *2.0, dist_to_line);
                    pixel_depth = interpolate_depth(line_start, line_end, depth.x, depth.y, gl_FragCoord.xy);
                }
                if (shape_alpha > 0.001) {
                    shapes[valid_shapes].color = vec4(shape_color, shape_alpha);
                    shapes[valid_shapes].depth = pixel_depth;
                    shapes[valid_shapes].alpha = shape_alpha;
                    valid_shapes++;
                }
            }
            for (int i = 0; i < valid_shapes - 1; i++) {  // Sort shapes based on depth (bubble sort).
                for (int j = 0; j < valid_shapes - i - 1; j++) {
                    if (shapes[j].depth > shapes[j + 1].depth) {
                        ShapeData temp = shapes[j];
                        shapes[j] = shapes[j + 1];
                        shapes[j + 1] = temp;
                    }
                }
            }
            for (int i = 0; i < valid_shapes; i++) {  // Blend shape contributions.
                float blend_factor = shapes[i].alpha * (1.0 - final_color.a);
                final_color.rgb += shapes[i].color.rgb * blend_factor;
                final_color.a += blend_factor;
            }
            
            FragColor = vec4(final_color.rgb, final_color.a * 0.88);  // FragColor is the final_color after multiplying it by a fixed opacity
        }
    """
    shader_info = gpu.types.GPUShaderCreateInfo()

    shader_info.vertex_source(vertex_shader_2d)
    shader_info.fragment_source(fragment_shader_2d)
    shader_info.push_constant('FLOAT', "global_thickness")
    shader_info.push_constant('INT', "num_shapes")
    shader_info.typedef_source("""
        struct ShapesBlock {
            vec4 color_type[32];
            vec4 geometry[32];
            vec4 depth_data[32];
        };
    """)
    shader_info.uniform_buf(0, 'ShapesBlock', "shapesBlock")
    shader_info.vertex_in(0, 'VEC2', "position")

    vert_out = gpu.types.GPUStageInterfaceInfo("out_data")
    vert_out.smooth("VEC2", "pos")
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', "FragColor")

    created_shader_2d = gpu.shader.create_from_info(shader_info)
    return created_shader_2d

def tag_redraw_all_view3d():
    """
    Forces a viewport redraw across all open 3D views. 
    Called when gizmo states update to ensure the GPU drawing updates instantly.
    """
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

def move_cursor(context, mouse_x, mouse_y):
    """
    Projects 2D screen/mouse coordinates into the 3D viewport space to 
    determine the exact placement for the 3D Cursor based on the mouse location in the viewport.
    """
    region = context.region
    rv3d = context.space_data.region_3d
    coord = (mouse_x, mouse_y)
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    ray_target = ray_origin + (view_vector * 1000)
    ray_direction = (ray_target - ray_origin).normalized()
    cursor_to_ray_origin = context.scene.cursor.location - ray_origin
    projection_length = cursor_to_ray_origin.dot(ray_direction)
    projection_point = ray_origin + ray_direction * projection_length
    return projection_point

def draw_text_2d(font_id, text, x, y, size, color=(1, 1, 1, 1)):  # A helper function to draw text. You can adapt this.
    """Simple wrapper for BLF text drawing."""
    blf.size(font_id, size)
    blf.color(font_id, color[0], color[1], color[2], color[3])
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, text)
    
def show_the_HUD(context, show_HUD):
    """Show the HUD in the 3D Viewport."""
    if show_HUD:  # check if the HUD is supposed to be shown
        context.space_data.show_region_hud = True  # enable it again

def get_zoom_factor(context, ui_scale, loc):
    """
    Calculates the necessary scale factor to keep the Gizmos at a constant 
    visual size on the screen, regardless of camera distance or perspective/ortho mode.
    """
    region = context.region
    rv3d = context.space_data.region_3d
    
    target_2d_size = ui_scale * 23.5
    ortho_f = 4.2
    cam_f = 1250
    cam_ortho_f = 2.9
    
    region_length = max(region.height, region.width)
    depth = (rv3d.view_matrix @ loc.to_4d()).z
    # Handle perspective and orthographic views separately
    zoom_factor = 1
    if rv3d.view_perspective == 'CAMERA' and context.space_data.camera:
        camera_obj = context.space_data.camera
        camera = camera_obj.data
        camera_frame = camera.view_frame(scene=context.scene)
        frame_2d = []
        for v in camera_frame:
            coord_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, camera_obj.matrix_world @ v)
            frame_2d.append(coord_2d)

        min_x = min([v.x for v in frame_2d])
        max_x = max([v.x for v in frame_2d])
        min_y = min([v.y for v in frame_2d])
        max_y = max([v.y for v in frame_2d])
        cam_frame_length = max((max_x - min_x), (max_y - min_y))
        cam_frame_zoom = region_length / cam_frame_length
        
        if camera.type == 'PERSP':
            fov_y = 2 * math.atan(camera.sensor_height * camera.lens / 2)
            zoom_factor = cam_f * (target_2d_size * abs(depth)) / (region_length * math.tan(fov_y / 2)) * cam_frame_zoom
        elif camera.type == 'ORTHO':
            zoom_factor = cam_ortho_f * target_2d_size * camera.ortho_scale / cam_frame_length
            
    elif rv3d.view_perspective == 'PERSP':
        fov_y = 2 * math.atan(24 / (2 * context.space_data.lens)) # 24 is the blender default sensor size & space_data.lens is the focal length
        zoom_factor = (target_2d_size * abs(depth)) / (region_length * math.tan(fov_y / 2))
    elif rv3d.view_perspective == 'ORTHO':
        ortho_scale = rv3d.view_distance  # Use view_distance in orthographic view
        zoom_factor = ortho_f * target_2d_size * ortho_scale / region_length
    return zoom_factor

def intersect_with_view_plane(loc1, loc2, clip_start, rv3d):  # crop_line function
    """
    Calculates the 3D intersection point between a line segment and the 
    camera's near clipping plane. Used to prevent rendering artifacts when 
    part of the gizmo goes behind the camera.
    """
    view_direction = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))  # The view direction is -Z in the view space
    view_origin = rv3d.view_matrix.inverted().translation  # The camera/view origin
    view_origin_c = view_origin + view_direction * clip_start # clipping the view_origin
    
    distance_loc1 = (loc1 - view_origin).dot(view_direction)
    distance_clipping_plane = (view_origin_c - view_origin).dot(view_direction)
    if abs(distance_loc1) < abs(distance_clipping_plane): # Check if loc1 is in front of the clipping plane
        return None
    
    direction = (loc2 - loc1).normalized()
    direction_alignment = direction.dot(view_direction)
    if direction_alignment == 0.0: # Check if the line between loc1 and loc2 is parallel to the view plane (no intersection)
        return None
    # Calculate the intersection point along the line at the clipping distance
    distance_to_plane = (view_origin_c - loc1).dot(view_direction) / direction_alignment # Calculate the line distance between loc1 & the clipped view plane
    intersect_point = loc1 + direction * distance_to_plane # Calculate the intersection point along the line at the clipping distance
    return intersect_point

def get_circle_border_point(center, target, radius):  # crop_line function
    """
    Calculates a 2D point on the circumference of a circle pointing towards a target.
    Used to ensure drawn lines start exactly at the circle's edge, not its center.
    """
    angle = math.atan2(target[1] - center[1], target[0] - center[0])
    border_point = center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle)
    return border_point

def crop_line(session, clip_start, region, rv3d, loc1, loc2, color, line_data, shape_type=1):
    """
    Calculates the visible segment of a connecting line between two Gizmo circles.
    Accounts for camera clipping planes and subtracts the circle radius so lines 
    do not cross the circle borders.
    """
    if loc1 is None or loc2 is None:
        return
        
    coord1 = view3d_utils.location_3d_to_region_2d(region, rv3d, loc1)
    coord2 = view3d_utils.location_3d_to_region_2d(region, rv3d, loc2)
    if coord1 is None and coord2 is None:
        return
    elif coord1 is None:
        loc1 = intersect_with_view_plane(loc2, loc1, clip_start, rv3d)
        if loc1 is not None: 
            coord1 = view3d_utils.location_3d_to_region_2d(region, rv3d, loc1)
    elif coord2 is None:
        loc2 = intersect_with_view_plane(loc1, loc2, clip_start, rv3d)
        if loc2 is not None: 
            coord2 = view3d_utils.location_3d_to_region_2d(region, rv3d, loc2)
        
    if coord1 and coord2:
        if shape_type == 2:
            radius_1 = 0
            radius_2 = 0
        else:
            radius_1 = session.center_radius
            if session.creating_gizmo == color:
                radius_2 = session.creating_radius
            else:
                radius_2 = session.small_radius
        if (coord2 - coord1).length > (radius_1 + radius_2): # if the two circles not intersects
            border1 = get_circle_border_point(coord1, coord2, radius_1)
            border2 = get_circle_border_point(coord2, coord1, radius_2)
            line_data.append((border1, border2, color, get_z_in_view_space(rv3d, loc1), get_z_in_view_space(rv3d, loc2)))  # adding z_value too

def get_z_in_view_space(rv3d, loc):
    """
    Converts a 3D world location into Normalized Device Coordinates (NDC) Z-depth.
    Required by the custom GPU shader to correctly depth-sort circles and lines.
    """
    if loc is None:
        return float('inf')
    
    clip_space_loc = rv3d.perspective_matrix @ loc.to_4d()
    if clip_space_loc.w != 0.0:
        ndc_z = clip_space_loc.z / clip_space_loc.w
    else:
        ndc_z = clip_space_loc.z
    
    return ndc_z

def keep_gizmo_size(context, circles, ui_scale):
    """
    Dynamically scales the gizmo's circle coordinates relative to the camera distance 
    so the gizmo maintains a fixed visual size on the user's screen.
    """
    if len(circles) >= 4:
        resized_circles = [circles[0]]
        circles_scale = get_zoom_factor(context, ui_scale, circles[0])
        for loc in circles[1:]:
            zoomed_loc = circles[0] + (loc - circles[0]).normalized() * circles_scale
            resized_circles.append(zoomed_loc)
        return resized_circles
    else:
        return circles