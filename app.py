import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import json
import google.generativeai as genai

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="Lighting Architect Pro", layout="wide")
st.title("💡 Lighting Architect Pro")

api_key = st.secrets.get("GEMINI_KEY") or st.sidebar.text_input("Enter Gemini API Key", type="password")

# --- 2. USER INPUTS ---
with st.sidebar:
    st.header("Room Dimensions")
    r_w = st.number_input("Width (X)", value=3.5)
    r_d = st.number_input("Depth (Y)", value=3.0)
    r_h = st.number_input("Height (Z)", value=2.8)
    st.divider()
    gear = st.text_area("Gear", "100W COB, 20W Stick, 80cm Whiteboard")
    style = st.selectbox("Style", ["Cinematic Moody", "Clean & Professional", "High-Contrast Noir"])

# --- 3. LOGIC: CLOCK POSITION & COLORS ---
def get_clock_pos(lx, ly, sx, sy):
    dx, dy = lx - sx, ly - sy
    angle = np.degrees(np.arctan2(dy, dx)) % 360
    # Map angle to clock (3 o'clock is 0 deg in polar, we want 12 o'clock at top)
    clock_map = {0:3, 30:2, 60:1, 90:12, 120:11, 150:10, 180:9, 210:8, 240:7, 270:6, 300:5, 330:4, 360:3}
    closest_clock = min(clock_map.keys(), key=lambda x:abs(x-angle))
    return clock_map[closest_clock]

def get_safe_color(c):
    c = str(c).lower()
    m = {"amber":"orange", "tungsten":"darkorange", "warm":"orange", "cool":"cyan"}
    return m.get(c, c) if mcolors.is_color_like(m.get(c,c)) else "gold"

# --- 4. DRAWING ENGINES ---
def draw_2d(data, rw, rd):
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_aspect('equal')
    sub_x, sub_y = rw/2, rd*0.6
    ax.plot(sub_x, sub_y, 'yo', markersize=15, label="Subject")
    ax.plot(rw/2, 0.5, 'bs', markersize=10, label="Camera")
    for l in data.get('lights', []):
        col = get_safe_color(l['color'])
        ax.plot(l['x'], l['y'], 'o', color=col, markersize=10)
        ax.annotate(l['id'], xy=(sub_x, sub_y), xytext=(l['x'], l['y']),
                    arrowprops=dict(arrowstyle='->', color=col, lw=2))
    st.pyplot(fig)

def draw_3d(data, rw, rd, rh):
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_zlim(0, rh)
    sub_x, sub_y, sub_z = rw/2, rd*0.6, 1.2
    # Draw Subject
    ax.scatter(sub_x, sub_y, sub_z, color='yellow', s=100, label="Subject")
    # Draw Lights as vectors
    for l in data.get('lights', []):
        col = get_safe_color(l['color'])
        ax.quiver(l['x'], l['y'], l['z'], sub_x-l['x'], sub_y-l['y'], sub_z-l['z'], 
                  color=col, length=0.8, normalize=True)
        ax.scatter(l['x'], l['y'], l['z'], color=col, s=50)
    ax.set_xlabel('Width'); ax.set_ylabel('Depth'); ax.set_zlabel('Height')
    st.pyplot(fig)

# --- 5. THE AI ENGINE ---
def get_lighting_plan(w, d, h, gear, style):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""Act as a DP. Room {w}x{d}x{h}m. Subject at {w/2},{d*0.6},1.2. 
    Return JSON ONLY: {{"style":"{style}", "lights":[{"id":"Key", "x":1, "y":1, "z":1.8, "color":"orange", "strength":80, "logic":"..."}]}}
    Gear: {gear}. Use realistic coords."""
    res = model.generate_content(prompt)
    return json.loads(res.text.replace('```json', '').replace('```', '').strip())

# --- 6. EXECUTION & CHEATSHEET ---
if st.button("Generate Layout"):
    if not api_key: st.error("No API Key")
    else:
        plan = get_lighting_plan(r_w, r_d, r_h, gear, style)
        c1, c2 = st.columns(2)
        with c1: st.subheader("Top View (2D)"); draw_2d(plan, r_w, r_d)
        with c2: st.subheader("Perspective (3D)"); draw_map_3d = draw_3d(plan, r_w, r_d, r_h)
        
        st.divider()
        st.header("📋 Setup Cheatsheet")
        for l in plan['lights']:
            clock = get_clock_pos(l['x'], l['y'], r_w/2, r_d*0.6)
            with st.expander(f"🔹 {l['id']} - {l['strength']}% Power"):
                st.write(f"**Horizontal:** Place at your {clock} o'clock position.")
                st.write(f"**Vertical:** Set stand height to {l['z']}m (Vertical Angle: ~90°).")
                st.write(f"**Aiming:** {l.get('logic', 'Point toward subject face.')}")
                st.info(f"**The Logic:** {l.get('logic', 'Creates depth and separation.')}")
