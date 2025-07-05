bl_info = {
    "name":        "Ground Conformer (my_addon)",
    "author":      "Kengo_Hoi",
    "version":     (0, 4, 0),
    "blender":     (3, 6, 0),
    "location":    "View3D ▸ Sidebar ▸ my_addons",
    "description": "Snap selected props onto ground, walls or ceiling (contact along chosen axis)",
    "category":    "Object",
}

import bpy
from mathutils import Vector

# ────────────────────────────────────────────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────────────────────────────────────────────

def extreme_offset(obj: bpy.types.Object, normal: Vector) -> float:
    """Return the scalar distance (along *normal*) from the origin to the extreme
    bounding‑box vertex that lies *against* the surface (i.e. along -normal).
    Negative values mean the origin is above / inside with respect to the surface."""
    corners_world = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return min((co - obj.location).dot(normal) for co in corners_world)


def cast_axis_ray(scene: bpy.types.Scene,
                  depsgraph: bpy.types.Depsgraph,
                  obj: bpy.types.Object,
                  direction: Vector,
                  ray_max: float):
    """Cast a ray along *direction* ignoring *obj* itself.

    The ray originates *ray_max* units *behind* the object and travels twice that
    length. If the first hit is the object itself we nudge the start point a bit
    past the hit and retry (\u03b5‑shift) until we either hit something else or
    reach empty space.
    """
    direction = direction.normalized()
    start = obj.location - direction * ray_max
    hit, loc, normal, index, hit_obj, _ = scene.ray_cast(depsgraph, start, direction, distance=ray_max * 2)

    ε = 1e-4
    while hit and hit_obj == obj:
        start = loc + direction * ε
        hit, loc, normal, index, hit_obj, _ = scene.ray_cast(depsgraph, start, direction, distance=ray_max * 2)
    return hit, loc, normal


# ────────────────────────────────────────────────────────────────────────────────
# Main operator
# ────────────────────────────────────────────────────────────────────────────────

class OBJECT_OT_ground_conform(bpy.types.Operator):
    """Project the selected meshes onto the first surface hit by a ray cast in the
    chosen axis direction, optionally aligning their Z‑axis to the hit normal."""

    bl_idname = "object.ground_conform"
    bl_label = "Conform to Surface"
    bl_options = {"REGISTER", "UNDO"}

    ray_max: bpy.props.FloatProperty(
        name="Ray Length",
        description="Half‑length of the bidirectional ray",
        default=1000.0,
        min=0.0,
    )

    align_rotation: bpy.props.BoolProperty(
        name="Align Z to Normal",
        description="Rotate object so its local Z axis matches the surface normal",
        default=False,
    )

    ray_direction: bpy.props.EnumProperty(
        name="Direction",
        description="Axis along which to search for a surface",
        items=[
            ("NEG_Z", "-Z (Down)", "Cast downwards"),
            ("POS_Z", "+Z (Up)", "Cast upwards"),
            ("NEG_X", "-X (Left)", "Cast toward negative X"),
            ("POS_X", "+X (Right)", "Cast toward positive X"),
            ("NEG_Y", "-Y (Front)", "Cast toward negative Y"),
            ("POS_Y", "+Y (Back)", "Cast toward positive Y"),
        ],
        default="NEG_Z",
    )

    # Mapping from enum to unit vector
    _DIR_MAP = {
        "NEG_Z": Vector((0, 0, -1)),
        "POS_Z": Vector((0, 0,  1)),
        "NEG_X": Vector((-1, 0, 0)),
        "POS_X": Vector((1, 0,  0)),
        "NEG_Y": Vector((0, -1, 0)),
        "POS_Y": Vector((0, 1,  0)),
    }

    def execute(self, ctx):
        scene = ctx.scene
        depsgraph = ctx.evaluated_depsgraph_get()
        direction = self._DIR_MAP[self.ray_direction]

        for obj in ctx.selected_objects:
            if obj.type != 'MESH':
                continue

            hit, loc, normal = cast_axis_ray(scene, depsgraph, obj, direction, self.ray_max)
            if not hit:
                self.report({'INFO'}, f"No surface hit for {obj.name}")
                continue

            if self.align_rotation:
                obj.rotation_mode = 'QUATERNION'
                obj.rotation_quaternion = normal.to_track_quat('Z', 'Y')

            offset = extreme_offset(obj, normal)
            obj.location = loc - normal * offset

        return {'FINISHED'}


# ────────────────────────────────────────────────────────────────────────────────
# Simple UI
# ────────────────────────────────────────────────────────────────────────────────

class VIEW3D_PT_ground_conformer(bpy.types.Panel):
    bl_label       = "Surface Conformer"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "Snap"

    def draw(self, ctx):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Ground / Wall Conformer:")
        op = col.operator("object.ground_conform", icon='SNAP_FACE')
        # Expose key parameters directly in the panel for quick access
        col.prop(ctx.scene, "ground_conformer_direction", text="Direction")
        col.prop(ctx.scene, "ground_conformer_align", text="Align Z to Normal")

# -----------------------------------------------------------------------------
# Registration helpers
# -----------------------------------------------------------------------------

classes = (
    OBJECT_OT_ground_conform,
    VIEW3D_PT_ground_conformer,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)

    # Store panel‑level properties at scene level so they persist
    bpy.types.Scene.ground_conformer_direction = bpy.props.EnumProperty(
        name="Direction",
        items=OBJECT_OT_ground_conform.ray_direction[1]['items'],  # reuse items
        default="NEG_Z",
    )
    bpy.types.Scene.ground_conformer_align = bpy.props.BoolProperty(
        name="Align Z to Normal",
        default=False,
    )


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.ground_conformer_direction
    del bpy.types.Scene.ground_conformer_align

if __name__ == "__main__":
    register()
