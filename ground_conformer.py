bl_info = {
    "name":        "Surface Conformer (my_addon)",
    "author":      "Kengo_Hoi",
    "version":     (0, 4, 1),
    "blender":     (3, 3, 0),
    "location":    "View3D ▸ Sidebar ▸ Snap",
    "description": "Snap selected props onto ground, walls or ceiling (contact along chosen axis)",
    "category":    "Object",
}

import bpy
from mathutils import Vector

# ────────────────────────────────────────────────────────────────────────────────
# Constants & Helpers
# ────────────────────────────────────────────────────────────────────────────────

ENUM_ITEMS = [
    ("NEG_Z", "-Z (Down)", "Cast downwards"),
    ("POS_Z", "+Z (Up)", "Cast upwards"),
    ("NEG_X", "-X (Left)", "Cast toward negative X"),
    ("POS_X", "+X (Right)", "Cast toward positive X"),
    ("NEG_Y", "-Y (Front)", "Cast toward negative Y"),
    ("POS_Y", "+Y (Back)", "Cast toward positive Y"),
]


def extreme_offset(obj: bpy.types.Object, normal: Vector) -> float:
    """Return the scalar distance (along *normal*) from the origin to the extreme
    bounding‑box vertex that lies *against* the surface (i.e. along -normal)."""
    corners_world = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return min((co - obj.location).dot(normal) for co in corners_world)


def cast_axis_ray(scene: bpy.types.Scene,
                  depsgraph: bpy.types.Depsgraph,
                  obj: bpy.types.Object,
                  direction: Vector,
                  ray_max: float):
    """Cast a ray along *direction* ignoring *obj* itself and return hit info."""
    direction = direction.normalized()
    start = obj.location - direction * ray_max  # start behind the object
    hit, loc, normal, idx, hit_obj, _ = scene.ray_cast(depsgraph, start, direction, distance=ray_max * 2)

    eps = 1e-4
    while hit and hit_obj == obj:
        start = loc + direction * eps
        hit, loc, normal, idx, hit_obj, _ = scene.ray_cast(depsgraph, start, direction, distance=ray_max * 2)
    return hit, loc, normal


# ────────────────────────────────────────────────────────────────────────────────
# Main Operator
# ────────────────────────────────────────────────────────────────────────────────

class OBJECT_OT_surface_conform(bpy.types.Operator):
    """Project the selected meshes onto the first surface hit by a ray cast in the
    chosen axis direction, optionally aligning their Z‑axis to the hit normal."""

    bl_idname = "object.surface_conform"
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
        default=False,
    )

    ray_direction: bpy.props.EnumProperty(
        name="Direction",
        description="Axis along which to search for a surface",
        items=ENUM_ITEMS,
        default="NEG_Z",
    )

    _DIR_VECTS = {
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
        direction_vec = self._DIR_VECTS[self.ray_direction]

        for obj in ctx.selected_objects:
            if obj.type != 'MESH':
                continue

            hit, loc, normal = cast_axis_ray(scene, depsgraph, obj, direction_vec, self.ray_max)
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
# UI Panel
# ────────────────────────────────────────────────────────────────────────────────

class VIEW3D_PT_surface_conformer(bpy.types.Panel):
    bl_label       = "Surface Conformer"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "Snap"

    def draw(self, ctx):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Surface Conformer:")
        op = col.operator("object.surface_conform", icon='SNAP_FACE')
        op.ray_max = ctx.scene.surface_conformer_ray_max
        op.align_rotation = ctx.scene.surface_conformer_align
        op.ray_direction = ctx.scene.surface_conformer_direction

        # Expose properties below for convenience
        col.prop(ctx.scene, "surface_conformer_direction", text="Direction")
        col.prop(ctx.scene, "surface_conformer_align", text="Align Z to Normal")
        col.prop(ctx.scene, "surface_conformer_ray_max", text="Ray Length")


# ────────────────────────────────────────────────────────────────────────────────
# Registration
# ────────────────────────────────────────────────────────────────────────────────

classes = (
    OBJECT_OT_surface_conform,
    VIEW3D_PT_surface_conformer,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)

    # Scene‑level properties (so they persist across sessions)
    bpy.types.Scene.surface_conformer_direction = bpy.props.EnumProperty(
        name="Direction",
        items=ENUM_ITEMS,
        default="NEG_Z",
    )
    bpy.types.Scene.surface_conformer_align = bpy.props.BoolProperty(
        name="Align Z to Normal",
        default=False,
    )
    bpy.types.Scene.surface_conformer_ray_max = bpy.props.FloatProperty(
        name="Ray Length",
        default=1000.0,
        min=0.0,
    )


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.surface_conformer_direction
    del bpy.types.Scene.surface_conformer_align
    del bpy.types.Scene.surface_conformer_ray_max


if __name__ == "__main__":
    register()
