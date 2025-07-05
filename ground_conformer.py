bl_info = {
    "name":        "Ground Conformer (my_addon)",
    "author":      "Kengo_Hoi",
    "version":     (0, 3, 0),
    "blender":     (3, 6, 0),
    "location":    "View3D ▸ Sidebar ▸ TA",
    "description": "Snap selected props onto ground surface (bottom-face contact)",
    "category":    "Object",
}

import bpy
from mathutils import Vector

def lowest_corner_offset(obj, normal):
    """原点から最下端バウンディングボックス頂点までの距離（法線方向スカラー）"""
    corners = [(obj.matrix_world @ Vector(c)) for c in obj.bound_box]  # ローカル → ワールド:contentReference[oaicite:2]{index=2}
    return min((co - obj.location).dot(normal) for co in corners)

def cast_ground_ray(scene, depsgraph, obj, ray_max):
    """自分自身を無視して真下へレイを飛ばし、地面のヒット位置と法線を返す"""
    up_vec     = Vector((0, 0, 1))
    down_vec   = -up_vec
    start      = obj.location + up_vec * ray_max      # オブジェクト上空から発射:contentReference[oaicite:3]{index=3}
    hit, loc, normal, index, hit_obj, _ = scene.ray_cast(
        depsgraph, start, down_vec, distance=ray_max * 2)

    # 自分自身をヒットした場合はわずかに先へ進めて再試行:contentReference[oaicite:4]{index=4}
    epsilon = 1e-4
    while hit and hit_obj == obj:
        start = loc + down_vec * epsilon
        hit, loc, normal, index, hit_obj, _ = scene.ray_cast(
            depsgraph, start, down_vec, distance=ray_max * 2)
    return hit, loc, normal

class OBJECT_OT_ground_conform(bpy.types.Operator):
    bl_idname  = "object.ground_conform"
    bl_label   = "Ground Conform"
    bl_options = {'REGISTER', 'UNDO'}

    ray_max: bpy.props.FloatProperty(name="Ray Length", default=1000.0, min=0.0)
    align_rotation: bpy.props.BoolProperty(name="Align to Normal", default=False)

    def execute(self, ctx):
        scn      = ctx.scene
        depsgra  = ctx.evaluated_depsgraph_get()

        for obj in ctx.selected_objects:
            if obj.type != 'MESH':
                continue

            hit, loc, normal = cast_ground_ray(scn, depsgra, obj, self.ray_max)
            if not hit:
                self.report({'INFO'}, f"No ground hit for {obj.name}")
                continue

            # 1) 必要なら法線合わせ（Z → ground normal）:contentReference[oaicite:5]{index=5}
            if self.align_rotation:
                obj.rotation_mode = 'QUATERNION'
                obj.rotation_quaternion = normal.to_track_quat('Z', 'Y')

            # 2) 最下端までのオフセットを計算して位置を調整
            offset = lowest_corner_offset(obj, normal)  # 負値
            obj.location = loc - normal * offset

        return {'FINISHED'}

class VIEW3D_PT_ground_conformer(bpy.types.Panel):
    bl_label       = "TA Tools"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "TA"
    def draw(self, ctx):
        self.layout.operator("object.ground_conform", icon='OUTLINER_OB_EMPTY')

classes = (OBJECT_OT_ground_conform, VIEW3D_PT_ground_conformer)
def register():   [bpy.utils.register_class(c) for c in classes]
def unregister(): [bpy.utils.unregister_class(c) for c in classes]

if __name__ == "__main__":
    register()
