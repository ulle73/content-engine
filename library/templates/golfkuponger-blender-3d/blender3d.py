"""Golfkuponger 3D-element i Blender 5.2, headless. Renderar en PNG-sekvens med alfa (läggs ovanpå filmer).

Körs av render.py (som även kodar ProRes 4444, WebM VP9 och MP4-förhandsvisning). Direkt:
  blender -b --factory-startup --python-exit-code 1 -P blender3d.py -- '<json>'

Effekter ("effekt"):
  titel     3D-ord/rubrik i guld som snurrar in ur djupet, landar mjukt, ljussvep över guldet, lätt gungning.
  golfboll  golfboll (riktiga dimplar i geometrin) i studioljus som studsar in från höger och rullar till vila.

Gemensamma nycklar: out (mapp för bildrutorna), fps (30), width/height (1080x1920), scale (% av upplösningen),
engine (EEVEE|CYCLES), samples (64), motion_blur (true), x/y (motivets mitt i px i 1080x1920; standard x 497 =
mitten av safe zone, y titel 620 / golfboll 960), intro (bildrutor för inrörelsen), frames (totalt; standard
intro + läsregel/vila),
only_frames ([n, ...] renderar bara de bildrutorna), blend (sökväg: spara .blend för GUI:t), exit (none|spin).
titel: text (\\n = ny rad), font (.ttf/.otf, standard Inter Bold), color ("#D6A536"), metallic (1.0), roughness
  (0.22), bredd_px (800), hojd_max_px (380), spin_deg (270), extrude (0.14), glint (true), glint_energy (3500).
golfboll: diameter_px (420), studs_px (650 = första fallhöjd), studsar (3), dimplar (336), djup (0.018),
  skugga (0.55 = kontaktskuggans styrka, 0 = av), squash (0.035).

Skriptet skriver qa.json i out (landningsbildruta, nedslag för ljudsynk, läsregel); render.py mäter motivets
verkliga ruta i alfan mot safe zones (x 65–929, y 270–1250). Läsregeln (titel) stoppar med exitkod 2.
"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Quaternion

a = json.loads(sys.argv[sys.argv.index("--") + 1])
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EFFEKT = a.get("effekt", "titel")
W, H = a.get("width", 1080), a.get("height", 1920)
FPS = a.get("fps", 30)
SAFE = (65, 270, 929, 1250)          # x0, y0, x1, y1 i 1080x1920 (skills/video-regler)
OUT = os.path.abspath(a["out"]); os.makedirs(OUT, exist_ok=True)


def srgb(hexstr):
    h = hexstr.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def ease_out(t, p=3):
    t = min(max(t, 0.0), 1.0); return 1 - (1 - t) ** p


def ease_in(t, p=3):
    t = min(max(t, 0.0), 1.0); return t ** p


# ---------- scen ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES' if a.get("engine", "EEVEE").upper() == "CYCLES" else 'BLENDER_EEVEE'
if sc.render.engine == 'CYCLES':
    sc.cycles.device = 'CPU'; sc.cycles.samples = a.get("samples", 64); sc.cycles.use_denoising = True
else:
    sc.eevee.taa_render_samples = a.get("samples", 64)
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = a.get("scale", 100)
sc.render.fps = FPS
sc.view_settings.view_transform = 'Standard'   # exakta brand-färger (AgX bleker)
sc.render.film_transparent = True
if a.get("motion_blur", True):
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5

# Studiomiljö utan HDRI: ljus horisont (softbox-band) framför, mörk golv, mjukt tak – syns bara i reflexer.
w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
nt = w.node_tree; nodes = nt.nodes; links = nt.links
bgn = nodes["Background"]
tc = nodes.new("ShaderNodeTexCoord"); sep = nodes.new("ShaderNodeSeparateXYZ")
ramp = nodes.new("ShaderNodeValToRGB")
links.new(tc.outputs["Generated"], sep.inputs[0])
mr = nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1; mr.inputs["From Max"].default_value = 1
links.new(sep.outputs["Z"], mr.inputs["Value"]); links.new(mr.outputs["Result"], ramp.inputs["Fac"])
cr = ramp.color_ramp; cr.interpolation = 'EASE'
cr.elements[0].position = 0.0; cr.elements[0].color = (0.004, 0.006, 0.005, 1)
cr.elements[1].position = 1.0; cr.elements[1].color = (0.25, 0.25, 0.25, 1)
for pos, v in ((0.42, 0.01), (0.5, 0.9), (0.56, 0.35), (0.7, 0.06)):
    e = cr.elements.new(pos); e.color = (v, v * 0.97, v * 0.92, 1)
links.new(ramp.outputs["Color"], bgn.inputs["Color"]); bgn.inputs["Strength"].default_value = 1.0


def area(name, loc, target, energy, size, size_y=None, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.color = color
    if size_y:
        d.shape = 'RECTANGLE'; d.size = size; d.size_y = size_y
    else:
        d.size = size
    o = bpy.data.objects.new(name, d); sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def camera(target, dist, elev_deg, fov_deg, x_px, y_px):
    """Kamera som tittar på target; objektivförskjutning (shift) lägger target på pixeln (x_px, y_px)."""
    cd = bpy.data.cameras.new("Cam"); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(fov_deg)
    cd.clip_start = 0.1; cd.clip_end = 500
    cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    el = math.radians(elev_deg)
    cam.location = Vector(target) + Vector((0, -dist * math.cos(el), dist * math.sin(el)))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cd.shift_x = (W / 2 - x_px) / max(W, H)
    cd.shift_y = (y_px - H / 2) / max(W, H)
    return cam


def world_per_px(dist, fov_deg):
    return 2 * dist * math.tan(math.radians(fov_deg) / 2) / H


def key(obj, path, f):
    obj.keyframe_insert(path, frame=f)


X_PX, Y_PX = a.get("x", 497), a.get("y", 620 if EFFEKT == "titel" else 960)
settle = None         # bildruta då inrörelsen landat
exit_start = None
nedslag = []          # bildrutor där bollen slår i marken (för ljudsynk)

# ---------- effekt 1: titel ----------
if EFFEKT == "titel":
    text = a.get("text", "MER GOLF").replace("\\n", "\n")
    chars = len(text.replace("\n", " "))
    lasning = max(5 / 6, chars / 12) + 0.9          # läsregeln, sekunder
    intro = a.get("intro", 27)
    exit_len = 12 if a.get("exit", "none") == "spin" else 0
    hold_min = math.ceil(lasning * FPS)
    frames = a.get("frames", intro + hold_min + 10 + exit_len)
    settle = intro; exit_start = frames - exit_len if exit_len else None
    hold = (exit_start or frames) - settle
    if hold < hold_min:
        print(f"STOPP: läsregeln – '{text}' ({chars} tecken) behöver {lasning:.2f} s = {hold_min} bildrutor "
              f"stilla, har {hold}. Öka frames eller korta texten.")
        sys.exit(2)

    cu = bpy.data.curves.new("Titel", 'FONT'); cu.body = text
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.space_line = 0.9
    cu.extrude = a.get("extrude", 0.14); cu.bevel_depth = 0.025; cu.bevel_resolution = 5
    font = a.get("font") or os.path.join(ROOT, "engine", "ad_studio", "fonts", "Inter-Bold.ttf")
    if os.path.exists(font):
        cu.font = bpy.data.fonts.load(font)
    t = bpy.data.objects.new("Titel", cu); sc.collection.objects.link(t)
    m = bpy.data.materials.new("Guld"); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*srgb(a.get("color", "#D6A536")), 1)
    p.inputs["Metallic"].default_value = a.get("metallic", 1.0)
    p.inputs["Roughness"].default_value = a.get("roughness", 0.22)
    cu.materials.append(m)

    DIST, FOV = 20.0, 30.0
    wpp = world_per_px(DIST, FOV)
    bpy.context.view_layer.update()
    dx, dy = max(t.dimensions.x, 1e-3), max(t.dimensions.y, 1e-3)
    k = min(a.get("bredd_px", 800) * wpp / dx, a.get("hojd_max_px", 380) * wpp / dy)
    cam = camera((0, 0, 0), DIST, 0, FOV, X_PX, Y_PX)

    area("Key", (-6, -14, 7), (0, 0, 0), 2500, 6)
    area("Fill", (8, -12, -2), (0, 0, 0), 700, 8)
    area("RimL", (-9, 6, 3), (0, 0, 0), 2200, 3)
    area("RimR", (9, 6, 3), (0, 0, 0), 2200, 3)
    glint = area("Glint", (-14, -9, 0), (0, 0, 0), a.get("glint_energy", 3500) if a.get("glint", True) else 0, 0.4, 14, (1, 0.95, 0.85))

    spin = math.radians(a.get("spin_deg", 270))
    for f in range(1, frames + 1):
        s = ease_out((f - 1) / max(settle - 1, 1))
        rz = -spin * (1 - s)
        ks = k * (0.35 + 0.65 * s)
        depth = 14 * (1 - s)                                   # kommer fram ur djupet
        if f > settle:                                         # lätt gungning, börjar med hastighet 0
            ph = (f - settle) / FPS
            rz += math.radians(4) * math.sin(math.pi * ph / 2.6) ** 2
        if exit_start and f > exit_start:
            e = ease_in((f - exit_start) / exit_len)
            rz += math.radians(120) * e; ks *= 1 - 0.95 * e
        t.location = (0, depth, 0); t.rotation_euler = (math.radians(90), 0, rz); t.scale = (ks, ks, ks)
        key(t, "location", f); key(t, "rotation_euler", f); key(t, "scale", f)
        gt = (f - settle - 3) / (0.9 * FPS)                    # ljussvep strax efter landning
        glint.location = (-14 + 28 * ease_out(min(max(gt, 0), 1), 2), -9, 0)
        glint.rotation_euler = (Vector((0, 0, 0)) - glint.location).to_track_quat('-Z', 'Y').to_euler()
        key(glint, "location", f); key(glint, "rotation_euler", f)

# ---------- effekt 2: golfboll ----------
elif EFFEKT == "golfboll":
    R = 1.0
    intro = a.get("intro", 54)
    frames = a.get("frames", intro + 36)
    settle = intro

    # Boll: icosfär med riktiga dimplar (radiell förskjutning av hörnen), jämnt fördelade (Fibonacci-sfär).
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=a.get("subdiv", 8), radius=R)
    ball = bpy.context.object; ball.name = "Golfboll"
    me = ball.data
    n = len(me.vertices); co = np.empty(n * 3, dtype=np.float64); me.vertices.foreach_get("co", co)
    print("Golfboll:", n, "hörn"); co = co.reshape(n, 3); dirs = co / np.linalg.norm(co, axis=1, keepdims=True)
    N = a.get("dimplar", 336)
    i = np.arange(N) + 0.5
    phi = np.arccos(1 - 2 * i / N); th = math.pi * (1 + 5 ** 0.5) * i
    centers = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], axis=1)
    spacing = math.sqrt(4 * math.pi / N * 2 / math.sqrt(3))
    r = 0.47 * spacing
    best = np.empty(n)
    for s0 in range(0, n, 20000):
        best[s0:s0 + 20000] = np.arccos(np.clip((dirs[s0:s0 + 20000] @ centers.T).max(axis=1), -1, 1))
    tt = np.clip(best / r, 0, 1)
    hgt = -a.get("djup", 0.018) * R * (1 - tt ** 2)
    me.vertices.foreach_set("co", (dirs * (R + hgt)[:, None]).ravel().astype(np.float32))
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons)); me.update()
    m = bpy.data.materials.new("Boll"); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.76, 0.77, 0.76, 1)
    p.inputs["Roughness"].default_value = 0.38
    p.inputs["Coat Weight"].default_value = 0.7; p.inputs["Coat Roughness"].default_value = 0.06
    me.materials.append(m)

    # Förälder: läge + squash (världsaxlar). Bollen: rullning (kvaternion) med slumpad startvinkel.
    rig = bpy.data.objects.new("BollRig", None); sc.collection.objects.link(rig)
    ball.parent = rig; ball.rotation_mode = 'QUATERNION'
    q0 = Quaternion((0.3, 0.8, 0.5), 1.1)

    # Kontaktskugga: plan med radiell gradient (fungerar i Eevee och med alfa, ingen shadow catcher behövs).
    bpy.ops.mesh.primitive_plane_add(size=2)
    sh = bpy.context.object; sh.name = "Skugga"
    sm = bpy.data.materials.new("Skugga"); sm.use_nodes = True
    try:
        sm.surface_render_method = 'BLENDED'
    except Exception:
        pass
    sn = sm.node_tree.nodes; sl = sm.node_tree.links
    sn.remove(sn["Principled BSDF"])
    tco = sn.new("ShaderNodeTexCoord"); gr = sn.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'
    pw = sn.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.2
    st = sn.new("ShaderNodeMath"); st.operation = 'MULTIPLY'; st.name = "Styrka"
    tr = sn.new("ShaderNodeBsdfTransparent"); em = sn.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1); mix = sn.new("ShaderNodeMixShader")
    sl.new(tco.outputs["Object"], gr.inputs["Vector"]); sl.new(gr.outputs["Fac"], pw.inputs[0])
    sl.new(pw.outputs[0], st.inputs[0]); sl.new(st.outputs[0], mix.inputs["Fac"])
    sl.new(tr.outputs[0], mix.inputs[1]); sl.new(em.outputs[0], mix.inputs[2])
    sl.new(mix.outputs[0], sn["Material Output"].inputs["Surface"])
    sh.data.materials.append(sm)
    sh.visible_shadow = False

    FOV = 22.0
    DIST = R * H / (a.get("diameter_px", 420) * math.tan(math.radians(FOV) / 2))
    cam = camera((0, 0, R), DIST, 12, FOV, X_PX, Y_PX)
    wpp = world_per_px(DIST, FOV)

    area("Key", (-7, -9, 9), (0, 0, R), 1200, 7)
    area("Fill", (9, -8, 2), (0, 0, R), 450, 9)
    area("RimL", (-6, 7, 4), (0, 0, R), 1300, 3)
    area("RimR", (7, 6, 5), (0, 0, R), 1600, 3)
    area("Top", (0, 0, 10), (0, 0, R), 500, 6)

    # Rörelse: konstant inbromsning i x (stannar exakt vid intro), fallande bågar med studs (e = 0,5).
    x0 = (W - X_PX + a.get("diameter_px", 420) * 0.8) * wpp
    h0 = a.get("studs_px", 650) * wpp
    nb = a.get("studsar", 3); e = 0.5
    heights = [h0 * (e * e) ** j for j in range(nb + 1)]
    durs = [math.sqrt(heights[0])] + [2 * math.sqrt(hh) for hh in heights[1:]]
    tb = 0.72 * intro                                                   # studsarna tar 72 % av inrörelsen
    kd = tb / sum(durs); durs = [d * kd for d in durs]
    impacts = list(np.cumsum(durs))
    nedslag = [round(float(ti) + 1, 1) for ti in impacts]

    def height(fr):
        tcur = fr - 1
        if tcur <= durs[0]:
            return heights[0] * (1 - (tcur / durs[0]) ** 2)
        acc = durs[0]
        for j in range(1, nb + 1):
            if tcur <= acc + durs[j]:
                u = (tcur - acc) / durs[j] * 2 - 1                      # -1..1 över bågen
                return heights[j] * (1 - u * u)
            acc += durs[j]
        return 0.0

    sq_amt = a.get("squash", 0.035); skugga = a.get("skugga", 0.55)
    for f in range(1, frames + 1):
        s = min((f - 1) / max(intro - 1, 1), 1)
        x = x0 * (1 - s) ** 2
        z = height(f)
        sq = 0.0
        for j, ti in enumerate(impacts[:-1] if nb else []):
            dt = abs((f - 1) - ti)
            if dt < 1.5:
                sq = max(sq, sq_amt * (e ** j) * (1 - dt / 1.5))
        rig.location = (x, 0, R * (1 - sq) + z)
        rig.scale = (1 + sq / 2, 1 + sq / 2, 1 - sq)
        key(rig, "location", f); key(rig, "scale", f)
        ball.rotation_quaternion = Quaternion((0, -1, 0), (x0 - x) / R) @ q0
        key(ball, "rotation_quaternion", f)
        hr = min(z / max(h0, 1e-6), 1)
        sh.location = (x, 0, 0.002); ss = 1.25 * R * (1 + 0.8 * hr); sh.scale = (ss, ss, 1)
        key(sh, "location", f); key(sh, "scale", f)
        node = sm.node_tree.nodes["Styrka"]; node.inputs[1].default_value = skugga * (1 - 0.75 * hr)
        node.inputs[1].keyframe_insert("default_value", frame=f)
else:
    print("Okänd effekt:", EFFEKT); sys.exit(1)

sc.frame_start, sc.frame_end = 1, frames

# ---------- QA-underlag (render.py mäter motivets ruta i alfan och jämför med safe zones) ----------
qa = {"effekt": EFFEKT, "frames": frames, "fps": FPS, "settle": settle, "exit_start": exit_start,
      "safe_zone": SAFE, "nedslag": nedslag}
if EFFEKT == "titel":
    qa.update(text=text, lasregel_s=round(lasning, 2), stilla_s=round(hold / FPS, 2))
with open(os.path.join(OUT, "qa.json"), "w", encoding="utf-8") as fh:
    json.dump(qa, fh, ensure_ascii=False, indent=1)
print("Landar bildruta", settle, "av", frames)

if a.get("blend"):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a["blend"]))

im = sc.render.image_settings
im.media_type = 'IMAGE'; im.file_format = 'PNG'; im.color_mode = 'RGBA'; im.color_depth = '8'
if a.get("only_frames"):
    for f in a["only_frames"]:
        sc.frame_set(f); sc.render.filepath = os.path.join(OUT, f"f_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = os.path.join(OUT, "f_")
    bpy.ops.render.render(animation=True)
print("KLART", OUT)
