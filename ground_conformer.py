bl_info = {
    "name":        "Ground_Conformer(my_addon)",
    "author":      "Kengo_Hoi",
    "version":     (0, 2, 0),
    "blender":     (3, 6, 0),
    "location":    "View3D > Sidebar > TA Tools",
    "description": "Snap selected props onto ground surface (bottom-face contact)",
    "category":    "Object",
}

import bpy
from mathutils import Vector

def lowest_corner_offset(obj, normal):
    """原点から一番下のバウンディングボックス頂点までの距離を返す"""
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]                # ローカル→ワールド座標へ変換 :contentReference[oaicite:0]{index=0}
    dists   = [(co - obj.location).dot(normal) for co in corners]                  # 法線方向のスカラー距離
    return min(dists)                                                              # 最小＝最下端（負値）

class OBJECT_OT_ground_conform(bpy.types.Operator):
    bl_idname  = "object.ground_conform"
    bl_label   = "Ground Conform"
    bl_options = {'REGISTER', 'UNDO'}

    ray_max: bpy.props.FloatProperty(name="Ray Length", default=1000.0, min=0.0)
    align_rotation: bpy.props.BoolProperty(name="Align to Normal", default=False)

    def execute(self, ctx):
        scn      = ctx.scene
        depsgra  = ctx.evaluated_depsgraph_get()                                   # 評価後データで正確にヒット判定 :contentReference[oaicite:1]{index=1}
        down_vec = Vector((0, 0, -1))

        for obj in ctx.selected_objects:
            if obj.type != 'MESH':
                continue

            # 1) レイキャストで真下のサーフェスを取得
            hit, loc, normal, *_ = scn.ray_cast(depsgra, obj.location, down_vec,
                                                distance=self.ray_max)            # :contentReference[oaicite:2]{index=2}
            if not hit:
                continue

            # 2) 必要なら法線合わせ（Z軸→ヒット法線）
            if self.align_rotation:
                obj.rotation_mode = 'QUATERNION'
                obj.rotation_quaternion = normal.to_track_quat('Z', 'Y')

            # 3) 原点から底面までのオフセット距離を求め，法線方向に移動
            offset = lowest_corner_offset(obj, normal)                             # 負値
            obj.location = loc - normal * offset                                   # 底面がちょうど接地

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
