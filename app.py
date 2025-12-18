import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import json
import re
import google.generativeai as genai

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="Lighting Architect Pro", layout="wide")
st.title("💡 Lighting Architect Pro")

api_key = st.secrets.get("GEMINI_KEY") or st.sidebar.text_input("Enter Gemini API Key", type="password")

# --- 2. USER INPUTS ---
with st.sidebar:
    st.header("📏 Room Dimensions")
    r_w = st.number_input("Width (X) in m", value=3.5)
    r_d = st.number_input("Depth (Y) in m", value=3.0)
    r_h = st.number_input("Height (Z) in m", value=2.8)
    st.divider()
    gear = st.text_area("Your Gear", "100W COB light, 20W Stick light, 80cm Whiteboard")
    style = st.selectbox("Style Vibe", ["Cinematic Moody", "Clean & Professional", "High-Contrast Noir"])

# --- 3. MATHEMATICAL HELPERS ---
def get_safe_color(c):
    c = str(c).lower().strip()
    m = {"amber":"orange", "tungsten":"darkorange", "warm":"orange", "cool":"cyan", "daylight":"azure"}
    res = m.get(c, c)
    return res if mcolors.is_color_like(res) else "gold"

def get_clock_pos(lx, ly, sx, sy):
    dx, dy = lx - sx, ly - sy
    angle = np.degrees(np.arctan2(dy, dx)) % 360
    clocks = {90:12, 60:1, 30:2, 0:3, 330:4, 300:5, 270:6, 240:7, 210:8, 180:9, 150:10, 120:11}
    closest = min(clocks.keys(), key=lambda x:abs(x-angle))
    return clocks[closest]

# --- 4. DRAWING ENGINES ---
def draw_2d(data, rw, rd):
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)
    
    sub_x, sub_y = rw/2, rd*0.6
    cam_x, cam_y = rw/2, 0.5
    
    # Draw Subject & Camera with distinct shapes
    ax.scatter(sub_x, sub_y, color='yellow', s=300, edgecolors='black', marker='o', label="Subject", zorder=5)
    ax.text(sub_x, sub_y + 0.2, "YOU", ha='center', weight='bold')
    
    ax.scatter(cam_x, cam_y, color='blue', s=200, marker='s', label="Camera", zorder=5)
    ax.text(cam_x, cam_y - 0.3, "CAMERA", ha='center', color='blue', weight='bold')

    for l in data.get('lights', []):
        col = get_safe_color(l.get('color', 'gold'))
        lx, ly = l['x'], l['y']
        
        # Calculate Distance (2D for map label)
        dist_2d = np.sqrt((lx-sub_x)**2 + (ly-sub_y)**2)
        
        # Plot Light as Hexagon
        ax.scatter(lx, ly, color=col, s=250, marker='h', edgecolors='black', zorder=6)
        
        # Smart Annotation Placement (Avoid overwriting)
        v_align = 'bottom' if ly < sub_y else 'top'
        ax.text(lx, ly + (0.1 if ly < sub_y else -0.2), f"{l['id']}\n({dist_2d:.1f}m away)", 
                ha='center', color=col, weight='bold', fontsize=8)
        
        ax.annotate('', xy=(sub_x, sub_y), xytext=(lx, ly),
                    arrowprops=dict(arrowstyle='->', color=col, lw=2, alpha=0.6))

    st.pyplot(fig)

def draw_3d(data, rw, rd, rh):
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_zlim(0, rh)
    
    sub_x, sub_y, sub_z = rw/2, rd*0.6, 1.2
    ax.scatter(sub_x, sub_y, sub_z, color='yellow', s=200, edgecolors='black')
    ax.text(sub_x, sub_y, sub_z + 0.2, "SUBJECT")

    for l in data.get('lights', []):
        lx, ly, lz = l['x'], l['y'], l['z']
        col = get_safe_color(l.get('color', 'gold'))
        
        # Calculate 3D Distance & Vector Angle
        dx, dy, dz = sub_x-lx, sub_y-ly, sub_z-lz
        dist_3d = np.sqrt(dx**2 + dy**2 + dz**2)
        tilt_angle = np.degrees(np.arctan2(dz, np.sqrt(dx**2 + dy**2)))
        
        ax.quiver(lx, ly, lz, dx, dy, dz, color=col, length=0.8, normalize=True, alpha=0.6)
        ax.scatter(lx, ly, lz, color=col, s=100, edgecolors='black')
        ax.text(lx, ly, lz + 0.1, f"{l['id']}\n{tilt_angle:.0f}° Tilt", fontsize=8, color=col)

    ax.set_xlabel('X (Width)'); ax.set_ylabel('Y (Depth)'); ax.set_zlabel('Z (Height)')
    st.pyplot(fig)

# --- 5. REINFORCED AI ENGINE ---
def get_lighting_plan(w, d, h, gear, style):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    prompt = f"""
    Return ONLY a JSON for a {w}x{d}x{h}m room. Subject at {w/2}, {d*0.6}, 1.2. 
    Gear: {gear}. Style: {style}.
    Schema: {{
      "style": str,
      "lights": [{{
        "id": str, "x": float, "y": float, "z": float, "color": str, "strength": int, 
        "aiming": "detailed instruction", "logic": "why this works"
      }}],
      "reflectors": [{{ "id": "Whiteboard", "x": float, "y": float }}]
    }}
    """
    res = model.generate_content(prompt)
    json_match = re.search(r"\{.*\}", res.text, re.DOTALL)
    return json.loads(json_match.group())

# --- 6. EXECUTION & CHEATSHEET ---
if st.button("Generate Layout"):
    if not api_key:
        st.error("Enter API Key")
    else:
        try:
            plan = get_lighting_plan(r_w, r_d, r_h, gear, style)
            c1, c2 = st.columns(2)
            with c1: st.subheader("2D Setup Map"); draw_2d(plan, r_w, r_d)
            with c2: st.subheader("3D Perspective View"); draw_3d(plan, r_w, r_d, r_h)
            
            st.divider(); st.header("📋 Setup Cheatsheet")
            
            sub_x, sub_y, sub_z = r_w/2, r_d*0.6, 1.2
            
            for l in plan.get('lights', []):
                lx, ly, lz = l['x'], l['y'], l['z']
                dist_3d = np.sqrt((lx-sub_x)**2 + (ly-sub_y)**2 + (lz-sub_z)**2)
                clock = get_clock_pos(lx, ly, sub_x, sub_y)
                
                with st.expander(f"🔹 {l['id']} - {l.get('strength', 50)}% Power"):
                    st.write(f"**Distance:** Place light exactly **{dist_3d:.2f} meters** from the subject.")
                    st.write(f"**Horizontal Angle:** Set at your **{clock} o'clock** position.")
                    st.write(f"**Vertical Height:** Raise stand to **{lz:.1f}m**.")
                    st.write(f"**Aiming:** {l.get('aiming', 'Aim at subject.')}")
                    st.info(f"**The Logic:** {l.get('logic', 'Separates subject from background.')}")
        except Exception as e:
            st.error(f"Error: {e}")
