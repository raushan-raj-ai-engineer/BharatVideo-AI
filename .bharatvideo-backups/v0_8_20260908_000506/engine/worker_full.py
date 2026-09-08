from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--plan", required=True)
    p.add_argument("--timeline", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--quality", default="")
    p.add_argument("--max-scenes", type=int, default=0)
    return p.parse_args(argv)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def material(name, color, rough=0.55, metallic=0.0):
    m = bpy.data.materials.new(name)
    # Blender 5.x creates node-based materials by default.
    if not m.node_tree:
        try:
            m.use_nodes = True
        except Exception:
            pass
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
    return m


def emissive_material(name, color, strength=3.0, rough=0.28):
    m = material(name, color, rough)
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.node_tree else None
    if bsdf:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = (*color, 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = float(strength)
    return m


def add_uv(name, loc, scale, mat, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, location=loc
    )
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    for poly in o.data.polygons:
        poly.use_smooth = True
    return o


def add_cube(name, loc, scale, mat, bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new("SoftEdges", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    return o


def add_cylinder(name, start, end, radius, mat):
    start = Vector(start)
    end = Vector(end)
    vec = end - start
    mid = (start + end) / 2
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24,
        radius=radius,
        depth=vec.length,
        location=mid,
    )
    o = bpy.context.object
    o.name = name
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = vec.to_track_quat("Z", "Y")
    o.data.materials.append(mat)
    bevel = o.modifiers.new("JointSoftness", "BEVEL")
    bevel.width = min(radius * 0.35, 0.06)
    bevel.segments = 2
    return o


def create_empty(name, location):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.location = location
    return o



COLORS = {
    "guddu": {
        "skin": (0.58, 0.26, 0.12), "shirt": (0.05, 0.35, 0.72),
        "pants": (0.06, 0.08, 0.16), "hair": (0.025, 0.018, 0.015),
    },
    "bittu": {
        "skin": (0.63, 0.31, 0.15), "shirt": (0.90, 0.35, 0.08),
        "pants": (0.08, 0.12, 0.23), "hair": (0.03, 0.02, 0.015),
    },
    "babuji": {
        "skin": (0.50, 0.23, 0.11), "shirt": (0.80, 0.73, 0.47),
        "pants": (0.22, 0.18, 0.12), "hair": (0.18, 0.16, 0.14),
    },
    "mai": {
        "skin": (0.60, 0.28, 0.13), "shirt": (0.65, 0.08, 0.28),
        "pants": (0.28, 0.05, 0.12), "hair": (0.025, 0.018, 0.015),
    },
}

CHARACTER_PROFILES = {
    "guddu": {
        "height": 1.05, "torso": (0.43, 0.28, 0.65),
        "hip": (0.35, 0.25, 0.25), "head": (0.40, 0.34, 0.47),
        "shoulder_x": 0.41, "upper_arm": 0.40, "lower_arm": 0.36,
        "leg": 0.72, "hair_style": "swept", "body_tag": "tall_slim",
    },
    "bittu": {
        "height": 0.92, "torso": (0.53, 0.32, 0.58),
        "hip": (0.43, 0.29, 0.27), "head": (0.46, 0.38, 0.48),
        "shoulder_x": 0.47, "upper_arm": 0.36, "lower_arm": 0.33,
        "leg": 0.63, "hair_style": "tuft", "body_tag": "short_round",
    },
    "babuji": {
        "height": 0.95, "torso": (0.57, 0.34, 0.61),
        "hip": (0.48, 0.31, 0.29), "head": (0.47, 0.38, 0.48),
        "shoulder_x": 0.49, "upper_arm": 0.37, "lower_arm": 0.34,
        "leg": 0.64, "hair_style": "receding", "body_tag": "older_wide",
    },
    "mai": {
        "height": 0.98, "torso": (0.45, 0.28, 0.62),
        "hip": (0.45, 0.30, 0.29), "head": (0.42, 0.35, 0.47),
        "shoulder_x": 0.42, "upper_arm": 0.37, "lower_arm": 0.34,
        "leg": 0.66, "hair_style": "bun", "body_tag": "medium_slim",
    },
}


def parent_local(obj, parent, location=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0)):
    obj.parent = parent
    obj.location = location
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = rotation
    return obj


def local_empty(name, parent, location=(0.0, 0.0, 0.0)):
    o = create_empty(name, (0.0, 0.0, 0.0))
    return parent_local(o, parent, location)


def local_uv(name, parent, location, scale, mat, segments=28, rings=14):
    o = add_uv(name, (0.0, 0.0, 0.0), scale, mat, segments, rings)
    return parent_local(o, parent, location)


def local_cube(name, parent, location, scale, mat, bevel=0.06):
    o = add_cube(name, (0.0, 0.0, 0.0), scale, mat, bevel)
    return parent_local(o, parent, location)


def local_segment(name, parent, length, radius, mat):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=20, radius=radius, depth=length, location=(0.0, 0.0, 0.0)
    )
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    bevel = o.modifiers.new("JointSoftness", "BEVEL")
    bevel.width = min(radius * 0.30, 0.045)
    bevel.segments = 2
    parent_local(o, parent, (0.0, 0.0, -length / 2.0))
    return o


def create_character(char_id, base):
    profile = CHARACTER_PROFILES.get(char_id, CHARACTER_PROFILES["guddu"])
    colors = COLORS.get(char_id, COLORS["guddu"])
    h = float(profile["height"])

    skin = material(f"{char_id}_skin", colors["skin"], 0.66)
    shirt = material(f"{char_id}_shirt", colors["shirt"], 0.52)
    pants = material(f"{char_id}_pants", colors["pants"], 0.68)
    hair = material(f"{char_id}_hair", colors["hair"], 0.78)
    white = material(f"{char_id}_eye_white", (0.98, 0.98, 0.95), 0.36)
    pupil_mat = material(f"{char_id}_pupil", (0.012, 0.010, 0.008), 0.30)
    mouth_mat = material(f"{char_id}_mouth", (0.24, 0.018, 0.025), 0.46)
    shoe = material(f"{char_id}_shoe", (0.035, 0.03, 0.025), 0.68)
    accent = material(f"{char_id}_accent", (0.90, 0.72, 0.22), 0.62)

    root = create_empty(f"{char_id}_ROOT", base)
    root.rotation_mode = "XYZ"

    torso_z = 1.52 * h
    hip_z = 0.92 * h
    shoulder_z = 1.70 * h
    head_z = 2.27 * h

    torso = local_uv(
        f"{char_id}_torso", root, (0, 0, torso_z),
        profile["torso"], shirt
    )
    hip = local_uv(
        f"{char_id}_hip", root, (0, 0, hip_z),
        profile["hip"], pants
    )

    # Distinct silhouette extras.
    if char_id == "babuji":
        local_uv(
            f"{char_id}_belly", root, (0, -0.025, 1.38 * h),
            (0.60, 0.35, 0.44), shirt, 28, 14
        )
        local_cube(
            f"{char_id}_kurta_panel", root, (0, -0.03, 1.12 * h),
            (0.46, 0.22, 0.38), shirt, 0.08
        )
    elif char_id == "mai":
        drape = local_cube(
            f"{char_id}_dupatta", root, (-0.18, -0.18, 1.55 * h),
            (0.15, 0.05, 0.72), accent, 0.04
        )
        drape.rotation_euler.y = math.radians(-12)
    elif char_id == "bittu":
        local_uv(
            f"{char_id}_round_belly", root, (0, -0.02, 1.34 * h),
            (0.51, 0.31, 0.40), shirt, 24, 12
        )

    neck = local_segment(f"{char_id}_neck", root, 0.18 * h, 0.115, skin)
    neck.location = (0, 0, 2.00 * h)

    # Face hierarchy: rotating HEAD_PIVOT rotates head + eyes + pupils + mouth.
    head_pivot = local_empty(f"{char_id}_HEAD_PIVOT", root, (0, 0, head_z))
    head_mesh = local_uv(
        f"{char_id}_head", head_pivot, (0, 0, 0),
        profile["head"], skin
    )

    hair_style = profile["hair_style"]
    if hair_style == "swept":
        local_uv(
            f"{char_id}_hair", head_pivot, (-0.06, 0.02, 0.29),
            (0.43, 0.35, 0.19), hair, 24, 12
        )
        local_uv(
            f"{char_id}_hair_sweep", head_pivot, (0.22, -0.03, 0.30),
            (0.20, 0.15, 0.12), hair, 20, 10
        )
    elif hair_style == "tuft":
        local_uv(
            f"{char_id}_hair", head_pivot, (0, 0.02, 0.29),
            (0.45, 0.37, 0.18), hair, 24, 12
        )
        local_uv(
            f"{char_id}_hair_tuft", head_pivot, (0.12, -0.05, 0.42),
            (0.16, 0.11, 0.18), hair, 18, 9
        )
    elif hair_style == "receding":
        local_uv(
            f"{char_id}_hair_back", head_pivot, (0, 0.08, 0.26),
            (0.40, 0.34, 0.13), hair, 22, 11
        )
    elif hair_style == "bun":
        local_uv(
            f"{char_id}_hair", head_pivot, (0, 0.04, 0.28),
            (0.42, 0.35, 0.18), hair, 24, 12
        )
        local_uv(
            f"{char_id}_hair_bun", head_pivot, (0.0, 0.22, 0.34),
            (0.20, 0.17, 0.20), hair, 20, 10
        )

    if char_id == "babuji":
        local_cube(
            f"{char_id}_moustache", head_pivot, (0, -0.355, -0.105),
            (0.19, 0.026, 0.038), hair, 0.02
        )

    # V6.2 recognizable face + costume layer: inexpensive geometry, much stronger identity.
    nose = local_uv(
        f"{char_id}_nose", head_pivot, (0.0, -0.405, -0.035),
        (0.075 if char_id != "babuji" else 0.095, 0.075, 0.105), skin, 20, 10
    )
    ears = []
    for side, dx in (("L", -0.39), ("R", 0.39)):
        ear = local_uv(
            f"{char_id}_ear_{side}", head_pivot, (dx, -0.01, -0.015),
            (0.070, 0.045, 0.105), skin, 18, 9
        )
        ears.append(ear)

    costume_parts = []
    if char_id == "babuji":
        # Black glasses frame, red tilak, vest/scarf stripes make Babuji readable even in a wide shot.
        frame_mat = material(f"{char_id}_glasses", (0.018, 0.015, 0.012), 0.34)
        tilak_mat = material(f"{char_id}_tilak", (0.70, 0.035, 0.018), 0.48)
        scarf_mat = material(f"{char_id}_scarf", (0.90, 0.88, 0.76), 0.74)
        scarf_red = material(f"{char_id}_scarf_red", (0.70, 0.07, 0.045), 0.62)
        for side, dx in (("L", -0.15), ("R", 0.15)):
            rim = local_uv(
                f"{char_id}_glasses_{side}", head_pivot,
                (dx, -0.325, 0.06), (0.137, 0.018, 0.153), frame_mat, 24, 12
            )
            # Eye stays slightly in front, giving a dark rim rather than an opaque lens.
            costume_parts.append(rim)
        bridge = local_cube(f"{char_id}_glasses_bridge", head_pivot, (0, -0.392, 0.065), (0.055, 0.014, 0.012), frame_mat, 0.008)
        tilak = local_cube(f"{char_id}_tilak", head_pivot, (0, -0.378, 0.235), (0.027, 0.012, 0.070), tilak_mat, 0.012)
        scarf_l = local_cube(f"{char_id}_scarf_L", root, (-0.25, -0.31, 1.42*h), (0.10, 0.035, 0.58), scarf_mat, 0.025)
        scarf_r = local_cube(f"{char_id}_scarf_R", root, (0.25, -0.31, 1.42*h), (0.10, 0.035, 0.58), scarf_mat, 0.025)
        stripe_l = local_cube(f"{char_id}_scarf_stripe_L", root, (-0.25, -0.35, 1.20*h), (0.105, 0.015, 0.025), scarf_red, 0.008)
        stripe_r = local_cube(f"{char_id}_scarf_stripe_R", root, (0.25, -0.35, 1.20*h), (0.105, 0.015, 0.025), scarf_red, 0.008)
        costume_parts += [bridge, tilak, scarf_l, scarf_r, stripe_l, stripe_r]
    elif char_id == "guddu":
        collar_mat = material(f"{char_id}_collar", (0.035, 0.10, 0.24), 0.56)
        for dx, ang in ((-0.12, -18), (0.12, 18)):
            collar = local_cube(f"{char_id}_collar_{ang}", root, (dx, -0.30, 1.80*h), (0.12, 0.025, 0.075), collar_mat, 0.018)
            collar.rotation_euler.y = math.radians(ang)
            costume_parts.append(collar)
    elif char_id == "bittu":
        chain_mat = material(f"{char_id}_chain", (0.84, 0.62, 0.12), 0.28, 0.25)
        pendant = local_uv(f"{char_id}_pendant", root, (0.0, -0.34, 1.62*h), (0.070, 0.025, 0.085), chain_mat, 18, 9)
        chin = local_uv(f"{char_id}_chin_shadow", head_pivot, (0.0, -0.347, -0.33), (0.19, 0.020, 0.08), hair, 20, 10)
        costume_parts += [pendant, chin]

    eyes = []
    pupils = []
    eye_z = 0.06
    eye_y = -0.342
    for side, dx in [("L", -0.15), ("R", 0.15)]:
        eye = local_uv(
            f"{char_id}_eye_{side}", head_pivot,
            (dx, eye_y, eye_z),
            (0.105, 0.050, 0.122), white, 24, 12
        )
        pupil = local_uv(
            f"{char_id}_pupil_{side}", head_pivot,
            (dx, eye_y - 0.055, eye_z),
            (0.044, 0.017, 0.056), pupil_mat, 20, 10
        )
        eyes.append(eye)
        pupils.append(pupil)

    # Add brows for readable emotion/face direction.
    brows = []
    for side, dx in [("L", -0.15), ("R", 0.15)]:
        brow = local_cube(
            f"{char_id}_brow_{side}", head_pivot,
            (dx, -0.36, 0.235),
            (0.095, 0.014, 0.020), hair, 0.01
        )
        brows.append(brow)

    mouth = local_uv(
        f"{char_id}_mouth", head_pivot,
        (0, -0.365, -0.205),
        (0.145, 0.022, 0.038), mouth_mat, 24, 12
    )

    shoulders = {}
    elbows = {}
    wrists = {}
    hands = []
    arm_parts = []

    for side, sign in [("L", -1), ("R", 1)]:
        shoulder = local_empty(
            f"{char_id}_{side}_SHOULDER", root,
            (sign * float(profile["shoulder_x"]), 0, shoulder_z)
        )
        upper_len = float(profile["upper_arm"]) * h
        lower_len = float(profile["lower_arm"]) * h
        upper = local_segment(
            f"{char_id}_{side}_upper_arm", shoulder,
            upper_len, 0.125 if char_id != "bittu" else 0.14, shirt
        )
        elbow = local_empty(
            f"{char_id}_{side}_ELBOW", shoulder,
            (0, 0, -upper_len)
        )
        lower = local_segment(
            f"{char_id}_{side}_lower_arm", elbow,
            lower_len, 0.105 if char_id != "bittu" else 0.115, skin
        )
        wrist = local_empty(
            f"{char_id}_{side}_WRIST", elbow,
            (0, 0, -lower_len)
        )
        hand = local_uv(
            f"{char_id}_{side}_hand", wrist,
            (0, -0.025, -0.09),
            (0.145, 0.115, 0.155), skin, 22, 11
        )

        # Slight natural rest angle, but all parts remain physically connected.
        shoulder.rotation_euler.y = math.radians(-sign * 7.0)
        elbow.rotation_euler.x = math.radians(-4.0)

        shoulders[side] = shoulder
        elbows[side] = elbow
        wrists[side] = wrist
        hands.append(hand)
        arm_parts += [upper, lower]

    hips = {}
    knees = {}
    leg_parts = []
    for side, sign in [("L", -1), ("R", 1)]:
        hip_joint = local_empty(
            f"{char_id}_{side}_HIP", root,
            (sign * 0.20, 0, 0.94 * h)
        )
        leg_len = float(profile["leg"]) * h
        leg = local_segment(
            f"{char_id}_{side}_leg", hip_joint,
            leg_len, 0.15 if char_id != "bittu" else 0.17, pants
        )
        knee = local_empty(
            f"{char_id}_{side}_KNEE", hip_joint,
            (0, 0, -leg_len)
        )
        foot = local_uv(
            f"{char_id}_{side}_shoe", knee,
            (0, -0.14, -0.07),
            (0.19, 0.31, 0.12), shoe, 22, 11
        )
        hips[side] = hip_joint
        knees[side] = knee
        leg_parts += [leg, foot]

    look_target = create_empty(
        f"{char_id}_LOOK",
        (base[0], base[1] - 4, base[2] + head_z)
    )

    pupil_bases = [p.location.copy() for p in pupils]
    mouth_base_scale = mouth.scale.copy()
    mouth_base_loc = mouth.location.copy()

    return {
        "id": char_id,
        "root": root,
        "torso": torso,
        "hip": hip,
        "head": head_pivot,
        "head_mesh": head_mesh,
        "mouth": mouth,
        "eyes": eyes,
        "eye_scales": [e.scale.copy() for e in eyes],
        "pupils": pupils,
        "pupil_bases": pupil_bases,
        "mouth_base_scale": mouth_base_scale,
        "mouth_base_loc": mouth_base_loc,
        "nose": nose,
        "ears": ears,
        "costume_parts": costume_parts,
        "brows": brows,
        "brow_bases": [b.location.copy() for b in brows],
        "look_target": look_target,
        "hands": hands,
        "shoulders": shoulders,
        "elbows": elbows,
        "wrists": wrists,
        "hips": hips,
        "knees": knees,
        "arms": arm_parts,
        "legs": leg_parts,
        "base": Vector(base),
        "profile": profile,
        "rig_type": "hierarchical_connected_v27",
    }

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        pass



def add_prop(prop_id, location, scale=1.0):
    """Create simple readable 3D props from episode-plan prop ids."""
    prop_id = str(prop_id or "").strip().lower()
    wood = material(f"prop_{prop_id}_wood", (0.34, 0.14, 0.05), 0.72)
    metal = material(f"prop_{prop_id}_metal", (0.18, 0.20, 0.23), 0.35, 0.25)
    dark = material(f"prop_{prop_id}_dark", (0.025, 0.03, 0.04), 0.42)
    glass = material(f"prop_{prop_id}_glass", (0.35, 0.68, 0.82), 0.25)
    bright = material(f"prop_{prop_id}_bright", (0.85, 0.42, 0.08), 0.52)
    green = material(f"prop_{prop_id}_green", (0.12, 0.42, 0.12), 0.72)

    x, y, z = location
    created = []

    if prop_id in {"phone", "mobile", "smartphone", "ai_phone"}:
        hero_scale = 1.22 if prop_id == "ai_phone" else 1.0
        body = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.14),
            (0.13 * hero_scale, 0.035, 0.24 * hero_scale), dark, 0.035
        )
        screen = add_cube(
            f"prop_{prop_id}_screen", (0, 0, 0),
            (0.10 * hero_scale, 0.008, 0.18 * hero_scale), glass, 0.015
        )
        screen.parent = body
        screen.location = (0, -0.043, 0.01)
        created += [body, screen]
        if prop_id == "ai_phone":
            ai_screen_mat = emissive_material(f"prop_{prop_id}_screen_glow", (0.03, 0.24, 0.44), 2.8, 0.20)
            if screen.data.materials:
                screen.data.materials[0] = ai_screen_mat
            else:
                screen.data.materials.append(ai_screen_mat)
            # V6.4 readable AI-BAHU assistant avatar: cyan face + magenta halo + eyes + voice bars.
            cyan = emissive_material(f"prop_{prop_id}_cyan", (0.05, 0.68, 1.00), 4.8, 0.16)
            magenta = emissive_material(f"prop_{prop_id}_magenta", (0.92, 0.08, 0.52), 4.2, 0.18)
            avatar_dark = emissive_material(f"prop_{prop_id}_avatar_dark", (0.005, 0.015, 0.030), 0.8, 0.20)
            halo = add_uv(
                f"prop_{prop_id}_avatar_halo", (0, 0, 0),
                (0.084, 0.010, 0.084), magenta, 20, 10,
            )
            halo.parent = body; halo.location = (0.0, -0.050, 0.022)
            orb = add_uv(
                f"prop_{prop_id}_ai_orb", (0, 0, 0),
                (0.065, 0.012, 0.065), cyan, 20, 10,
            )
            orb.parent = body; orb.location = (0.0, -0.058, 0.022)
            # Face details make the assistant read as a speaking avatar in a 1-2 second cold open.
            for side, dx in (("L", -0.021), ("R", 0.021)):
                eye = add_uv(f"prop_{prop_id}_avatar_eye_{side}", (0,0,0), (0.010,0.005,0.013), avatar_dark, 14, 7)
                eye.parent = body; eye.location = (dx, -0.071, 0.038)
                created.append(eye)
            smile = add_cube(f"prop_{prop_id}_avatar_smile", (0,0,0), (0.028,0.004,0.006), magenta, 0.004)
            smile.parent = body; smile.location = (0.0, -0.071, -0.002)
            smile.rotation_euler.z = math.radians(-4)
            created.append(smile)
            # Three voice bars = instantly readable 'speaking assistant' cue.
            for idx, (dx, hh) in enumerate(((0.073,0.018),(0.084,0.033),(0.095,0.024))):
                bar = add_cube(f"prop_{prop_id}_voicebar_{idx}", (0,0,0), (0.004,0.004,hh), magenta if idx==1 else cyan, 0.003)
                bar.parent = body; bar.location = (dx, -0.069, 0.018)
                created.append(bar)
            created += [halo, orb]
    elif prop_id in {"cup", "tea", "mug"}:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.13*scale, depth=0.24*scale, location=(x, y, z+0.12*scale))
        cup = bpy.context.object
        cup.name = f"prop_{prop_id}"
        cup.data.materials.append(bright)
        created.append(cup)
    elif prop_id in {"bag", "school_bag"}:
        body = add_cube(f"prop_{prop_id}", (x, y, z + 0.28), (0.30, 0.15, 0.36), bright, 0.08)
        created.append(body)
    elif prop_id in {"flower", "flowers", "plant"}:
        stem = add_cylinder(f"prop_{prop_id}_stem", (x, y, z), (x, y, z+0.55), 0.035, green)
        blossom = add_uv(f"prop_{prop_id}_blossom", (x, y, z+0.62), (0.18, 0.18, 0.14), bright)
        created += [stem, blossom]
    elif prop_id in {"broom", "stick"}:
        handle = add_cylinder(
            f"prop_{prop_id}", (x, y, z), (x, y, z+1.2), 0.035, wood
        )
        brush = add_cube(
            f"prop_{prop_id}_brush", (0, 0, 0),
            (0.26, 0.10, 0.08), bright, 0.02
        )
        brush.parent = handle
        brush.location = (0, 0, -0.58)
        created += [handle, brush]
    elif prop_id in {"bucket"}:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.24, depth=0.38, location=(x, y, z+0.19))
        obj = bpy.context.object
        obj.name = f"prop_{prop_id}"
        obj.data.materials.append(metal)
        created.append(obj)
    elif prop_id in {"book", "books"}:
        body = add_cube(f"prop_{prop_id}", (x, y, z + 0.06), (0.26, 0.18, 0.06), bright, 0.02)
        created.append(body)
    elif prop_id in {"ball", "football"}:
        ball = add_uv(f"prop_{prop_id}", (x, y, z+0.18), (0.18,0.18,0.18), bright)
        created.append(ball)
    elif prop_id in {"qr_board", "qr", "payment_qr"}:
        board = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.52),
            (0.34, 0.035, 0.46), material(f"prop_{prop_id}_white", (0.94,0.94,0.91), 0.58), 0.025
        )
        # Readable fake QR pattern: decorative squares, not an actual scannable code.
        for row, col in ((-1,-1),(-1,1),(1,-1),(0,0),(1,1),(-1,0),(0,1)):
            sq = add_cube(
                f"prop_{prop_id}_sq_{row}_{col}", (0,0,0),
                (0.055,0.010,0.055), dark, 0.005
            )
            sq.parent = board
            sq.location = (col*0.095, -0.043, row*0.095)
        created.append(board)
    elif prop_id in {"loudspeaker", "megaphone", "speaker"}:
        bpy.ops.mesh.primitive_cone_add(
            vertices=28, radius1=0.26, radius2=0.11, depth=0.45,
            location=(x, y, z+0.42), rotation=(math.radians(90), 0, 0)
        )
        horn = bpy.context.object
        horn.name = f"prop_{prop_id}"
        horn.data.materials.append(bright)
        handle = add_cube(
            f"prop_{prop_id}_handle", (0,0,0),
            (0.055,0.06,0.16), dark, 0.02
        )
        handle.parent = horn
        handle.location = (0,0.10,-0.18)
        created += [horn, handle]
    elif prop_id in {"kulhad", "clay_cup"}:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=20, radius=0.12*scale, depth=0.20*scale,
            location=(x, y, z+0.10*scale)
        )
        cup = bpy.context.object
        cup.name = f"prop_{prop_id}"
        cup.data.materials.append(wood)
        created.append(cup)
    elif prop_id in {"table_fan", "fan", "jugaad_fan"}:
        stand = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.34),
            (0.18, 0.16, 0.34), metal, 0.06
        )
        rotor = create_empty(f"prop_{prop_id}_rotor", (x, y - 0.03, z + 0.92))
        for idx, angle in enumerate((0, 90, 180, 270)):
            blade = add_cube(
                f"prop_{prop_id}_blade_{idx}", (0, 0, 0),
                (0.055, 0.018, 0.34), bright, 0.025
            )
            blade.parent = rotor
            blade.location = (0, 0, 0.22)
            blade.rotation_euler.y = math.radians(angle)
        hub = add_uv(
            f"prop_{prop_id}_hub", (x, y - 0.05, z + 0.92),
            (0.13, 0.08, 0.13), dark, 18, 9
        )
        created += [stand, rotor, hub]
    elif prop_id in {"ice_bucket", "icebox"}:
        bucket = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.25),
            (0.34, 0.28, 0.25), glass, 0.07
        )
        for idx in range(5):
            cube = add_cube(
                f"prop_{prop_id}_ice_{idx}",
                (x - 0.20 + idx * 0.10, y - 0.02 + (idx % 2) * 0.08, z + 0.56),
                (0.07, 0.07, 0.07), glass, 0.015
            )
            created.append(cube)
        created.append(bucket)
    elif prop_id in {"coin_box", "cash_box", "money_box"}:
        box = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.20),
            (0.28, 0.22, 0.20), bright, 0.05
        )
        slot = add_cube(
            f"prop_{prop_id}_slot", (0, 0, 0),
            (0.10, 0.018, 0.018), dark, 0.005
        )
        slot.parent = box
        slot.location = (0, -0.235, 0.08)
        created += [box, slot]
    elif prop_id in {"matka", "earthen_pot"}:
        pot = add_uv(
            f"prop_{prop_id}", (x, y, z + 0.38),
            (0.32, 0.32, 0.42), material(f"prop_{prop_id}_clay", (0.60,0.25,0.10), 0.80), 22, 11
        )
        created.append(pot)
    elif prop_id in {"extension_board", "power_strip"}:
        board = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.07),
            (0.32, 0.11, 0.07), material(f"prop_{prop_id}_white", (0.90,0.88,0.80), 0.58), 0.025
        )
        for idx in range(3):
            socket = add_uv(
                f"prop_{prop_id}_socket_{idx}",
                (x - 0.16 + idx*0.16, y - 0.12, z + 0.08),
                (0.035,0.015,0.035), dark, 12, 6
            )
            created.append(socket)
        created.append(board)
    elif prop_id in {"gamcha", "towel", "cloth"}:
        cloth = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.72),
            (0.40, 0.025, 0.55), material(f"prop_{prop_id}_cloth", (0.78,0.10,0.08), 0.88), 0.02
        )
        created.append(cloth)
    elif prop_id in {"wedding_card", "wedding_invite", "invite_card"}:
        card_mat = material(f"prop_{prop_id}_card", (0.92, 0.16, 0.22), 0.48)
        gold = material(f"prop_{prop_id}_gold", (0.92, 0.68, 0.14), 0.38, 0.12)
        card = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.23),
            (0.25, 0.025, 0.34), card_mat, 0.018
        )
        band = add_cube(
            f"prop_{prop_id}_band", (0, 0, 0),
            (0.20, 0.008, 0.035), gold, 0.006
        )
        band.parent = card
        band.location = (0, -0.034, 0.02)
        created += [card, band]
    elif prop_id in {"mithai_box", "sweets_box", "sweet_box"}:
        box = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.16),
            (0.31, 0.23, 0.16), material(f"prop_{prop_id}_box", (0.82,0.16,0.08), 0.55), 0.045
        )
        laddu_mat = material(f"prop_{prop_id}_laddu", (0.94,0.52,0.08), 0.62)
        for idx, (dx, dy) in enumerate(((-0.12,-0.06),(0.0,-0.06),(0.12,-0.06),(-0.06,0.06),(0.06,0.06))):
            laddu = add_uv(
                f"prop_{prop_id}_laddu_{idx}", (x+dx, y+dy, z+0.38),
                (0.07,0.07,0.055), laddu_mat, 16, 8
            )
            created.append(laddu)
        created.append(box)
    elif prop_id in {"chair", "wooden_chair"}:
        seat = add_cube(
            f"prop_{prop_id}", (x, y, z + 0.48),
            (0.36, 0.34, 0.07), wood, 0.035
        )
        back = add_cube(
            f"prop_{prop_id}_back", (x, y+0.30, z+0.92),
            (0.34, 0.07, 0.43), wood, 0.035
        )
        created += [seat, back]
        for idx, (dx, dy) in enumerate(((-0.27,-0.24),(0.27,-0.24),(-0.27,0.24),(0.27,0.24))):
            leg = add_cube(
                f"prop_{prop_id}_leg_{idx}", (x+dx, y+dy, z+0.24),
                (0.055,0.055,0.24), wood, 0.018
            )
            created.append(leg)
    elif prop_id in {"garland", "flower_garland"}:
        garland_root = create_empty(f"prop_{prop_id}", (x, y, z + 0.55))
        petal_mat = material(f"prop_{prop_id}_petal", (0.95,0.54,0.06), 0.72)
        for idx in range(9):
            dx = (idx - 4) * 0.075
            dz = -0.035 * abs(idx - 4)
            petal = add_uv(
                f"prop_{prop_id}_petal_{idx}", (x+dx, y, z+0.55+dz),
                (0.055,0.035,0.055), petal_mat, 14, 7
            )
            petal.parent = garland_root
            created.append(petal)
        created.append(garland_root)
    else:
        # Generic prop is intentionally compact instead of silently dropping
        # the plan contract.
        body = add_cube(f"prop_{prop_id or 'object'}", (x, y, z+0.18), (0.20,0.16,0.18), wood, 0.04)
        created.append(body)
    return created



def resolve_world_id(location_id):
    raw = str(location_id or "living_room").strip().lower()
    aliases = {
        "aangan": "courtyard",
        "rasoi": "kitchen",
        "chai_shop": "tea_shop",
        "chai_dukan": "tea_shop",
        "bus_stop": "bus_stand",
        "bazaar": "market",
        "street": "city_street",
        "road": "city_street",
        "room": "bedroom",
        "front_door": "house_entrance",
        "door": "house_entrance",
        "delivery_door": "house_entrance",
        "outdoor_rasoi": "outdoor_kitchen",
        "chaupal": "village_chaupal",
        "gaon_chaupal": "village_chaupal",
        "village_square": "village_chaupal",
        "gaon_gali": "village_lane",
        "village_street": "village_lane",
    }
    if raw in aliases:
        return aliases[raw]

    known = {
        "living_room", "courtyard", "kitchen", "outdoor_kitchen",
        "bedroom", "tea_shop", "school_ground", "school",
        "playground", "bus_stand", "market", "city_street",
        "house_entrance", "dining_room", "garden", "rooftop",
        "village_chaupal", "village_lane",
    }
    if raw in known:
        return raw

    # Semantic fallback instead of silently collapsing unknown worlds to TV/sofa.
    if "chaupal" in raw or "village_square" in raw:
        return "village_chaupal"
    if "village" in raw and ("lane" in raw or "street" in raw or "gali" in raw):
        return "village_lane"
    if "outdoor" in raw and "kitchen" in raw:
        return "outdoor_kitchen"
    if "kitchen" in raw or "cook" in raw:
        return "kitchen"
    if "court" in raw or "aangan" in raw or "yard" in raw:
        return "courtyard"
    if "door" in raw or "entrance" in raw or "delivery" in raw:
        return "house_entrance"
    if "school" in raw or "ground" in raw or "play" in raw:
        return "school_ground"
    if "tea" in raw or "chai" in raw:
        return "tea_shop"
    if "bus" in raw or "stand" in raw:
        return "bus_stand"
    if "market" in raw or "bazaar" in raw or "mela" in raw:
        return "market"
    if "street" in raw or "road" in raw or "city" in raw:
        return "city_street"
    if "bed" in raw or "sleep" in raw:
        return "bedroom"
    if "roof" in raw:
        return "rooftop"
    if "garden" in raw:
        return "garden"
    if "dining" in raw:
        return "dining_room"
    return "living_room"


def environment(location_id, props=None):
    requested = str(location_id or "living_room").strip().lower()
    world_id = resolve_world_id(requested)
    props = [str(x).strip().lower() for x in (props or []) if str(x).strip()]

    floor_m = material("floor", (0.30, 0.24, 0.17), 0.82)
    wall_m = material("wall", (0.76, 0.66, 0.50), 0.88)
    accent_m = material("accent", (0.14, 0.39, 0.23), 0.74)
    accent2_m = material("accent2", (0.66, 0.21, 0.08), 0.70)
    wood_m = material("wood", (0.31, 0.12, 0.042), 0.72)
    road_m = material("road", (0.11, 0.12, 0.14), 0.90)
    grass_m = material("grass", (0.14, 0.38, 0.10), 0.86)
    metal_m = material("metal", (0.20, 0.22, 0.25), 0.42, 0.20)
    tile_m = material("tile", (0.62, 0.58, 0.50), 0.78)
    cloth_m = material("cloth", (0.53, 0.12, 0.18), 0.72)

    if world_id == "village_chaupal":
        mud = material("village_mud", (0.47, 0.30, 0.17), 0.90)
        lime = material("village_lime", (0.82, 0.74, 0.57), 0.86)
        add_cube("chaupal_ground", (0,0,-0.08), (6,5,0.08), mud, 0)
        add_cube("mud_house_back", (0,4.1,1.35), (5.8,0.50,1.45), lime, 0.08)
        add_cube("mud_house_door", (-2.2,3.55,0.95), (0.62,0.10,0.95), wood_m, 0.04)
        # Banyan-style tree + hanging roots.
        add_cylinder("banyan_trunk", (-3.7,2.0,0), (-3.7,2.0,2.45), 0.32, wood_m)
        for ox, oy in ((-3.7,2.0),(-3.1,2.1),(-4.2,2.3)):
            add_uv("banyan_crown", (ox,oy,3.05), (1.25,1.0,0.75), grass_m, 20, 10)
        for rx in (-4.15,-3.75,-3.35):
            add_cylinder("banyan_root", (rx,2.25,0.25), (rx,2.25,1.65), 0.045, wood_m)
        add_cube("chaupal_charpai", (2.4,1.95,0.34), (1.35,0.62,0.10), wood_m, 0.04)
        # Hand pump.
        add_cylinder("handpump_body", (3.8,2.8,0), (3.8,2.8,1.05), 0.13, metal_m)
        add_cylinder("handpump_handle", (3.8,2.8,0.90), (4.45,2.8,1.18), 0.055, metal_m)
        # Earthen water pot.
        pot_m = material("clay_pot", (0.60,0.25,0.10), 0.78)
        add_uv("matka", (2.9,3.0,0.45), (0.34,0.34,0.48), pot_m, 22, 11)

    elif world_id == "village_lane":
        mud = material("lane_mud", (0.50,0.34,0.19), 0.90)
        add_cube("lane_ground", (0,0,-0.08), (6,5,0.08), mud, 0)
        for i, x in enumerate((-4.1, -1.2, 2.0, 4.5)):
            house_m = wall_m if i % 2 else accent2_m
            add_cube(f"lane_house_{i}", (x,3.8,1.25), (1.35,0.55,1.30), house_m, 0.08)
            add_cube(f"lane_door_{i}", (x,3.22,0.82), (0.42,0.07,0.82), wood_m, 0.03)
        add_cylinder("lane_tree_trunk", (-4.7,1.8,0), (-4.7,1.8,2.1), 0.22, wood_m)
        add_uv("lane_tree_crown", (-4.7,1.8,2.65), (0.95,0.8,0.75), grass_m, 18, 9)
        add_cube("lane_bench", (3.4,1.6,0.34), (1.0,0.35,0.10), wood_m, 0.04)

    elif world_id == "courtyard":
        add_cube("courtyard_ground", (0, 0, -0.08), (6.0, 5.0, 0.08), floor_m, 0)
        add_cube("house_wall", (0, 3.6, 1.5), (6.0, 0.10, 1.6), wall_m, 0)
        add_cube("courtyard_door", (-1.5, 3.45, 1.05), (0.65, 0.08, 1.05), wood_m, 0.05)
        for x in (-3.8, 3.7):
            add_cylinder("tree_trunk", (x, 2.4, 0), (x, 2.4, 2.2), 0.22, wood_m)
            add_uv("tree_crown", (x, 2.4, 2.8), (1.0, 0.85, 0.8), grass_m)
        add_cube("charpai", (2.7, 1.8, 0.35), (1.2, 0.55, 0.10), wood_m, 0.04)
        # V6.2 Kanpuri home cues: more depth/identity without external assets.
        window_m = material("courtyard_window_dark", (0.08, 0.10, 0.11), 0.48)
        clay_m = material("courtyard_clay", (0.58, 0.23, 0.075), 0.82)
        plant_m = material("courtyard_plant", (0.10, 0.36, 0.08), 0.84)
        wire_m = material("courtyard_wire", (0.045, 0.04, 0.035), 0.54)
        meter_m = material("courtyard_meter", (0.70, 0.72, 0.67), 0.62)
        add_cube("courtyard_window", (1.45, 3.44, 1.75), (0.72, 0.07, 0.55), window_m, 0.035)
        for bar_x in (0.95, 1.45, 1.95):
            add_cube(f"courtyard_window_bar_{bar_x}", (bar_x, 3.35, 1.75), (0.025, 0.025, 0.52), metal_m, 0.008)
        add_uv("courtyard_matka", (-3.05, 2.65, 0.43), (0.34, 0.34, 0.46), clay_m, 22, 11)
        add_cube("courtyard_meter", (-4.55, 3.40, 1.78), (0.22, 0.07, 0.31), meter_m, 0.025)
        add_cylinder("courtyard_meter_wire", (-4.55,3.30,2.08), (-4.10,3.30,2.80), 0.018, wire_m)
        add_cylinder("courtyard_clothesline", (-4.35,2.95,2.35), (4.25,2.95,2.25), 0.012, wire_m)
        cloth_colors = [cloth_m, accent2_m, accent_m]
        for idx, x in enumerate((-2.4, -0.8, 0.9)):
            cloth = add_cube(f"courtyard_cloth_{idx}", (x,2.91,1.95), (0.34,0.025,0.30), cloth_colors[idx], 0.018)
            cloth.rotation_euler.y = math.radians((-1 if idx % 2 else 1) * 4)
        for idx, x in enumerate((-4.4, 4.25)):
            pot = add_uv(f"courtyard_plant_pot_{idx}", (x,2.8,0.26), (0.25,0.25,0.28), clay_m, 18, 9)
            add_uv(f"courtyard_plant_leaf_{idx}", (x,2.8,0.72), (0.38,0.30,0.48), plant_m, 18, 9)
        # small stepping stones provide foreground parallax in camera pushes.
        for idx, (x,y) in enumerate(((-2.3,0.1),(-1.1,0.45),(0.2,0.15),(1.45,0.55),(2.65,0.20))):
            add_uv(f"courtyard_step_{idx}", (x,y,0.015), (0.38,0.24,0.035), tile_m, 14, 7)

    elif world_id == "outdoor_kitchen":
        add_cube("outdoor_kitchen_ground", (0, 0, -0.08), (6, 5, 0.08), floor_m, 0)
        add_cube("outdoor_kitchen_wall", (0, 3.7, 1.4), (6, 0.10, 1.5), wall_m, 0)
        add_cube("outdoor_counter", (1.6, 2.55, 0.72), (2.1, 0.55, 0.18), tile_m, 0.06)
        add_cube("outdoor_shelf", (-3.1, 2.8, 1.45), (1.0, 0.35, 0.08), wood_m, 0.03)
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=24, radius=0.42, depth=0.32, location=(-0.6, 2.35, 0.22)
        )
        chulha = bpy.context.object
        chulha.name = "outdoor_chulha"
        chulha.data.materials.append(accent2_m)
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=24, radius=0.28, depth=0.26, location=(-0.6, 2.35, 0.56)
        )
        pot = bpy.context.object
        pot.name = "cooking_pot"
        pot.data.materials.append(metal_m)
        add_cube("awning", (0.4, 2.9, 2.8), (3.5, 1.0, 0.10), cloth_m, 0.03)

    elif world_id == "kitchen":
        add_cube("kitchen_floor", (0, 0, -0.08), (6,5,0.08), tile_m, 0)
        add_cube("kitchen_back_wall", (0,3.4,1.8), (6,0.10,1.9), wall_m, 0)
        add_cube("counter", (0,2.75,0.72), (3.2,0.55,0.18), accent_m, 0.08)
        add_cube("cabinet_left", (-3.9,2.9,1.4), (0.9,0.45,1.25), wood_m, 0.05)
        add_cube("stove", (1.6,2.18,0.94), (0.65,0.48,0.10), metal_m, 0.04)
        add_cube("fridge", (4.2,2.8,1.35), (0.75,0.52,1.35), metal_m, 0.06)

    elif world_id == "bedroom":
        add_cube("bedroom_floor", (0,0,-0.08), (6,5,0.08), floor_m, 0)
        add_cube("bedroom_wall", (0,3.4,1.8), (6,0.10,1.9), wall_m, 0)
        add_cube("bed", (-2.1,2.0,0.42), (1.55,1.0,0.28), accent_m, 0.16)
        add_cube("pillow", (-2.1,2.55,0.80), (0.65,0.35,0.14), wall_m, 0.12)
        add_cube("wardrobe", (3.7,2.8,1.5), (0.9,0.50,1.5), wood_m, 0.06)

    elif world_id == "tea_shop":
        add_cube("tea_shop_ground", (0,0,-0.08), (6,5,0.08), floor_m, 0)
        add_cube("shop_back", (0,3.4,1.5), (5.5,0.12,1.6), wall_m, 0)
        add_cube("tea_counter", (0,1.9,0.65), (2.4,0.48,0.65), wood_m, 0.08)
        bpy.ops.mesh.primitive_uv_sphere_add(location=(1.0,1.35,1.25), segments=24, ring_count=12)
        kettle = bpy.context.object
        kettle.name = "tea_kettle"
        kettle.scale = (0.32,0.25,0.30)
        kettle.data.materials.append(metal_m)
        add_cube("bench", (-2.8,0.8,0.35), (1.2,0.35,0.12), wood_m, 0.04)
        add_cube("tea_sign", (0,3.20,2.25), (1.5,0.05,0.30), accent2_m, 0.03)
        add_cylinder("tea_tree_trunk", (-4.2,2.4,0), (-4.2,2.4,2.1), 0.22, wood_m)
        add_uv("tea_tree_crown", (-4.2,2.4,2.65), (1.0,0.85,0.72), grass_m, 18, 9)
        for j in range(4):
            bpy.ops.mesh.primitive_cylinder_add(vertices=18, radius=0.09, depth=0.16, location=(-0.55+j*0.35,1.34,0.95))
            kulhad = bpy.context.object
            kulhad.name = f"tea_kulhad_{j}"
            kulhad.data.materials.append(wood_m)

    elif world_id in {"school_ground", "school", "playground"}:
        add_cube("school_grass", (0,0,-0.08), (6,5,0.08), grass_m, 0)
        add_cube("school_building", (0,4.0,1.4), (5.4,0.7,1.5), wall_m, 0.03)
        add_cube("school_door", (0,3.28,1.0), (0.7,0.06,1.0), wood_m, 0.03)
        for x in (-3.6, 3.6):
            add_cylinder("goal_post", (x,2.0,0), (x,2.0,1.7), 0.045, metal_m)
        add_cylinder("goal_bar", (-3.6,2.0,1.7), (3.6,2.0,1.7), 0.045, metal_m)

    elif world_id == "bus_stand":
        add_cube("bus_ground", (0,0,-0.08), (6,5,0.08), road_m, 0)
        add_cube("sidewalk", (0,1.8,0.02), (6,1.0,0.10), floor_m, 0)
        add_cube("shelter_roof", (0,2.2,2.25), (2.8,0.8,0.10), metal_m, 0.03)
        for x in (-2.5,2.5):
            add_cylinder("shelter_post", (x,2.2,0), (x,2.2,2.2), 0.06, metal_m)
        add_cube("bus_bench", (0,2.2,0.42), (1.5,0.28,0.12), wood_m, 0.04)
        add_cube("bus_sign", (3.3,2.0,1.6), (0.35,0.06,0.55), accent2_m, 0.03)

    elif world_id == "market":
        add_cube("market_ground", (0,0,-0.08), (6,5,0.08), floor_m, 0)
        for i, x in enumerate((-3.6, 0, 3.6)):
            add_cube(f"stall_{i}", (x,2.6,0.75), (1.2,0.55,0.75), wood_m, 0.05)
            add_cube(f"awning_{i}", (x,2.55,1.75), (1.4,0.85,0.12), accent2_m if i%2 else accent_m, 0.03)
            for j in range(3):
                add_uv(
                    f"market_item_{i}_{j}",
                    (x - 0.55 + j * 0.55, 2.0, 1.0),
                    (0.14,0.14,0.14), accent2_m if j%2 else accent_m, 16, 8
                )

    elif world_id == "city_street":
        add_cube("road", (0,0,-0.08), (6,5,0.08), road_m, 0)
        add_cube("left_sidewalk", (-4.8,0,0.03), (1.1,5,0.11), floor_m, 0)
        add_cube("right_sidewalk", (4.8,0,0.03), (1.1,5,0.11), floor_m, 0)
        add_cube("building_left", (-4.2,3.5,1.7), (1.5,0.8,1.8), wall_m, 0.05)
        add_cube("building_right", (4.2,3.5,1.7), (1.5,0.8,1.8), accent_m, 0.05)
        for x in (-4.7,4.7):
            add_cylinder("street_lamp", (x,1.5,0), (x,1.5,3.2), 0.055, metal_m)
            add_uv("street_lamp_head", (x,1.5,3.25), (0.20,0.20,0.12), accent2_m)

    elif world_id == "house_entrance":
        add_cube("entrance_ground", (0,0,-0.08), (6,5,0.08), floor_m, 0)
        add_cube("house_front", (0,3.7,1.6), (6,0.12,1.7), wall_m, 0)
        add_cube("front_door", (0.4,3.52,1.05), (0.85,0.08,1.05), wood_m, 0.05)
        add_cube("door_step", (0.4,2.9,0.12), (1.1,0.55,0.12), tile_m, 0.04)
        add_uv("door_plant", (-2.1,2.8,0.55), (0.40,0.40,0.70), grass_m, 20, 10)

    elif world_id == "dining_room":
        add_cube("dining_floor", (0,0,-0.08), (6,5,0.08), floor_m, 0)
        add_cube("dining_wall", (0,3.5,1.8), (6,0.10,1.9), wall_m, 0)
        add_cube("dining_table", (0,1.7,0.65), (1.8,0.9,0.12), wood_m, 0.06)
        for x in (-2.4,2.4):
            add_cube("dining_chair", (x,1.7,0.45), (0.45,0.45,0.45), accent_m, 0.06)

    elif world_id == "garden":
        add_cube("garden_ground", (0,0,-0.08), (6,5,0.08), grass_m, 0)
        for x in (-3, -1, 1, 3):
            add_uv("garden_bush", (x,2.6,0.55), (0.55,0.45,0.55), grass_m, 18, 9)
        add_cube("garden_path", (0,0.5,0.0), (1.0,4.0,0.05), tile_m, 0)

    elif world_id == "rooftop":
        add_cube("roof_floor", (0,0,-0.08), (6,5,0.08), tile_m, 0)
        for x in (-5.5,5.5):
            add_cube("roof_parapet", (x,0,0.55), (0.18,5,0.55), wall_m, 0)
        add_cube("water_tank", (3.5,2.5,1.1), (0.8,0.8,1.1), metal_m, 0.08)

    else:  # living_room
        add_cube("living_floor", (0,0,-0.08), (6,5,0.08), floor_m, 0)
        add_cube("living_back_wall", (0,3.4,1.8), (6,0.10,1.9), wall_m, 0)
        add_cube("living_left_wall", (-5.9,0,1.8), (0.10,3.5,1.9), wall_m, 0)
        add_cube("sofa", (2.4,2.6,0.55), (1.45,0.55,0.45), accent_m, 0.16)
        add_cube("table", (2.7,1.35,0.48), (0.65,0.55,0.10), wood_m, 0.04)
        add_cube("tv_unit", (-3.7,2.9,0.55), (1.05,0.35,0.55), wood_m, 0.05)
        add_cube("tv_screen", (-3.7,2.52,1.55), (0.85,0.05,0.62), road_m, 0.04)
        add_uv("living_plant", (4.5,2.5,0.75), (0.45,0.45,0.75), grass_m, 18, 9)

    # Keep props in visible action zone but away from actors' feet.
    for i, prop in enumerate(props[:6]):
        x = -2.2 + (i % 4) * 1.25
        y = 1.55 + (i // 4) * 0.55
        add_prop(prop, (x, y, 0.0), 1.0)

    add_world_dressing(world_id)

    # Three-point lighting with a little more depth.
    bpy.ops.object.light_add(type="AREA", location=(0, -2.8, 5.8))
    key_light = bpy.context.object
    key_light.name = "KeyLight"
    key_light.data.energy = 1250
    key_light.data.shape = "DISK"
    key_light.data.size = 4.2
    _aim_object_at(key_light, (0.0, 0.65, 1.45))

    bpy.ops.object.light_add(type="AREA", location=(4.5, -0.6, 3.4))
    fill_light = bpy.context.object
    fill_light.name = "FillLight"
    fill_light.data.energy = 420
    fill_light.data.size = 3.8
    _aim_object_at(fill_light, (0.2, 0.75, 1.35))

    bpy.ops.object.light_add(type="AREA", location=(-4.2, 2.7, 4.2))
    rim_light = bpy.context.object
    rim_light.name = "RimLight"
    rim_light.data.energy = 820
    rim_light.data.size = 2.8
    _aim_object_at(rim_light, (0.0, 0.9, 1.65))

    if world_id in {"courtyard", "house_entrance", "rooftop", "garden", "village_lane", "village_chaupal"}:
        bpy.ops.object.light_add(type="SUN", location=(0, 0, 5.5))
        sun = bpy.context.object
        sun.name = "WarmSun"
        sun.data.energy = 1.4
        sun.rotation_euler = (math.radians(28), math.radians(-18), math.radians(-32))

    world = bpy.context.scene.world
    if world and world.node_tree:
        bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg:
            bg.inputs["Color"].default_value = (0.055, 0.070, 0.095, 1.0)
            bg.inputs["Strength"].default_value = 0.42

    print(
        f"[WORLD ROUTER] requested={requested} resolved={world_id} "
        f"semantic_match={'YES' if requested == world_id or resolve_world_id(requested) == world_id else 'FALLBACK'}"
    )
    return world_id



def add_world_dressing(world_id):
    """V4.0 lightweight depth dressing so locations read as worlds, not stages.

    Everything is procedural and Eevee-friendly: no external textures/assets, so the
    patch stays portable on the existing Mac workflow.
    """
    world_id = str(world_id or "living_room")
    outdoor = {
        "village_chaupal", "village_lane", "courtyard", "outdoor_kitchen",
        "tea_shop", "school_ground", "school", "playground", "bus_stand",
        "market", "city_street", "house_entrance", "garden", "rooftop",
    }
    earth = material("dress_earth", (0.36, 0.23, 0.13), 0.94)
    leaf = material("dress_leaf", (0.10, 0.30, 0.075), 0.90)
    bark = material("dress_bark", (0.25, 0.105, 0.035), 0.84)
    stone = material("dress_stone", (0.34, 0.33, 0.30), 0.94)
    warm = material("dress_warm", (0.62, 0.28, 0.07), 0.82)
    pale = material("dress_pale", (0.78, 0.68, 0.50), 0.90)
    dark = material("dress_dark", (0.10, 0.08, 0.06), 0.82)

    events = 0
    if world_id in outdoor:
        # Background tree clusters establish depth behind the actors.
        for idx, (x, y, h, scale) in enumerate((
            (-5.1, 4.45, 2.35, 0.82),
            (-2.7, 4.65, 2.05, 0.67),
            (2.8, 4.55, 2.20, 0.74),
            (5.15, 4.35, 2.55, 0.88),
        )):
            add_cylinder(f"dress_tree_trunk_{idx}", (x, y, 0), (x, y, h), 0.13, bark)
            add_uv(
                f"dress_tree_crown_{idx}",
                (x, y, h + 0.48),
                (scale, scale * 0.76, scale * 0.66),
                leaf,
                18,
                9,
            )
            events += 2

        # Ground breakup: stones/patches stop the floor reading as one flat card.
        for idx, (x, y, sx, sy) in enumerate((
            (-4.3, 1.0, 0.24, 0.14), (-2.7, 2.2, 0.18, 0.11),
            (-0.8, 3.0, 0.22, 0.13), (1.4, 2.45, 0.17, 0.10),
            (3.2, 1.25, 0.25, 0.14), (4.3, 3.05, 0.19, 0.12),
        )):
            pebble = add_uv(
                f"dress_ground_mark_{idx}", (x, y, 0.015),
                (sx, sy, 0.035), stone if idx % 2 else earth, 14, 7
            )
            pebble.rotation_euler.z = math.radians(idx * 19)
            events += 1

        # Side-depth objects intentionally stay outside the central acting lane.
        add_cube("dress_left_crate", (-4.7, 2.05, 0.28), (0.48, 0.40, 0.28), warm, 0.06)
        add_cube("dress_right_pot", (4.65, 2.15, 0.30), (0.34, 0.34, 0.30), warm, 0.09)
        events += 2
    else:
        # Indoor depth: rug + wall frames + side furniture create foreground/mid/background layers.
        add_cube("dress_rug", (0.0, 0.85, 0.006), (2.55, 1.35, 0.012), warm, 0.02)
        for idx, x in enumerate((-2.4, 0.0, 2.4)):
            add_cube(
                f"dress_wall_frame_{idx}", (x, 3.25, 2.15),
                (0.42, 0.035, 0.32), pale if idx % 2 else warm, 0.025
            )
        add_cube("dress_side_stool", (-4.35, 2.05, 0.38), (0.48, 0.42, 0.38), dark, 0.06)
        add_uv("dress_side_plant", (4.35, 2.25, 0.62), (0.45, 0.38, 0.65), leaf, 18, 9)
        events += 6

    print(f"[WORLD DRESSING V4] world={world_id} detail_objects={events}")
    return events

def _aim_object_at(obj, target=(0.0, 0.7, 1.45), track_axis="-Z", up_axis="Y"):
    direction = Vector(target) - obj.location
    if direction.length > 1e-6:
        obj.rotation_euler = direction.to_track_quat(track_axis, up_axis).to_euler()
    return obj


def _new_camera(name, location, target_location, lens=50):
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.object
    camera.name = name
    camera.data.lens = lens
    camera.data.sensor_width = 36
    target = create_empty(f"{name}_TARGET", target_location)
    c = camera.constraints.new(type="DAMPED_TRACK")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    return camera, target


def _bind_camera(scene, camera, frame, name):
    marker = scene.timeline_markers.new(name, frame=max(1, int(frame)))
    marker.camera = camera
    return marker


def setup_camera():
    camera, target = _new_camera(
        "CartoonCamera_EST",
        (0, -11.4, 3.05),
        (0, 0.65, 1.55),
        lens=48,
    )
    bpy.context.scene.camera = camera
    _bind_camera(bpy.context.scene, camera, 1, "ESTABLISHING")
    return camera, target


def camera_for_scene(camera, target, scene, frame, width_factor=1.0):
    kind = str(scene.get("camera") or "medium_two_shot")
    variant = str(scene.get("environment_variant") or "")
    if "close" in kind:
        loc = (0.9 if scene.get("id", 0) % 2 else -0.9, -8.3, 2.65)
        target.location = (0, 0.35, 1.95)
        camera.data.lens = 56
    elif "wide" in kind or variant == "establishing":
        loc = (0, -12.0, 3.25)
        target.location = (0, 0.9, 1.50)
        camera.data.lens = 45
    else:
        shift = -0.45 if "left" in variant else (0.45 if "right" in variant else 0.0)
        loc = (shift, -10.4, 2.9)
        target.location = (shift * 0.25, 0.55, 1.55)
        camera.data.lens = 48

    camera.location = loc
    camera.keyframe_insert("location", frame=frame)
    camera.data.keyframe_insert("lens", frame=frame)
    target.keyframe_insert("location", frame=frame)

    # Safe, subtle establishing push.
    camera.location.y += 0.18
    camera.keyframe_insert("location", frame=frame + 18)

def key(obj, prop, frame):
    obj.keyframe_insert(prop, frame=frame)




def _key_rotation(obj, frame):
    key(obj, "rotation_euler", frame)


def _arm_rest(actor, side, frame):
    sign = -1 if side == "L" else 1
    shoulder = actor["shoulders"][side]
    elbow = actor["elbows"][side]
    shoulder.rotation_euler = (0.0, math.radians(-sign * 7.0), 0.0)
    elbow.rotation_euler = (math.radians(-4.0), 0.0, 0.0)
    _key_rotation(shoulder, frame)
    _key_rotation(elbow, frame)


def animate_arm_pose(actor, action, start_frame, end_frame, fps, side="R"):
    """Move shoulder+elbow joints, never the hand independently."""
    shoulder = actor["shoulders"][side]
    elbow = actor["elbows"][side]
    sign = -1 if side == "L" else 1
    mid = min(end_frame, start_frame + max(3, int(0.28 * fps)))
    hold = max(mid + 1, end_frame - max(2, int(0.18 * fps)))

    _arm_rest(actor, side, start_frame)

    action = str(action or "idle").lower()
    if action in {"pointing", "point", "give", "show", "use"}:
        shoulder.rotation_euler = (
            math.radians(-52), math.radians(-sign * 12), math.radians(sign * 3)
        )
        elbow.rotation_euler = (math.radians(-24), 0.0, 0.0)
    elif action in {"phone_use", "phone", "thinking", "confused", "facepalm", "whisper"}:
        shoulder.rotation_euler = (
            math.radians(-58), math.radians(-sign * 10), math.radians(sign * 4)
        )
        elbow.rotation_euler = (math.radians(-62), 0.0, math.radians(sign * 3))
    elif action in {"drink"}:
        shoulder.rotation_euler = (
            math.radians(-62), math.radians(-sign * 8), 0.0
        )
        elbow.rotation_euler = (math.radians(-72), 0.0, 0.0)
    elif action in {"carry"}:
        shoulder.rotation_euler = (
            math.radians(-42), math.radians(-sign * 7), 0.0
        )
        elbow.rotation_euler = (math.radians(-42), 0.0, 0.0)
    else:
        shoulder.rotation_euler = (
            math.radians(-30), math.radians(-sign * 8), 0.0
        )
        elbow.rotation_euler = (math.radians(-18), 0.0, 0.0)

    _key_rotation(shoulder, mid)
    _key_rotation(elbow, mid)
    _key_rotation(shoulder, hold)
    _key_rotation(elbow, hold)
    _arm_rest(actor, side, end_frame)
    return 8


def pose_actor(actor, pose, frame, fps):
    root = actor["root"]
    head = actor["head"]
    pose = str(pose or "idle").lower()
    end = frame + max(6, int(0.9 * fps))

    if pose in {"pointing", "give", "show", "use", "phone_use"}:
        animate_arm_pose(actor, pose, frame, end, fps, "R")
    elif pose in {"thinking", "confused", "facepalm"}:
        animate_arm_pose(actor, "facepalm" if pose == "facepalm" else "thinking", frame, end, fps, "R")
        head.rotation_euler.x = math.radians(-5.0)
        _key_rotation(head, frame + max(2, fps // 3))
    elif pose in {"shocked", "angry"}:
        for side in ("L", "R"):
            shoulder = actor["shoulders"][side]
            sign = -1 if side == "L" else 1
            _arm_rest(actor, side, frame)
            shoulder.rotation_euler = (
                math.radians(-18), math.radians(-sign * 28), math.radians(sign * 8)
            )
            _key_rotation(shoulder, frame + max(2, fps // 4))
            _arm_rest(actor, side, end)
        root.rotation_euler.x = math.radians(-4.0)
        _key_rotation(root, frame)
        root.rotation_euler.x = math.radians(3.0)
        _key_rotation(root, frame + max(2, int(0.35 * fps)))
    elif pose in {"laughing", "happy", "proud", "smirk"}:
        z = root.location.z
        root.location.z = z
        key(root, "location", frame)
        root.location.z = z + 0.055
        key(root, "location", frame + max(2, int(0.28 * fps)))
        root.location.z = z
        key(root, "location", frame + max(4, int(0.62 * fps)))

    # Stronger speaking head beat, preserving Z yaw used for partner-facing.
    base_x = head.rotation_euler.x
    head.rotation_euler.x = math.radians(-3.5)
    _key_rotation(head, frame)
    head.rotation_euler.x = math.radians(4.5)
    _key_rotation(head, frame + max(2, int(0.34 * fps)))
    head.rotation_euler.x = base_x
    _key_rotation(head, frame + max(4, int(0.76 * fps)))


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def animate_visible_gaze(actor, partner, start_frame, end_frame, fps):
    """V4.0 true partner-facing: pupils + head + clearly visible torso yaw."""
    dx = float(partner["base"].x - actor["base"].x)
    dy = float(partner["base"].y - actor["base"].y)
    side = _clamp(dx / 1.8, -1.0, 1.0)
    depth = _clamp(dy / 1.5, -1.0, 1.0)

    # Characters are modelled facing -Y. Solve the actual partner direction,
    # then split it between torso and head so the body does not stay front-on.
    desired_yaw = math.atan2(dx, -dy)
    max_body = math.radians(34.0)
    body_yaw = _clamp(desired_yaw, -max_body, max_body)
    head_residual = _clamp(
        desired_yaw - body_yaw,
        math.radians(-22.0),
        math.radians(22.0),
    )

    pupil_keys = 0
    settle = min(end_frame, start_frame + max(3, int(0.24 * fps)))
    hold = max(settle + 1, end_frame - max(1, int(0.08 * fps)))
    for pupil, base in zip(actor["pupils"], actor["pupil_bases"]):
        pupil.location = base.copy()
        key(pupil, "location", start_frame)
        pupil.location.x = base.x + (0.085 * side)
        pupil.location.z = base.z + (0.020 * depth)
        key(pupil, "location", settle)
        key(pupil, "location", hold)
        pupil_keys += 3

    root = actor["root"]
    head = actor["head"]

    root.rotation_euler.z = body_yaw * 0.45
    _key_rotation(root, start_frame)
    root.rotation_euler.z = body_yaw
    _key_rotation(root, settle)
    _key_rotation(root, hold)

    head.rotation_euler.z = head_residual * 0.45
    _key_rotation(head, start_frame)
    head.rotation_euler.z = head_residual
    _key_rotation(head, settle)
    _key_rotation(head, hold)

    return {"pupil": pupil_keys, "body": 3, "head": 3}


def animate_dialogue_blocking(speaker, listener, start_frame, end_frame, fps, turn_index):
    """V6.4 readable dialogue blocking: real step/lean/torso travel, not micro-shifts."""
    if listener is None or end_frame <= start_frame:
        return 0
    root = speaker["root"]
    base = speaker["base"]
    target = listener["base"]
    dx = float(target.x - base.x); dy = float(target.y - base.y)
    length = max(0.001, math.sqrt(dx * dx + dy * dy))
    # 45-62cm travel is visible even in group coverage, while remaining safe inside the set.
    step = 0.62 if turn_index % 2 else 0.46
    ux, uy = dx / length, dy / length
    approach = min(end_frame, start_frame + max(6, int(0.40 * fps)))
    hold = max(approach + 1, end_frame - max(5, int(0.30 * fps)))
    recover = end_frame
    desired_yaw = math.atan2(dx, -dy)
    body_yaw = _clamp(desired_yaw, math.radians(-38), math.radians(38))

    root.location = Vector((base.x, base.y, base.z)); key(root, "location", start_frame)
    root.rotation_euler.x = 0.0; _key_rotation(root, start_frame)
    root.location = Vector((base.x + ux * step, base.y + uy * step, base.z + 0.045)); key(root, "location", approach)
    root.rotation_euler.x = math.radians(-5.5)
    root.rotation_euler.z = body_yaw
    _key_rotation(root, approach)
    key(root, "location", hold); _key_rotation(root, hold)
    # Do not snap fully back: retain 28% of travel through the end of the turn.
    root.location = Vector((base.x + ux * step * 0.28, base.y + uy * step * 0.28, base.z)); key(root, "location", recover)
    root.rotation_euler.x = 0.0
    root.rotation_euler.z = body_yaw * 0.35
    _key_rotation(root, recover)
    return 8

def animate_idle_life(actor, start_frame, end_frame, fps):
    root = actor["root"]
    head = actor["head"]
    span = max(6, end_frame - start_frame)
    q1 = start_frame + span // 3
    q2 = start_frame + (span * 2) // 3

    base_z = root.location.z
    base_x = root.location.x

    root.location.z = base_z
    root.location.x = base_x
    key(root, "location", start_frame)

    root.location.z = base_z + 0.035
    root.location.x = base_x + 0.025
    key(root, "location", q1)

    root.location.z = base_z + 0.008
    root.location.x = base_x - 0.022
    key(root, "location", q2)

    root.location.z = base_z
    root.location.x = base_x
    key(root, "location", end_frame)

    # Small head tilt adds life between larger partner turns.
    current_z = head.rotation_euler.z
    head.rotation_euler.y = math.radians(-2.5)
    _key_rotation(head, q1)
    head.rotation_euler.y = math.radians(2.0)
    _key_rotation(head, q2)
    head.rotation_euler.y = 0.0
    head.rotation_euler.z = current_z
    _key_rotation(head, end_frame)
    return 7


def animate_listener_reaction(actor, start_frame, end_frame, fps, emotion="neutral"):
    root = actor["root"]
    head = actor["head"]
    mid = (start_frame + end_frame) // 2
    emotion = str(emotion or "neutral").lower()

    nod = -5.5 if emotion == "shocked" else 5.0
    lean = 2.5 if emotion not in {"angry", "shocked"} else -3.0

    head.rotation_euler.x = 0.0
    _key_rotation(head, start_frame)
    head.rotation_euler.x = math.radians(nod)
    _key_rotation(head, mid)
    head.rotation_euler.x = 0.0
    _key_rotation(head, end_frame)

    root.rotation_euler.x = 0.0
    _key_rotation(root, start_frame)
    root.rotation_euler.x = math.radians(lean)
    _key_rotation(root, mid)
    root.rotation_euler.x = 0.0
    _key_rotation(root, end_frame)

    # Listener hand reaction every few turns.
    animate_arm_pose(
        actor,
        "thinking" if emotion in {"confused", "serious"} else "show",
        start_frame,
        end_frame,
        fps,
        "L",
    )
    return 14


def animate_face_emotion(actor, emotion, start_frame, end_frame, fps):
    """V6.4 exaggerated comedy expressions with clearly different silhouettes."""
    emotion = str(emotion or "neutral").lower()
    brows = actor.get("brows") or []
    eyes = actor.get("eyes") or []
    pupils = actor.get("pupils") or []
    eye_scales = actor.get("eye_scales") or [e.scale.copy() for e in eyes]
    pupil_bases = actor.get("pupil_bases") or [p.location.copy() for p in pupils]
    mouth = actor["mouth"]
    head = actor["head"]
    mid = min(end_frame, start_frame + max(2, int(0.20 * fps)))
    settle = min(end_frame, mid + max(3, int(0.28 * fps)))

    brow_bases = actor.get("brow_bases") or [b.location.copy() for b in brows]
    mouth_base_scale = actor.get("mouth_base_scale") or mouth.scale.copy()
    mouth_base_loc = actor.get("mouth_base_loc") or mouth.location.copy()
    for brow, brow_base in zip(brows, brow_bases):
        brow.location = brow_base.copy(); key(brow, "location", start_frame)
        brow.rotation_euler = (0.0, 0.0, 0.0); _key_rotation(brow, start_frame)
    mouth.scale = mouth_base_scale.copy(); key(mouth, "scale", start_frame)
    mouth.location = mouth_base_loc.copy(); key(mouth, "location", start_frame)
    mouth.rotation_euler.z = 0.0; _key_rotation(mouth, start_frame)
    for eye, base in zip(eyes, eye_scales):
        eye.scale = base.copy(); key(eye, "scale", start_frame)
    for pupil, base in zip(pupils, pupil_bases):
        pupil.location = base.copy(); key(pupil, "location", start_frame)

    if emotion in {"angry", "serious", "annoyed"}:
        for i, brow in enumerate(brows):
            sign = -1 if i == 0 else 1
            brow.rotation_euler.z = math.radians(sign * 44.0); brow.location.z -= 0.038
            _key_rotation(brow, mid); key(brow, "location", mid)
        for eye, base in zip(eyes, eye_scales):
            eye.scale = Vector((base.x * 1.12, base.y, base.z * 0.46)); key(eye, "scale", mid)
        mouth.scale = Vector((mouth_base_scale.x * 1.55, mouth_base_scale.y, max(0.58, mouth_base_scale.z * 0.58)))
        head.rotation_euler.x = math.radians(11.0); _key_rotation(head, mid)
    elif emotion in {"confused", "thinking"}:
        if len(brows) >= 2:
            brows[0].rotation_euler.z = math.radians(-34); brows[0].location.z += 0.050
            brows[1].rotation_euler.z = math.radians(22); brows[1].location.z -= 0.022
            _key_rotation(brows[0], mid); key(brows[0], "location", mid)
            _key_rotation(brows[1], mid); key(brows[1], "location", mid)
        for i, (pupil, base) in enumerate(zip(pupils, pupil_bases)):
            pupil.location.x = base.x + (0.070 if i == 0 else 0.050); key(pupil, "location", mid)
        mouth.rotation_euler.z = math.radians(10); _key_rotation(mouth, mid)
        mouth.scale = Vector((mouth_base_scale.x * 1.20, mouth_base_scale.y, mouth_base_scale.z * 0.82))
        head.rotation_euler.y = math.radians(9); head.rotation_euler.z += math.radians(9); _key_rotation(head, mid)
    elif emotion in {"shocked", "surprised"}:
        for brow in brows:
            brow.location.z += 0.155; key(brow, "location", mid)
        for eye, base in zip(eyes, eye_scales):
            eye.scale = Vector((base.x * 1.62, base.y, base.z * 1.72)); key(eye, "scale", mid)
        for pupil, base in zip(pupils, pupil_bases):
            pupil.location = base.copy(); key(pupil, "location", mid)
        mouth.scale = Vector((mouth_base_scale.x * 1.18, mouth_base_scale.y, max(4.10, mouth_base_scale.z * 4.10)))
        mouth.location.z = mouth_base_loc.z - 0.055; key(mouth, "location", mid)
        head.rotation_euler.x = math.radians(-16); _key_rotation(head, mid)
    elif emotion in {"laughing", "happy", "excited"}:
        for i, brow in enumerate(brows):
            sign = -1 if i == 0 else 1
            brow.rotation_euler.z = math.radians(-sign * 16.0); brow.location.z += 0.035
            _key_rotation(brow, mid); key(brow, "location", mid)
        for eye, base in zip(eyes, eye_scales):
            eye.scale = Vector((base.x * 1.08, base.y, base.z * 0.76)); key(eye, "scale", mid)
        mouth.scale = Vector((mouth_base_scale.x * 1.90, mouth_base_scale.y, max(1.70, mouth_base_scale.z * 1.70)))
        head.rotation_euler.x = math.radians(-6); _key_rotation(head, mid)
    elif emotion in {"smirk", "proud"}:
        if len(brows) >= 2:
            brows[0].location.z += 0.050; key(brows[0], "location", mid)
            brows[1].location.z -= 0.015; key(brows[1], "location", mid)
        mouth.scale = Vector((mouth_base_scale.x * 2.05, mouth_base_scale.y, max(0.66, mouth_base_scale.z * 0.72)))
        mouth.rotation_euler.z = math.radians(-19); _key_rotation(mouth, mid)
        head.rotation_euler.x = math.radians(-4); head.rotation_euler.y = math.radians(-7); _key_rotation(head, mid)
    else:
        mouth.scale = mouth_base_scale.copy()

    key(mouth, "scale", mid); key(mouth, "scale", settle)
    key(mouth, "location", settle)
    return max(7, len(brows) * 2 + len(eyes) + len(pupils) + 3)

def animate_speaker_emphasis(actor, start_frame, end_frame, fps, turn_index):
    """Small positional emphasis so dialogue is not only mouth/eye animation."""
    root = actor["root"]
    start = root.location.copy()
    mid = min(end_frame, start_frame + max(3, int(0.32 * fps)))
    hold = max(mid + 1, end_frame - max(2, int(0.18 * fps)))
    direction = -1 if turn_index % 2 else 1

    root.location = start.copy()
    key(root, "location", start_frame)
    root.location.x = start.x + 0.055 * direction
    root.location.y = start.y - 0.050
    root.location.z = start.z + 0.018
    key(root, "location", mid)
    key(root, "location", hold)
    root.location = start
    key(root, "location", end_frame)
    return 4


def animate_solo_performance(actor, start_frame, end_frame, fps, turn_index, emotion="neutral"):
    """Solo scenes need deliberate acting even without a gaze partner."""
    root = actor["root"]
    head = actor["head"]
    span = max(6, end_frame - start_frame)
    f1 = start_frame + span // 4
    f2 = start_frame + span // 2
    f3 = start_frame + (span * 3) // 4
    side = -1 if turn_index % 2 else 1

    # Look off-axis, return through camera, then opposite side.
    head.rotation_euler.z = math.radians(13 * side)
    head.rotation_euler.y = math.radians(-3 * side)
    _key_rotation(head, f1)
    head.rotation_euler.z = 0.0
    head.rotation_euler.y = 0.0
    _key_rotation(head, f2)
    head.rotation_euler.z = math.radians(-8 * side)
    _key_rotation(head, f3)
    head.rotation_euler.z = 0.0
    _key_rotation(head, end_frame)

    # Visible weight shift/half-step.
    base = root.location.copy()
    root.location = base.copy()
    key(root, "location", start_frame)
    root.location.x = base.x + 0.10 * side
    root.location.y = base.y - 0.08
    root.location.z = base.z + 0.025
    key(root, "location", f2)
    root.location = base
    key(root, "location", end_frame)

    # Alternate hand gestures to keep solo delivery physically alive.
    action = "thinking" if str(emotion).lower() in {"confused", "serious"} else "show"
    arm_keys = animate_arm_pose(actor, action, f1, end_frame, fps, "R")
    return 7 + arm_keys


def animate_scene_energy(scene_data, actors, primary_actor_id, start_frame, end_frame, fps):
    """Distribute physical beats across the whole scene, not only first 1-2 sec."""
    if not actors:
        return 0
    primary = actors.get(primary_actor_id) or next(iter(actors.values()))
    others = [a for a in actors.values() if a is not primary]
    action = infer_scene_action(scene_data)
    duration = max(12, end_frame - start_frame)
    beat1 = start_frame + int(duration * 0.28)
    beat2 = start_frame + int(duration * 0.56)
    beat3 = start_frame + int(duration * 0.80)
    events = 0

    # Primary gets three separated body/hand beats.
    if action == "dance":
        events += animate_funky_dance(primary, beat1, fps, cycles=2)
        events += animate_funky_dance(primary, beat3, fps, cycles=2)
    else:
        events += animate_arm_pose(primary, action if action != "dialogue" else "show", beat1, min(end_frame, beat1 + fps), fps, "R")
    events += animate_speaker_emphasis(primary, beat2, min(end_frame, beat2 + fps), fps, 2)
    events += animate_arm_pose(primary, "thinking" if action in {"dialogue", "phone_use"} else "show", beat3, min(end_frame, beat3 + fps), fps, "L")

    # Supporting cast reacts at offset beats instead of freezing between lines.
    for idx, actor in enumerate(others):
        reaction_start = min(end_frame - 4, beat1 + idx * max(2, fps // 4))
        reaction_end = min(end_frame, reaction_start + max(6, fps))
        events += animate_listener_reaction(actor, reaction_start, reaction_end, fps, "neutral")

    return events


def animate_continuous_scene_performance(
    scene_data,
    actors,
    primary_actor_id,
    start_frame,
    end_frame,
    fps,
):
    """Guarantee visible performance beats across the full scene.

    V2.9 could front-load movement and then leave a long static tail.
    V3.0 schedules a visible beat roughly every 2.4 seconds and adds a
    mandatory payoff/reaction beat near the end of the scene.
    """
    if not actors or end_frame <= start_frame:
        return 0

    primary = actors.get(primary_actor_id) or next(iter(actors.values()))
    supporting = [a for a in actors.values() if a is not primary]
    action = infer_scene_action(scene_data)

    interval = max(12, int(1.8 * fps))
    first_beat = start_frame + max(6, int(1.4 * fps))
    last_usable = max(first_beat + 1, end_frame - max(6, int(1.0 * fps)))
    beat_frames = list(range(first_beat, last_usable, interval))

    payoff = max(start_frame + 1, end_frame - max(8, int(2.2 * fps)))
    if not beat_frames or abs(beat_frames[-1] - payoff) > max(5, int(1.0 * fps)):
        beat_frames.append(payoff)

    events = 0
    for idx, beat in enumerate(beat_frames):
        beat_end = min(end_frame, beat + max(8, int(1.15 * fps)))
        mode = idx % 5

        if mode == 0:
            events += animate_speaker_emphasis(
                primary, beat, beat_end, fps, idx + 1
            )
        elif mode == 1:
            gesture = action if action not in {"dialogue", "idle"} else "show"
            events += animate_arm_pose(
                primary, gesture, beat, beat_end, fps, "R"
            )
        elif mode == 2:
            events += animate_solo_performance(
                primary, beat, beat_end, fps, idx + 1, emotion="happy"
            )
        elif mode == 3:
            events += animate_arm_pose(
                primary, "thinking", beat, beat_end, fps, "L"
            )
        else:
            events += animate_idle_life(
                primary, beat, beat_end, fps
            )

        if supporting:
            reactor = supporting[idx % len(supporting)]
            reaction_start = min(end_frame - 2, beat + max(2, fps // 5))
            reaction_end = min(
                end_frame,
                reaction_start + max(7, int(0.95 * fps)),
            )
            events += animate_listener_reaction(
                reactor,
                reaction_start,
                reaction_end,
                fps,
                "shocked" if mode in {1, 4} else "neutral",
            )

    return events


def add_ambient_camera_beats(scene, actors, start_frame, end_frame, fps):
    """Add camera coverage during otherwise long dialogue/animation gaps."""
    if not actors or end_frame - start_frame < max(20, int(4 * fps)):
        return 0

    cuts = 0
    cast = list(actors.values())
    interval = max(18, int(3.4 * fps))
    positions = list(range(
        start_frame + max(15, int(3.2 * fps)),
        end_frame - max(8, int(1.2 * fps)),
        interval,
    ))

    for idx, frame in enumerate(positions, start=1):
        if len(cast) >= 2 and idx % 2:
            left = cast[0]
            right = cast[-1]
            cx = (float(left["base"].x) + float(right["base"].x)) / 2.0
            camera, target = _new_camera(
                f"AMBIENT_WIDE_{idx:02d}",
                (cx * 0.10, -11.3, 2.9),
                (cx, 0.65, 1.58),
                lens=48,
            )
            shot = "ambient_group"
        else:
            actor = cast[idx % len(cast)]
            sx = float(actor["base"].x)
            sy = float(actor["base"].y)
            camera, target = _new_camera(
                f"AMBIENT_REACTION_{idx:02d}",
                (sx, -7.5, 2.72),
                (sx, sy, 1.85),
                lens=82,
            )
            shot = "ambient_reaction"

        _bind_camera(
            scene, camera, frame, f"AMBIENT_CUT_{idx:02d}_{shot}"
        )
        camera.keyframe_insert("location", frame=frame)
        camera.location.y += 0.10
        camera.keyframe_insert(
            "location",
            frame=min(end_frame, frame + max(6, int(0.8 * fps))),
        )
        cuts += 2

    return cuts


def add_final_payoff_camera(scene, actors, end_frame, fps):
    """Reserve the end of every scene for a reaction/punchline camera."""
    if not actors:
        return 0

    cast = list(actors.values())
    frame = max(1, end_frame - max(7, int(1.4 * fps)))
    focus = cast[-1] if len(cast) > 1 else cast[0]
    sx = float(focus["base"].x)
    sy = float(focus["base"].y)
    sz = float(focus["base"].z) + 1.85 * float(focus["profile"]["height"])

    camera, target = _new_camera(
        f"PAYOFF_CAM_{focus['id']}",
        (sx, -7.2, 2.70),
        (sx, sy, sz - 0.25),
        lens=88,
    )
    _bind_camera(scene, camera, frame, "FINAL_PAYOFF_REACTION")
    camera.keyframe_insert("location", frame=frame)
    camera.location.y += 0.08
    camera.keyframe_insert("location", frame=end_frame)
    return 2

def mouth_animation(actor, start_frame, end_frame, cycle):
    mouth = actor["mouth"]
    mouth.scale = (1.0, 1.0, 1.0)
    key(mouth, "scale", start_frame)
    count = 1
    frame = start_frame + 2
    opened = False
    while frame < end_frame - 1:
        opened = not opened
        mouth.scale.z = 2.7 if opened else 0.85
        mouth.scale.x = 1.12 if opened else 1.0
        key(mouth, "scale", frame)
        count += 1
        frame += max(3, cycle)
    mouth.scale = (1.0, 1.0, 1.0)
    key(mouth, "scale", end_frame)
    return count + 1



def listener_motion(actor, start_frame, end_frame, fps):
    return animate_listener_reaction(
        actor,
        start_frame,
        end_frame,
        fps,
        emotion="neutral",
    )


def animate_walk(actor, start_frame, fps, run=False):
    root = actor["root"]
    original = root.location.copy()
    duration = max(8, int((1.15 if run else 1.55) * fps))
    distance = 1.45 if run else 1.05

    root.location.x = original.x - distance
    key(root, "location", start_frame)

    steps = 4
    for i in range(steps + 1):
        f = start_frame + int(duration * i / steps)
        phase = -1 if i % 2 else 1

        actor["hips"]["L"].rotation_euler.y = math.radians(phase * (24 if run else 17))
        actor["hips"]["R"].rotation_euler.y = math.radians(-phase * (24 if run else 17))
        _key_rotation(actor["hips"]["L"], f)
        _key_rotation(actor["hips"]["R"], f)

        actor["shoulders"]["L"].rotation_euler.y = math.radians(-phase * 14)
        actor["shoulders"]["R"].rotation_euler.y = math.radians(phase * 14)
        _key_rotation(actor["shoulders"]["L"], f)
        _key_rotation(actor["shoulders"]["R"], f)

        root.location.x = original.x - distance + distance * (i / steps)
        root.location.z = original.z + (0.035 if i % 2 else 0.0)
        key(root, "location", f)

    root.location = original
    key(root, "location", start_frame + duration + 1)
    return duration

def choose_partner(actor_id, scene_chars, episode_chars):
    for c in scene_chars:
        if c != actor_id:
            return c
    for c in episode_chars:
        if c != actor_id:
            return c
    return actor_id



def infer_scene_action(scene):
    explicit = str(scene.get("visual_action") or "").strip().lower()
    setup = str(scene.get("setup") or "").strip().lower()
    props = {str(x).strip().lower() for x in (scene.get("props") or [])}

    if explicit and explicit not in {"idle", "dialogue", "none"}:
        return explicit

    rules = [
        (("chase", "run after", "bhaag", "दौड़", "भाग"), "chase"),
        (("run", "running", "दौड़ता", "भागता"), "run"),
        (("walk", "enter", "arrive", "चलता", "आता", "entry"), "walk"),
        (("give", "hand over", "pass", "देता", "देती", "पकड़ाता"), "give"),
        (("show", "display", "दिखाता", "दिखाती"), "show"),
        (("clean", "sweep", "broom", "झाड़ू", "साफ"), "clean"),
        (("drink", "tea", "chai", "चाय", "पीता", "पीती"), "drink"),
        (("jugaad", "build", "जुगाड़", "बनाता", "बनाते"), "build_jugaad"),
        (("wind", "storm", "आंधी", "हवा", "उड़"), "wind_chaos"),
        (("collect", "coin", "पैसा", "वसूली", "कमाई"), "collect_money"),
        (("relax", "charpai", "आराम", "ठंडक"), "relax"),
        (("spill", "water", "पानी गिर", "फैल"), "spill"),
        (("repair", "wire", "तार", "ठीक कर", "plug"), "repair"),
        (("queue", "line", "कतार"), "queue"),
        (("power cut", "बिजली चली", "current गया"), "power_cut"),
        (("refund", "customer care", "वापस पैसा"), "refund_chase"),
        (("celebrate", "हँसते", "laugh together", "जश्न"), "celebrate"),
        (("phone", "mobile", "assistant", "order", "app", "फोन", "मोबाइल"), "phone_use"),
        (("carry", "box", "parcel", "bag", "डिब्बा", "पार्सल", "बैग"), "carry"),
        (("sit", "sitting", "बैठ"), "sit"),
        (("point", "points", "इशारा"), "point"),
        (("scan", "qr", "स्कैन"), "scan"),
        (("dance", "नाच", "ठुमका", "बारात"), "dance"),
        (("announce", "announcement", "एलान", "ऐलान", "घोषणा"), "announce"),
        (("serve", "परोस", "चाय देना"), "serve"),
    ]
    for words, action in rules:
        if any(word in setup for word in words):
            return action

    if {"qr_board", "qr", "payment_qr"} & props:
        return "scan"
    if {"loudspeaker", "megaphone", "speaker"} & props:
        return "announce"
    if {"phone", "mobile", "smartphone"} & props:
        return "phone_use"
    if {"cup", "tea", "mug"} & props:
        return "drink"
    if {"broom"} & props:
        return "clean"
    if {"bag", "box", "parcel"} & props:
        return "carry"

    return "dialogue"


def _find_prop_object(prop_id):
    prop_id = str(prop_id or "").strip().lower()
    aliases = [prop_id]
    if prop_id == "mobile":
        aliases.append("phone")
    if prop_id == "ai_phone":
        aliases.extend(["ai_phone", "phone"])
    if prop_id in {"wedding_invite", "invite_card"}:
        aliases.append("wedding_card")
    if prop_id in {"sweets_box", "sweet_box"}:
        aliases.append("mithai_box")
    if prop_id == "tea":
        aliases.append("cup")
    if prop_id == "qr":
        aliases.append("qr_board")
    if prop_id == "megaphone":
        aliases.append("loudspeaker")
    for alias in aliases:
        obj = bpy.data.objects.get(f"prop_{alias}")
        if obj:
            return obj
    return None



def attach_story_prop(actor, prop_id):
    """Attach prop to the articulated right hand using local hand space."""
    obj = _find_prop_object(prop_id)
    if obj is None:
        return False
    hand = actor["hands"][1]
    obj.parent = hand
    obj.location = (0.0, -0.12, -0.02)
    obj.rotation_mode = "XYZ"

    pid = str(prop_id).lower()
    if pid in {"phone", "mobile", "smartphone", "ai_phone"}:
        obj.rotation_euler = (math.radians(6), 0.0, math.radians(6))
    elif pid in {"wedding_card", "wedding_invite", "invite_card"}:
        obj.location = (0.0, -0.13, -0.01)
        obj.rotation_euler = (math.radians(4), 0.0, math.radians(4))
    elif pid in {"mithai_box", "sweets_box", "sweet_box"}:
        obj.location = (0.0, -0.12, -0.08)
        obj.rotation_euler = (0.0, 0.0, math.radians(4))
    elif pid in {"cup", "tea", "mug"}:
        obj.location = (0.0, -0.10, 0.02)
    elif pid in {"broom", "stick"}:
        obj.location = (0.0, -0.05, -0.35)
        obj.rotation_euler = (math.radians(18), 0.0, 0.0)
    elif pid in {"loudspeaker", "megaphone", "speaker"}:
        obj.location = (0.0, -0.15, -0.02)
        obj.rotation_euler = (math.radians(84), 0.0, math.radians(4))
    elif pid in {"kulhad", "clay_cup"}:
        obj.location = (0.0, -0.10, 0.01)
    return True


def stage_scene_props(scene, actors, primary_actor_id):
    props = [
        str(x).strip().lower()
        for x in (scene.get("props") or [])
        if str(x).strip()
    ]
    action = infer_scene_action(scene)
    actor = actors.get(primary_actor_id) if primary_actor_id else None
    attached = []

    if actor:
        preferred = []
        if action in {"phone_use", "scan", "snatch_phone", "phone_pass", "ai_interview", "interview_sit", "mock_shock", "end_screen_hold"}:
            preferred = ["ai_phone", "phone", "mobile", "smartphone"]
        elif action in {"show_wedding_card", "wedding_prep"}:
            preferred = ["wedding_card", "wedding_invite", "invite_card"]
        elif action in {"offer_sweets"}:
            preferred = ["mithai_box", "sweets_box", "sweet_box"]
        elif action == "drink":
            preferred = ["cup", "tea", "mug"]
        elif action == "clean":
            preferred = ["broom", "stick"]
        elif action == "carry":
            preferred = ["bag", "box", "parcel"]
        elif action == "announce":
            preferred = ["loudspeaker", "megaphone", "speaker"]
        elif action == "serve":
            preferred = ["cup", "tea", "mug", "kulhad"]
        elif action in {"give", "show", "use", "point"}:
            preferred = props[:1]

        for prop in preferred:
            if prop in props and attach_story_prop(actor, prop):
                attached.append(prop)
                break

    return action, attached



def animate_funky_dance(actor, start_frame, fps, cycles=3):
    root = actor["root"]
    base = root.location.copy()
    events = 0
    step = max(3, int(0.28 * fps))
    for i in range(cycles * 2 + 1):
        f = start_frame + i * step
        side = -1 if i % 2 else 1
        root.location.x = base.x + 0.11 * side
        root.location.z = base.z + (0.05 if i % 2 else 0.0)
        root.rotation_euler.z = math.radians(6.0 * side)
        key(root, "location", f)
        _key_rotation(root, f)
        actor["shoulders"]["L"].rotation_euler.x = math.radians(-35 - 15*side)
        actor["shoulders"]["R"].rotation_euler.x = math.radians(-35 + 15*side)
        _key_rotation(actor["shoulders"]["L"], f)
        _key_rotation(actor["shoulders"]["R"], f)
        events += 4
    root.location = base
    root.rotation_euler.z = 0.0
    key(root, "location", start_frame + (cycles*2+1)*step)
    _key_rotation(root, start_frame + (cycles*2+1)*step)
    return events + 2

def animate_action_choreography(action, actors, primary_actor_id, start_frame, fps):
    """Scene-level physical action instead of a single generic pose."""
    action = str(action or "dialogue").lower()
    primary = actors.get(primary_actor_id) if primary_actor_id else None
    others = [a for k, a in actors.items() if k != primary_actor_id]
    partner = others[0] if others else None
    events = 0

    if action in {"walk", "enter"}:
        for actor in actors.values():
            animate_walk(actor, start_frame, fps, run=False)
            events += 1

    elif action in {"run", "chase"}:
        offset = 0
        for actor in actors.values():
            animate_walk(actor, start_frame + offset, fps, run=True)
            offset += max(2, fps // 5)
            events += 1

    elif action in {"give", "show", "point", "use"} and primary:
        end = start_frame + max(10, int(1.5 * fps))
        events += animate_arm_pose(primary, action, start_frame, end, fps, "R")
        if partner:
            events += animate_arm_pose(
                partner, "show", start_frame + max(2, fps // 4),
                end, fps, "L"
            )

    elif action == "facepalm" and primary:
        end = start_frame + max(12, int(1.6 * fps))
        events += animate_arm_pose(primary, "facepalm", start_frame, end, fps, "R")
        primary["head"].rotation_euler.x = math.radians(9)
        _key_rotation(primary["head"], start_frame + max(3, fps // 3))
        if partner:
            events += animate_listener_reaction(partner, start_frame, end, fps, "smirk")

    elif action == "snatch_phone" and primary:
        end = start_frame + max(14, int(1.9 * fps))
        events += animate_arm_pose(primary, "give", start_frame, end, fps, "R")
        if partner:
            events += animate_arm_pose(partner, "phone_use", start_frame, end, fps, "R")
            root = partner["root"]; base = root.location.copy()
            root.location = base.copy(); key(root, "location", start_frame)
            root.location.y = base.y + 0.18; key(root, "location", start_frame + max(5, int(.55*fps)))
            root.location = base; key(root, "location", end)
            events += 3

    elif action == "phone_pass" and primary:
        end = start_frame + max(12, int(1.7 * fps))
        events += animate_arm_pose(primary, "give", start_frame, end, fps, "R")
        if partner:
            events += animate_arm_pose(partner, "show", start_frame + max(3, fps//3), end, fps, "L")

    elif action == "whisper" and primary:
        end = start_frame + max(12, int(1.8 * fps))
        events += animate_arm_pose(primary, "whisper", start_frame, end, fps, "R")
        if partner:
            for actor, sign in ((primary, 1), (partner, -1)):
                root = actor["root"]; base = root.location.copy()
                root.location = base.copy(); key(root, "location", start_frame)
                root.location.x = base.x + 0.38 * sign
                root.location.y = base.y + 0.28
                root.rotation_euler.x = math.radians(-10.0)
                key(root, "location", start_frame + max(4, int(.45*fps))); _key_rotation(root, start_frame + max(4, int(.45*fps)))
                root.location = base; root.rotation_euler.x = 0.0
                key(root, "location", end); _key_rotation(root, end)
                events += 5
            events += animate_face_emotion(partner, "shocked", start_frame + max(3, fps//3), end, fps)

    elif action in {"interview_sit", "ai_interview"}:
        end = start_frame + max(16, int(2.2 * fps))
        # Only the interviewer drops into the chair zone; supporting cast stays standing/reaction-ready.
        if primary:
            root = primary["root"]; base = root.location.copy()
            root.location = base.copy(); key(root, "location", start_frame)
            root.location.z = base.z - 0.34; root.location.y = base.y + 0.10
            key(root, "location", start_frame + max(5, int(.55*fps)))
            events += 2
            events += animate_arm_pose(primary, "phone_use", start_frame, end, fps, "R")
        if partner:
            root = partner["root"]; base = root.location.copy()
            root.location = base.copy(); key(root, "location", start_frame)
            root.location.x = base.x + (-0.22 if base.x > 0 else 0.22); root.location.y = base.y - 0.12
            key(root, "location", start_frame + max(5, int(.65*fps)))
            root.location = base; key(root, "location", end)
            events += 3
            events += animate_listener_reaction(partner, start_frame, end, fps, "confused")

    elif action == "show_wedding_card" and primary:
        end = start_frame + max(14, int(1.9 * fps))
        events += animate_arm_pose(primary, "show", start_frame, end, fps, "R")
        if partner:
            events += animate_listener_reaction(partner, start_frame + max(2,fps//4), end, fps, "shocked")

    elif action == "offer_sweets" and primary:
        end = start_frame + max(14, int(1.9 * fps))
        events += animate_arm_pose(primary, "give", start_frame, end, fps, "R")
        if partner:
            events += animate_arm_pose(partner, "show", start_frame + max(3,fps//3), end, fps, "L")
            events += animate_listener_reaction(partner, start_frame, end, fps, "confused")

    elif action == "backpedal" and primary:
        end = start_frame + max(14, int(1.9 * fps))
        root = primary["root"]; base = root.location.copy()
        for idx, shift in enumerate((0.0, 0.22, 0.44, 0.62)):
            f = start_frame + int((end-start_frame) * idx / 3)
            root.location = Vector((base.x, base.y + shift, base.z + (0.025 if idx % 2 else 0.0)))
            key(root, "location", f)
            events += 1
        root.location = base; key(root, "location", end + 1); events += 1
        events += animate_arm_pose(primary, "show", start_frame, end, fps, "L")

    elif action == "wedding_prep" and primary:
        end = start_frame + max(16, int(2.2 * fps))
        events += animate_arm_pose(primary, "show", start_frame, end, fps, "R")
        for idx, actor in enumerate(others):
            events += animate_listener_reaction(actor, start_frame + idx*max(2,fps//6), end, fps, "excited")

    elif action == "mock_shock" and primary:
        end = start_frame + max(12, int(1.6 * fps))
        root = primary["root"]; base = root.location.copy()
        root.location = base.copy(); key(root, "location", start_frame)
        root.location.y = base.y + 0.28; root.location.z = base.z + 0.035
        key(root, "location", start_frame + max(4, int(.38*fps)))
        root.location = base; key(root, "location", end)
        events += 3
        events += animate_arm_pose(primary, "show", start_frame, end, fps, "L")
        events += animate_arm_pose(primary, "phone_use", start_frame, end, fps, "R")
        events += animate_listener_reaction(primary, start_frame, end, fps, "shocked")
        events += animate_face_emotion(primary, "shocked", start_frame, end, fps)
        if partner:
            events += animate_listener_reaction(partner, start_frame + max(2,fps//4), end, fps, "confused")

    elif action == "end_screen_hold":
        end = start_frame + max(14, int(2.0 * fps))
        for idx, actor in enumerate(actors.values()):
            events += animate_arm_pose(actor, "show", start_frame + idx*max(1,fps//8), end, fps, "R")
            events += animate_listener_reaction(actor, start_frame, end, fps, "happy")

    elif action == "phone_use" and primary:
        end = start_frame + max(10, int(1.8 * fps))
        events += animate_arm_pose(primary, "phone_use", start_frame, end, fps, "R")
        if partner:
            events += animate_listener_reaction(
                partner, start_frame, end, fps, "confused"
            )

    elif action == "drink" and primary:
        end = start_frame + max(10, int(1.6 * fps))
        events += animate_arm_pose(primary, "drink", start_frame, end, fps, "R")

    elif action == "clean" and primary:
        shoulder = primary["shoulders"]["R"]
        elbow = primary["elbows"]["R"]
        end = start_frame + max(12, int(2.2 * fps))
        for i, angle in enumerate((-35, -62, -28, -58, -30)):
            f = start_frame + int((end - start_frame) * i / 4)
            shoulder.rotation_euler.x = math.radians(angle)
            shoulder.rotation_euler.z = math.radians((-1 if i % 2 else 1) * 15)
            elbow.rotation_euler.x = math.radians(-35)
            _key_rotation(shoulder, f)
            _key_rotation(elbow, f)
            events += 2

    elif action == "carry" and primary:
        end = start_frame + max(10, int(1.7 * fps))
        events += animate_arm_pose(primary, "carry", start_frame, end, fps, "L")
        events += animate_arm_pose(primary, "carry", start_frame, end, fps, "R")

    elif action == "build_jugaad" and primary:
        end = start_frame + max(14, int(2.4 * fps))
        mid = start_frame + (end - start_frame) // 2
        events += animate_arm_pose(primary, "show", start_frame, mid, fps, "R")
        events += animate_arm_pose(primary, "carry", mid, end, fps, "L")
        if partner:
            events += animate_listener_reaction(partner, start_frame, end, fps, "confused")

    elif action == "wind_chaos" and primary:
        end = start_frame + max(16, int(2.8 * fps))
        for idx, actor in enumerate(actors.values()):
            root = actor["root"]
            base = root.location.copy()
            f1 = start_frame + idx * max(2, fps // 8)
            f2 = min(end, f1 + max(6, int(0.8 * fps)))
            f3 = min(end, f2 + max(6, int(0.8 * fps)))
            root.location = base.copy(); key(root, "location", f1)
            root.location.x = base.x + (0.18 if idx % 2 else -0.18)
            root.location.y = base.y + 0.10
            root.rotation_euler.z = math.radians(10 if idx % 2 else -10)
            key(root, "location", f2); _key_rotation(root, f2)
            root.location = base; root.rotation_euler.z = 0.0
            key(root, "location", f3); _key_rotation(root, f3)
            events += 5
            events += animate_arm_pose(actor, "show", f1, f3, fps, "R" if idx % 2 else "L")

    elif action == "collect_money" and primary:
        end = start_frame + max(12, int(2.0 * fps))
        events += animate_arm_pose(primary, "show", start_frame, end, fps, "R")
        if partner:
            events += animate_arm_pose(partner, "thinking", start_frame, end, fps, "L")
            events += animate_listener_reaction(partner, start_frame, end, fps, "shocked")

    elif action == "relax" and primary:
        end = start_frame + max(12, int(2.2 * fps))
        root = primary["root"]
        base = root.location.copy()
        root.location = base.copy(); key(root, "location", start_frame)
        root.location.y = base.y + 0.12; root.location.z = base.z - 0.08
        key(root, "location", start_frame + max(4, int(0.7 * fps)))
        root.location = base; key(root, "location", end)
        events += 3
        events += animate_arm_pose(primary, "show", start_frame, end, fps, "L")

    elif action == "scan" and primary:
        end = start_frame + max(12, int(2.0 * fps))
        events += animate_arm_pose(primary, "phone_use", start_frame, end, fps, "R")
        if partner:
            events += animate_listener_reaction(partner, start_frame + max(2, fps//3), end, fps, "excited")

    elif action == "announce" and primary:
        end = start_frame + max(12, int(2.0 * fps))
        events += animate_arm_pose(primary, "show", start_frame, end, fps, "R")
        primary["head"].rotation_euler.x = math.radians(-6)
        _key_rotation(primary["head"], start_frame + max(2, fps//3))
        if partner:
            events += animate_listener_reaction(partner, start_frame, end, fps, "shocked")

    elif action == "serve" and primary:
        end = start_frame + max(12, int(1.8 * fps))
        events += animate_arm_pose(primary, "give", start_frame, end, fps, "R")
        if partner:
            events += animate_arm_pose(partner, "show", start_frame + max(2,fps//3), end, fps, "L")

    elif action == "dance":
        offset = 0
        for actor in actors.values():
            events += animate_funky_dance(actor, start_frame + offset, fps, cycles=3)
            offset += max(1, fps//8)

    elif action == "spill":
        end = start_frame + max(12, int(1.8 * fps))
        for idx, actor in enumerate(actors.values()):
            f1 = start_frame + idx * max(1, fps // 8)
            f2 = min(end, f1 + max(5, int(0.65 * fps)))
            events += animate_listener_reaction(
                actor, f1, f2, fps, "shocked"
            )
            root = actor["root"]
            base = root.location.copy()
            root.location = base.copy(); key(root, "location", f1)
            root.location.x = base.x + (-0.14 if idx % 2 else 0.14)
            root.location.y = base.y - 0.08
            key(root, "location", f2)
            root.location = base; key(root, "location", end)
            events += 3

    elif action == "repair" and primary:
        end = start_frame + max(14, int(2.2 * fps))
        mid = start_frame + (end - start_frame) // 2
        events += animate_arm_pose(primary, "thinking", start_frame, mid, fps, "L")
        events += animate_arm_pose(primary, "show", mid, end, fps, "R")
        if partner:
            events += animate_listener_reaction(
                partner, start_frame, end, fps, "confused"
            )

    elif action == "queue":
        step = max(5, int(0.7 * fps))
        for idx, actor in enumerate(actors.values()):
            root = actor["root"]
            base = root.location.copy()
            f1 = start_frame + idx * max(2, fps // 6)
            f2 = f1 + step
            root.location = base.copy(); key(root, "location", f1)
            root.location.y = base.y + 0.18
            key(root, "location", f2)
            root.location = base; key(root, "location", f2 + step)
            events += 3

    elif action == "power_cut":
        end = start_frame + max(14, int(2.0 * fps))
        for idx, actor in enumerate(actors.values()):
            f1 = start_frame + idx * max(1, fps // 10)
            events += animate_listener_reaction(
                actor, f1, end, fps, "confused"
            )
            actor["head"].rotation_euler.z = math.radians(
                -8 if idx % 2 else 8
            )
            _key_rotation(actor["head"], f1 + max(3, fps // 3))
            events += 1

    elif action == "refund_chase":
        offset = 0
        for actor in actors.values():
            animate_walk(actor, start_frame + offset, fps, run=True)
            offset += max(2, fps // 6)
            events += 1

    elif action == "celebrate":
        offset = 0
        for actor in actors.values():
            events += animate_funky_dance(
                actor,
                start_frame + offset,
                fps,
                cycles=2,
            )
            offset += max(1, fps // 10)

    elif action == "sit":
        for actor in actors.values():
            z = actor["root"].location.z
            actor["root"].location.z = z
            key(actor["root"], "location", start_frame)
            actor["root"].location.z = z - 0.42
            key(actor["root"], "location", start_frame + max(4, fps // 2))
            for side in ("L", "R"):
                actor["hips"][side].rotation_euler.x = math.radians(-55)
                _key_rotation(actor["hips"][side], start_frame + max(4, fps // 2))
            events += 4

    return events




def animate_story_prop_motion(scene_data, start_frame, end_frame, fps):
    """Animate readable story props so physical comedy is not actor-only."""
    props = {str(x).strip().lower() for x in (scene_data.get("props") or [])}
    action = infer_scene_action(scene_data)
    events = 0

    fan_ids = ("table_fan", "fan", "jugaad_fan")
    if props.intersection(fan_ids):
        rotor = next(
            (bpy.data.objects.get(f"prop_{pid}_rotor") for pid in fan_ids if bpy.data.objects.get(f"prop_{pid}_rotor")),
            None,
        )
        if rotor is not None:
            steps = 8 if action in {"wind_chaos", "relax"} else 5
            for idx in range(steps + 1):
                frame = start_frame + int((end_frame - start_frame) * idx / max(1, steps))
                rotor.rotation_euler.y = math.radians(idx * (540 if action == "wind_chaos" else 300))
                _key_rotation(rotor, frame)
                events += 1

    cloth = next(
        (bpy.data.objects.get(f"prop_{pid}") for pid in ("gamcha", "towel", "cloth") if bpy.data.objects.get(f"prop_{pid}")),
        None,
    )
    if cloth is not None and action == "wind_chaos":
        base = cloth.location.copy()
        for idx, shift in enumerate((0.0, 0.32, -0.18, 0.48, 0.0)):
            frame = start_frame + int((end_frame - start_frame) * idx / 4)
            cloth.location.x = base.x + shift
            cloth.location.z = base.z + abs(shift) * 0.18
            cloth.rotation_euler.y = math.radians(shift * 45)
            key(cloth, "location", frame)
            _key_rotation(cloth, frame)
            events += 2
        cloth.location = base
    return events


def animate_declared_reaction_payoff(scene_data, actors, scene, start_frame, end_frame, fps):
    """Honor the episode plan's declared reaction as an actual visual punchline."""
    reaction = scene_data.get("reaction") or {}
    if not isinstance(reaction, dict) or not reaction or not actors:
        return 0

    char_id = str(reaction.get("character_id") or "").strip().lower()
    actor = actors.get(char_id) or next(iter(actors.values()))
    emotion = str(reaction.get("expression") or "shocked").strip().lower()
    duration = max(0.65, float(reaction.get("duration_seconds") or 0.9))
    reaction_end = max(start_frame + 2, end_frame - max(2, int(0.25 * fps)))
    reaction_start = max(start_frame, reaction_end - max(8, int(duration * fps)))

    events = animate_face_emotion(actor, emotion, reaction_start, reaction_end, fps)
    events += animate_listener_reaction(actor, reaction_start, reaction_end, fps, emotion)

    root = actor["root"]
    base = root.location.copy()
    mid = reaction_start + max(2, (reaction_end - reaction_start) // 2)
    root.location = base.copy(); key(root, "location", reaction_start)
    root.location.z = base.z + 0.07
    root.location.y = base.y - 0.10
    key(root, "location", mid)
    root.location = base; key(root, "location", reaction_end)
    events += 3

    sx = float(actor["base"].x)
    sy = float(actor["base"].y)
    sz = float(actor["base"].z) + 1.95 * float(actor["profile"]["height"])
    camera, target = _new_camera(
        f"DECLARED_REACTION_{char_id}_{int(reaction_start)}",
        (sx, -6.75, 2.70),
        (sx, sy, sz - 0.24),
        lens=100,
    )
    _bind_camera(scene, camera, reaction_start, f"REACTION_PAYOFF_{char_id}")
    camera.keyframe_insert("location", frame=reaction_start)
    camera.location.y += 0.16
    camera.keyframe_insert("location", frame=reaction_end)
    target.keyframe_insert("location", frame=reaction_start)
    target.keyframe_insert("location", frame=reaction_end)
    return events + 6

def add_ai_phone_hero_opening(scene, actors, scene_data, start_frame, fps):
    """V6.4 cold-open: safe screen framing, animated AI-bahu avatar, then hard handoff to Babuji reaction."""
    if int(scene_data.get("id", 0) or 0) != 1 or "ai_phone" not in {str(x).lower() for x in (scene_data.get("props") or [])}:
        return 0
    prop = _find_prop_object("ai_phone")
    screen = bpy.data.objects.get("prop_ai_phone_screen")
    babuji = actors.get("babuji")
    if prop is None or babuji is None:
        return 0
    focus = screen if screen is not None else prop
    hero_seconds = float(scene_data.get("hero_insert_seconds") or 1.85)
    hero_seconds = max(1.75, min(2.05, hero_seconds))
    hero_end = start_frame + max(20, int(hero_seconds * fps))

    bpy.context.view_layer.update()
    pos = focus.matrix_world.translation.copy()
    # V6.4: back camera away + raise/right offset to avoid Babuji's hand occluding the display.
    cam, target = _new_camera(
        "AI_PHONE_HERO_CAM_V64",
        (float(pos.x) + 0.16, float(pos.y) - 1.72, float(pos.z) + 0.14),
        (float(pos.x), float(pos.y), float(pos.z) + 0.018),
        lens=60,
    )
    if cam.constraints:
        cam.constraints[-1].target = focus
    for marker in list(scene.timeline_markers):
        if start_frame <= int(marker.frame) <= hero_end:
            scene.timeline_markers.remove(marker)
    _bind_camera(scene, cam, start_frame, "AI_PHONE_HERO_INSERT_V64")
    scene.camera = cam
    cam.keyframe_insert("location", frame=start_frame)
    # tiny motivated push, not a clipping zoom
    push = min(hero_end - 1, start_frame + max(8, int(0.85 * fps)))
    cam.location.y += 0.10; cam.location.x -= 0.025
    cam.keyframe_insert("location", frame=push); cam.keyframe_insert("location", frame=hero_end)
    target.keyframe_insert("location", frame=start_frame); target.keyframe_insert("location", frame=hero_end)

    # Screen/avatar pulse.  Keep scale modest so nothing clips the handset bezel.
    orb = bpy.data.objects.get("prop_ai_phone_ai_orb")
    halo = bpy.data.objects.get("prop_ai_phone_avatar_halo")
    bars = [bpy.data.objects.get(f"prop_ai_phone_voicebar_{i}") for i in range(3)]
    pulse = min(hero_end - 1, start_frame + max(6, int(0.62 * fps)))
    for obj, factor in ((orb,1.18),(halo,1.12)):
        if obj is not None:
            base = obj.scale.copy(); obj.scale=base.copy(); key(obj,"scale",start_frame)
            obj.scale=Vector((base.x*factor,base.y,base.z*factor)); key(obj,"scale",pulse)
            obj.scale=base.copy(); key(obj,"scale",hero_end)
    for idx, bar in enumerate(bars):
        if bar is not None:
            base=bar.scale.copy(); key(bar,"scale",start_frame)
            bar.scale=Vector((base.x,base.y,base.z*(1.35+idx*0.18))); key(bar,"scale",min(hero_end-1,pulse+idx*2))
            bar.scale=base.copy(); key(bar,"scale",hero_end)

    # Pre-load the reaction so the first face cut lands on a big readable expression.
    animate_face_emotion(babuji, "shocked", start_frame, hero_end + max(10, int(0.70 * fps)), fps)
    return 14

def camera_for_dialogue_turn(
    scene,
    speaker,
    listener,
    start_frame,
    end_frame,
    turn_index,
    fps,
    cast_count=1,
    emotion="neutral",
):
    """V6.4 motivated coverage; cold-open gives phone ~1.8s then a strong face reaction."""
    sx = float(speaker["base"].x); sy = float(speaker["base"].y)
    sz = float(speaker["base"].z) + 2.0 * float(speaker["profile"]["height"])
    if listener is not None:
        lx = float(listener["base"].x); ly = float(listener["base"].y)
        lz = float(listener["base"].z) + 1.95 * float(listener["profile"]["height"])
    else:
        lx, ly, lz = sx, sy, sz

    emotion = str(emotion or "neutral").lower()
    cut_frame = start_frame
    if turn_index == 1:
        # Hero-phone insert occupies the first ~1.75 seconds.
        cut_frame = min(end_frame - 1, start_frame + max(16, int(1.82 * fps)))

    if listener is None:
        mode = turn_index % 3
        if mode == 1:
            loc = (sx * 0.18, -10.7, 2.85); target = (sx, sy + 0.15, sz - 0.55); lens = 50; shot = "solo_wide"
        elif mode == 2:
            loc = (sx, -7.8, 2.70); target = (sx, sy, sz - 0.38); lens = 78; shot = "solo_medium"
        else:
            loc = (sx * 0.98, -6.9, 2.72); target = (sx, sy, sz - 0.22); lens = 92; shot = "solo_close"
    elif turn_index == 1 and emotion in {"shocked", "surprised", "angry", "confused"}:
        # The first post-phone image must be the face that sells the joke.
        loc = (sx, -6.55, 2.72); target = (sx, sy, sz - 0.22); lens = 98; shot = "opening_reaction_close"
    elif turn_index == 1 or turn_index % 4 == 0:
        cx = (sx + lx) / 2.0; cy = (sy + ly) / 2.0; width = abs(sx - lx)
        loc = (cx * 0.10, -10.9 - min(1.0, width * 0.12), 2.86)
        target = (cx, cy, min(sz, lz) - 0.48); lens = 48 if cast_count <= 2 else 44
        shot = "two_shot" if cast_count <= 2 else "group_wide"
    elif turn_index % 2 == 0:
        side = -1.0 if lx > sx else 1.0
        loc = (sx + side * 0.72, -7.65, 2.68); target = (sx, sy, sz - 0.34); lens = 76; shot = "speaker_three_quarter"
    else:
        loc = (sx, -7.15, 2.68); target = (sx, sy, sz - 0.30); lens = 88; shot = "speaker_isolated"

    camera, target_obj = _new_camera(f"DIALOGUE_CAM_{turn_index:02d}_{speaker['id']}_{shot}", loc, target, lens=lens)
    _bind_camera(scene, camera, cut_frame, f"CUT_{turn_index:02d}_{shot}")
    camera.keyframe_insert("location", frame=cut_frame)
    camera.location.y += 0.10; camera.keyframe_insert("location", frame=max(cut_frame + 1, end_frame - 1))
    target_obj.keyframe_insert("location", frame=cut_frame); target_obj.keyframe_insert("location", frame=max(cut_frame + 1, end_frame - 1))
    events = 6

    duration_frames = end_frame - start_frame
    if listener is not None and duration_frames >= int(1.45 * fps) and (
        emotion in {"shocked", "angry", "confused", "excited", "happy"} or turn_index % 3 == 0
    ):
        reaction_frame = max(cut_frame + max(5, int(0.70 * fps)), end_frame - max(6, int(0.48 * fps)))
        reaction_frame = min(end_frame - 1, reaction_frame)
        rx = float(listener["base"].x); ry = float(listener["base"].y)
        rz = float(listener["base"].z) + 1.95 * float(listener["profile"]["height"])
        reaction_cam, reaction_target = _new_camera(
            f"REACTION_CAM_{turn_index:02d}_{listener['id']}", (rx, -6.75, 2.70), (rx, ry, rz - 0.22), lens=98
        )
        _bind_camera(scene, reaction_cam, reaction_frame, f"REACTION_CUT_{turn_index:02d}")
        reaction_cam.keyframe_insert("location", frame=reaction_frame); reaction_target.keyframe_insert("location", frame=reaction_frame)
        events += 4
    return events

def animate_ai_bahu_signature_blocking(scene_data, actors, start_frame, end_frame, fps):
    """V6.4 story-specific blocking for the opening; inserted last so it cannot be masked by generic motion."""
    sid = int(scene_data.get("id", 0) or 0)
    if sid not in {1, 2, 3}:
        return 0
    events = 0
    babuji = actors.get("babuji"); guddu = actors.get("guddu"); bittu = actors.get("bittu")
    def travel(actor, frame_a, frame_b, frame_c, dx, dy, dz=0.0, yaw=0.0, lean=-4.0):
        nonlocal events
        if actor is None: return
        root=actor["root"]; base=actor["base"]
        root.location=Vector((base.x,base.y,base.z)); key(root,"location",frame_a)
        root.rotation_euler.x=0.0; root.rotation_euler.z=0.0; _key_rotation(root,frame_a)
        root.location=Vector((base.x+dx,base.y+dy,base.z+dz)); key(root,"location",frame_b)
        root.rotation_euler.x=math.radians(lean); root.rotation_euler.z=math.radians(yaw); _key_rotation(root,frame_b)
        key(root,"location",frame_c); _key_rotation(root,frame_c); events += 6

    if sid == 1:
        # 0-1.8s phone insert; 1.8-4.5s Babuji recoils while Guddu physically closes distance.
        f1=min(end_frame,start_frame+max(18,int(1.85*fps)))
        f2=min(end_frame,start_frame+max(30,int(3.10*fps)))
        f3=min(end_frame,start_frame+max(44,int(4.55*fps)))
        travel(babuji,f1,f2,f3,-0.18,0.92,0.06,yaw=-11,lean=10)
        travel(guddu,f1,min(f3,f2+max(5,int(.45*fps))),f3,-0.66,-0.46,0.03,yaw=-24,lean=-10)
        if babuji: events += animate_arm_pose(babuji,"phone_use",f1,f3,fps,"R") + animate_arm_pose(babuji,"show",f1,f3,fps,"L")
        if guddu: events += animate_arm_pose(guddu,"facepalm",f2,f3,fps,"R")
        if bittu:
            travel(bittu,f1,min(f3,f2+max(4,int(.35*fps))),f3,0.22,-0.26,0.01,yaw=8,lean=-4)
            events += animate_listener_reaction(bittu,f2,f3,fps,"shocked")
    elif sid == 2:
        f1=start_frame+max(5,int(.45*fps)); f2=min(end_frame,start_frame+max(18,int(1.65*fps))); f3=min(end_frame,start_frame+max(34,int(3.2*fps)))
        travel(babuji,f1,f2,f3,0.24,0.62,-0.42,yaw=12,lean=-8)
        travel(guddu,f1,min(f3,f2+max(4,int(.4*fps))),f3,-0.40,-0.34,0.02,yaw=-18,lean=-7)
        if babuji: events += animate_arm_pose(babuji,"phone_use",f1,f3,fps,"R")
        if guddu: events += animate_arm_pose(guddu,"facepalm",f2,f3,fps,"R")
    elif sid == 3:
        f1=start_frame+max(5,int(.40*fps)); f2=min(end_frame,start_frame+max(18,int(1.55*fps))); f3=min(end_frame,start_frame+max(34,int(3.15*fps)))
        # Bittu leans into Babuji's space; Babuji meets halfway, Guddu visibly recoils.
        travel(bittu,f1,f2,f3,-0.86,-0.36,0.04,yaw=-32,lean=-14)
        travel(babuji,f1,min(f3,f2+max(4,int(.35*fps))),f3,0.36,0.22,0.02,yaw=20,lean=-8)
        travel(guddu,f1,min(f3,f2+max(4,int(.35*fps))),f3,0.42,0.52,0.02,yaw=11,lean=7)
        if bittu: events += animate_arm_pose(bittu,"whisper",f1,f3,fps,"R")
        if babuji: events += animate_face_emotion(babuji,"shocked",f2,f3,fps)
        if guddu: events += animate_face_emotion(guddu,"confused",f2,f3,fps)
    return events

def add_dead_air_visual_beats(scene, actors, turns, total_seconds, fps, max_gap_seconds=1.25):
    """Turn long dialogue gaps/tails into visible reaction/action beats."""
    if not actors or total_seconds <= 0:
        return 0
    intervals = []
    cursor = 0.0
    for t in sorted(turns, key=lambda x: float(x.get("start_seconds", 0.0))):
        start = float(t.get("start_seconds", 0.0))
        if start - cursor > max_gap_seconds:
            intervals.append((cursor, start))
        cursor = max(
            cursor,
            float(t.get("end_seconds", start)) + float(t.get("pause_after_seconds", 0.0)),
        )
    if total_seconds - cursor > max_gap_seconds:
        intervals.append((cursor, total_seconds))

    cast = list(actors.values())
    events = 0
    for idx, (gap_start, gap_end) in enumerate(intervals, start=1):
        beat_sec = gap_start + min(0.55, max(0.18, (gap_end - gap_start) * 0.30))
        beat = max(1, int(beat_sec * fps) + 1)
        beat_end = min(int(gap_end * fps), beat + max(8, int(0.90 * fps)))
        actor = cast[(idx - 1) % len(cast)]
        events += animate_solo_performance(actor, beat, beat_end, fps, idx, emotion="confused" if idx % 2 else "happy")
        if len(cast) > 1:
            reactor = cast[idx % len(cast)]
            events += animate_listener_reaction(reactor, beat, beat_end, fps, "shocked" if idx % 2 else "neutral")
        sx = float(actor["base"].x)
        sy = float(actor["base"].y)
        sz = float(actor["base"].z) + 1.9 * float(actor["profile"]["height"])
        cam, target = _new_camera(
            f"DEAD_AIR_BEAT_{idx:02d}", (sx, -7.5, 2.74), (sx, sy, sz - 0.25), lens=82
        )
        _bind_camera(scene, cam, beat, f"DEAD_AIR_ACTION_{idx:02d}")
        cam.keyframe_insert("location", frame=beat)
        target.keyframe_insert("location", frame=beat)
        events += 4
    return events


def scene_blocking_positions(count, action):
    """Shallow arc with depth separation to make partner-facing angles visible."""
    if count <= 1:
        return [(0.0, 0.45, 0.0)]
    if count == 2:
        return [(-1.30, 0.35, 0.0), (1.30, 0.90, 0.0)]
    if count == 3:
        # asymmetric triangle avoids the "three dolls on a line" silhouette.
        return [(-1.55, 0.20, 0.0), (0.15, 1.18, 0.0), (2.05, 0.56, 0.0)]
    return [
        (-2.35, 0.35, 0.0),
        (-0.80, 1.00, 0.0),
        (0.80, 1.00, 0.0),
        (2.35, 0.35, 0.0),
    ]

def set_render(scene, config, quality, frames_dir):
    prefs = config.get("render_engine_preference", ["BLENDER_EEVEE", "BLENDER_WORKBENCH"])
    chosen = None
    for candidate in prefs:
        try:
            scene.render.engine = candidate
            chosen = candidate
            break
        except Exception:
            continue
    if not chosen:
        raise RuntimeError(
            "No supported Eevee render engine found. "
            f"Available build rejected: {prefs}"
        )

    quality = quality or config.get("quality", "standard")
    res = config.get("resolution", {}).get(quality) or [960, 540]
    scene.render.resolution_x = int(res[0])
    scene.render.resolution_y = int(res[1])
    scene.render.resolution_percentage = 100
    scene.render.fps = int(config.get("fps", 24))
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(frames_dir / "frame_")
    scene.render.film_transparent = bool(config.get("render", {}).get("transparent", False))

    # Current Blender 5.2 Homebrew LTS may expose BLENDER_EEVEE rather than
    # BLENDER_EEVEE_NEXT; avoid engine-specific property assumptions.
    return chosen, quality, tuple(res)


def main():
    a = args()
    plan = load(a.plan)
    timeline = load(a.timeline)
    config = load(a.config)
    out = Path(a.output_dir)
    frames = out / "frames"
    frames.mkdir(parents=True, exist_ok=True)

    clear_scene()

    selected_scenes = plan.get("scenes", [])
    if a.max_scenes:
        selected_scenes = selected_scenes[:a.max_scenes]
    if not selected_scenes:
        raise RuntimeError("No scenes to render")

    selected_ids = {int(s.get("id", i+1)) for i, s in enumerate(selected_scenes)}
    turns = [t for t in timeline.get("turns", []) if int(t["scene_id"]) in selected_ids]
    fps = int(config.get("fps", 24))  # resolved per-quality FPS from pipeline
    cycle = int(config.get("animation", {}).get("mouth_cycle_frames", 5))

    # Timeline defines actual audio duration; render must cover it.
    total_seconds = float(timeline.get("duration_seconds") or 0.0)
    if a.max_scenes:
        matching = [t for t in turns]
        if matching:
            max_turn = max(float(t["end_seconds"]) + float(t.get("pause_after_seconds", 0)) for t in matching)
            # scene padding was included in master audio, but for max-scenes mode
            # use selected scene shot budgets.
            total_seconds = max(
                max_turn,
                sum(float(s.get("shot_duration_seconds", 12)) for s in selected_scenes),
            )

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = max(2, int(math.ceil(total_seconds * fps)))

    first_scene = selected_scenes[0]
    first_location = str(first_scene.get("location_id") or "living_room")
    resolved_world = environment(first_location, first_scene.get("props") or [])
    print(
        f"[SCENE WORLD] requested={first_location} resolved={resolved_world} "
        f"props={','.join(str(x) for x in (first_scene.get('props') or [])) or 'NONE'}"
    )
    camera, camera_target = setup_camera()

    chars = [
        str(c).strip().lower()
        for c in (plan.get("characters") or [])
        if str(c).strip()
    ]
    for t in turns:
        c = str(t.get("character_id") or "").lower()
        if c and c != "narrator" and c not in chars:
            chars.append(c)
    chars = chars[:4] or ["guddu", "bittu"]

    scene_action = infer_scene_action(first_scene)
    positions = scene_blocking_positions(len(chars), scene_action)
    actors = {
        c: create_character(c, positions[i])
        for i, c in enumerate(chars)
    }
    print(
        f"[SCENE PERFORMANCE] action={scene_action} "
        f"blocking=conversational_arc cast={','.join(chars)}"
    )

    # Bind relevant story prop to the first speaker when the scene action
    # clearly calls for phone/cup/broom/bag interaction.
    primary_actor_id = str(first_scene.get("action_actor_id") or "").strip().lower()
    first_dialogue = first_scene.get("dialogue") or []
    if not primary_actor_id and first_dialogue and isinstance(first_dialogue[0], dict):
        primary_actor_id = str(
            first_dialogue[0].get("character_id")
            or first_dialogue[0].get("speaker")
            or ""
        ).lower()
    resolved_action, attached_props = stage_scene_props(
        first_scene,
        actors,
        primary_actor_id,
    )
    print(
        f"[SCENE PROP STAGING] action={resolved_action} "
        f"primary={primary_actor_id or 'NONE'} "
        f"attached={','.join(attached_props) or 'NONE'}"
    )
    # Initial camera keys per scene using cumulative audio-aware timing.
    # V6.4 delays scene-1 generic coverage until after the cold-open phone insert.
    scene_offsets = {}
    cursor = 0.0
    for s in selected_scenes:
        sid = int(s.get("id", 0))
        scene_offsets[sid] = cursor
        camera_frame = max(1, int(cursor * fps) + 1)
        if sid == 1 and str(s.get("hero_insert") or "") == "ai_phone_close_up":
            hero_seconds = max(1.65, float(s.get("hero_insert_seconds") or 1.75))
            camera_frame += int(hero_seconds * fps) + 2
        camera_for_scene(camera, camera_target, s, camera_frame)
        cursor += float(s.get("shot_duration_seconds", 12.0))

    # Bind hero camera AFTER generic camera setup, so frame-1 cannot be overwritten.
    hero_camera_keys = add_ai_phone_hero_opening(scene, actors, first_scene, 1, fps)
    if hero_camera_keys:
        print(f"[AI BAHU V6.4] hero_phone_camera_keys={hero_camera_keys} priority=LOCKED")

    mouth_keys = 0
    gaze_keys = 0
    gesture_events = 0

    scene_camera_beat_keys = int(hero_camera_keys)

    # Scene-level action choreography.
    choreography_events = 0
    for s in selected_scenes:
        action = infer_scene_action(s)
        sid = int(s.get("id", 0))
        start = max(1, int(scene_offsets.get(sid, 0.0) * fps) + 1)

        scene_dialogue = s.get("dialogue") or []
        primary = str(s.get("action_actor_id") or "").strip().lower()
        if not primary and scene_dialogue and isinstance(scene_dialogue[0], dict):
            primary = str(
                scene_dialogue[0].get("character_id")
                or scene_dialogue[0].get("speaker")
                or ""
            ).lower()

        choreography_events += animate_action_choreography(
            action,
            actors,
            primary,
            start,
            fps,
        )
        scene_end = min(
            scene.frame_end,
            start + max(12, int(float(s.get("shot_duration_seconds") or 20.0) * fps)) - 1,
        )
        choreography_events += animate_scene_energy(
            s,
            actors,
            primary,
            start,
            scene_end,
            fps,
        )
        choreography_events += animate_continuous_scene_performance(
            s,
            actors,
            primary,
            start,
            scene_end,
            fps,
        )
        choreography_events += animate_story_prop_motion(
            s,
            start,
            scene_end,
            fps,
        )
        choreography_events += animate_declared_reaction_payoff(
            s,
            actors,
            scene,
            start,
            scene_end,
            fps,
        )
        scene_camera_beat_keys += add_ambient_camera_beats(
            scene,
            actors,
            start,
            scene_end,
            fps,
        )

    scene_camera_beat_keys += add_final_payoff_camera(
        scene,
        actors,
        scene.frame_end,
        fps,
    )

    # Dialogue-driven performance.
    by_scene = {}
    for t in turns:
        by_scene.setdefault(int(t["scene_id"]), []).append(t)

    mouth_keys = 0
    gaze_keys = 0
    gesture_events = 0
    pupil_gaze_keys = 0
    head_turn_keys = 0
    body_turn_keys = 0
    listener_reaction_keys = 0
    idle_motion_keys = 0
    dialogue_camera_keys = scene_camera_beat_keys

    for global_turn_index, t in enumerate(turns, start=1):
        char_id = str(t["character_id"]).lower()
        actor = actors.get(char_id)
        if not actor:
            continue

        start_f = max(1, int(round(float(t["start_seconds"]) * fps)) + 1)
        end_f = max(start_f + 3, int(round(float(t["end_seconds"]) * fps)) + 1)

        scene_chars = [
            str(x["character_id"]).lower()
            for x in by_scene.get(int(t["scene_id"]), [])
            if str(x.get("character_id") or "").lower() in actors
        ]
        partner_id = choose_partner(char_id, scene_chars, list(actors))
        partner = actors.get(partner_id)
        if partner is actor:
            partner = next((v for k, v in actors.items() if k != char_id), None)

        # Speaker performance.
        mouth_keys += mouth_animation(actor, start_f, end_f, cycle)
        pose_actor(
            actor,
            str(t.get("pose") or t.get("emotion") or "idle"),
            start_f,
            fps,
        )
        gesture_events += 1
        gesture_events += animate_face_emotion(
            actor,
            str(t.get("emotion") or "neutral"),
            start_f,
            end_f,
            fps,
        )
        gesture_events += animate_speaker_emphasis(
            actor,
            start_f,
            end_f,
            fps,
            global_turn_index,
        )
        idle_motion_keys += animate_idle_life(actor, start_f, end_f, fps)

        if partner is not None:
            gaze = animate_visible_gaze(actor, partner, start_f, end_f, fps)
            pupil_gaze_keys += gaze["pupil"]
            body_turn_keys += gaze["body"]
            head_turn_keys += gaze["head"]
            gaze_keys += gaze["pupil"] + gaze["head"] + gaze["body"]
            gesture_events += animate_dialogue_blocking(
                actor, partner, start_f, end_f, fps, global_turn_index
            )
        else:
            gesture_events += animate_solo_performance(
                actor,
                start_f,
                end_f,
                fps,
                global_turn_index,
                emotion=str(t.get("emotion") or "neutral"),
            )

        # Camera grammar applies to both conversations and solo dialogue.
        dialogue_camera_keys += camera_for_dialogue_turn(
            scene,
            actor,
            partner,
            start_f,
            end_f,
            global_turn_index,
            fps,
            cast_count=len(actors),
            emotion=str(t.get("emotion") or "neutral"),
        )

        # Listener performance: every listener visibly turns toward speaker,
        # reacts, and keeps subtle idle motion.
        for other_id, other in actors.items():
            if other_id == char_id:
                continue

            gaze = animate_visible_gaze(other, actor, start_f, end_f, fps)
            pupil_gaze_keys += gaze["pupil"]
            body_turn_keys += gaze["body"]
            head_turn_keys += gaze["head"]
            gaze_keys += gaze["pupil"] + gaze["head"] + gaze["body"]

            listener_reaction_keys += animate_listener_reaction(
                other,
                start_f,
                end_f,
                fps,
                emotion=str(t.get("emotion") or "neutral"),
            )
            idle_motion_keys += animate_idle_life(other, start_f, end_f, fps)

    # V6.4 final-pass blocking for opening scenes. This runs after generic dialogue motion
    # so hero movements remain visible rather than being overwritten by micro-animation.
    signature_blocking_keys = 0
    for s in selected_scenes:
        sid = int(s.get("id", 0))
        start = max(1, int(scene_offsets.get(sid, 0.0) * fps) + 1)
        end = min(scene.frame_end, start + max(12, int(float(s.get("shot_duration_seconds") or 13.33) * fps)) - 1)
        signature_blocking_keys += animate_ai_bahu_signature_blocking(s, actors, start, end, fps)
    choreography_events += signature_blocking_keys

    dead_air_visual_keys = add_dead_air_visual_beats(
        scene,
        actors,
        turns,
        total_seconds,
        fps,
        max_gap_seconds=1.25,
    )
    dialogue_camera_keys += dead_air_visual_keys

    # Fallback camera drift only when the scene has no spoken dialogue.
    if not turns and scene.frame_end > 24:
        camera.location.x -= 0.08
        key(camera, "location", scene.frame_start)
        camera.location.x += 0.16
        key(camera, "location", scene.frame_end)

    engine, quality, resolution = set_render(scene, config, a.quality, frames)

    # World
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    if not world.node_tree:
        try:
            world.use_nodes = True
        except Exception:
            pass
    bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg:
        bg.inputs["Color"].default_value = (0.055, 0.065, 0.08, 1)
        bg.inputs["Strength"].default_value = 0.38

    blend_file = out / "cartoon_blender_full.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))

    print(f"[BLENDER FULL] engine={engine} quality={quality} resolution={resolution[0]}x{resolution[1]}")
    print(f"[BLENDER FULL] frames=1-{scene.frame_end} fps={fps}")
    print(f"[BLENDER FULL] Rendering PNG sequence...")
    bpy.ops.render.render(animation=True)

    rendered = sorted(frames.glob("frame_*.png"))
    expected = scene.frame_end - scene.frame_start + 1
    if len(rendered) != expected:
        raise RuntimeError(f"Rendered frame mismatch: {len(rendered)}/{expected}")

    manifest = {
        "version": "6.4",
        "plan": str(Path(a.plan)),
        "timeline": str(Path(a.timeline)),
        "blend": str(blend_file),
        "frames_dir": str(frames),
        "render_engine": engine,
        "quality": quality,
        "resolution": list(resolution),
        "fps": fps,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "duration_seconds": total_seconds,
        "checks": {
            "character_count": len(actors),
            "dialogue_turn_count": len(turns),
            "partner_performance_required": bool(len(actors) >= 2 and len(turns) > 0),
            "visible_pupil_count": sum(len(x["pupils"]) for x in actors.values()),
            "mouth_animation_keyframes": mouth_keys,
            "gaze_animation_keyframes": gaze_keys,
            "pupil_gaze_keyframes": pupil_gaze_keys,
            "head_turn_keyframes": head_turn_keys,
            "body_turn_keyframes": body_turn_keys,
            "listener_reaction_keyframes": listener_reaction_keys,
            "idle_motion_keyframes": idle_motion_keys,
            "dialogue_camera_keyframes": dialogue_camera_keys,
            "gesture_events": gesture_events,
            "choreography_events": choreography_events,
            "scene_action": resolved_action,
            "requested_location": first_location,
            "resolved_world": resolved_world,
            "semantic_world_match": bool(resolved_world == resolve_world_id(first_location)),
            "connected_rig_count": sum(
                1 for a in actors.values()
                if a.get("rig_type") == "hierarchical_connected_v27"
            ),
            "solo_performance_enabled": True,
            "safe_framing_enabled": True,
            "establishing_hold_enabled": True,
            "distributed_scene_energy_enabled": True,
            "continuous_performance_scheduler_enabled": True,
            "ai_phone_hero_priority_v64": bool(hero_camera_keys),
            "signature_blocking_v63": True,
            "exaggerated_facial_acting_v63": True,
            "ambient_camera_beats_enabled": True,
            "final_payoff_camera_enabled": True,
            "strong_body_facing_v40_enabled": True,
            "dialogue_turn_blocking_v40_enabled": True,
            "dialogue_motivated_camera_v40_enabled": True,
            "dead_air_visual_filler_v40_enabled": True,
            "world_dressing_v40_enabled": True,
            "ambient_pause_bed_v40_enabled": True,
            "quality_fps_sync_v40_enabled": True,
            "ai_bahu_3d_v60_enabled": True,
            "ai_bahu_action_pack_v60": [
                "facepalm", "snatch_phone", "phone_pass", "whisper",
                "ai_interview", "show_wedding_card", "offer_sweets",
                "backpedal", "wedding_prep", "mock_shock", "end_screen_hold"
            ],
            "declared_reaction_payoff_enabled": True,
            "story_prop_motion_enabled": True,
            "village_jugaad_comedy_pack_enabled": True,
            "longform_action_pack_enabled": True,
            "village_funky_worlds_enabled": True,
            "funky_action_library_enabled": True,
            "distinct_profile_count": len({
                a["profile"].get("body_tag") for a in actors.values()
            }),
            "attached_props": attached_props,
            "frame_count": len(rendered),
            "expected_frame_count": expected
        }
    }
    mf = out / "blender_manifest.json"
    mf.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[BLENDER FULL] manifest={mf}")
    print(f"[BLENDER FULL] frames_rendered={len(rendered)}/{expected}")


if __name__ == "__main__":
    main()
