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

# --- 2. STRUCTURED GEAR INPUTS ---
with st.sidebar:
    st.header("📏 Room Dimensions")
    r_w = st.number_input("Width (X) in m", value=3.5)
    r_d = st.number_input("Depth (Y) in m", value=3.0)
    r_h = st.number_input("Height (Z) in m", value=2.8)
    
    st.divider()
    st.header("📸 Gear Inventory")
    gear_main = st.text_input("Main Light (e.g. 100W COB)", "100W COB light")
    gear_secondary = st.text_input("Secondary Light (e.g. 20W Stick)", "20W Stick light")
    gear_mod = st.text_input("Modifiers/Reflectors", "80cm Whiteboard")
    
    style = st.selectbox("Style Vibe", ["Cinematic Moody", "Clean & Professional", "High-Contrast Noir"])

# --- 3. MATHEMATICAL HELPERS ---
def get_safe_color(c):
    c = str(c).lower().strip()
    m = {"amber":"orange", "tungsten":"darkorange", "warm":"orange", "cool":"cyan", "daylight":"azure"}
    res = m.get(c, c)
    return res if mcolors.is_color_like(res) else "gold"

# --- 4. DRAWING ENGINES ---
def draw_2d(data, rw, rd):
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)
    
    sub_x, sub_y = rw/2, rd*0.6
    ax.scatter(sub_x, sub_y, color='yellow', s=300, edgecolors='black', marker='o', zorder=5)
    ax.text(sub_x, sub_y + 0.2, "YOU", ha='center', weight='bold')
    
    # Draw Lights
    for l in data.get('lights', []):
        col = get_safe_color(l.get('color', 'gold'))
        ax.scatter(l['x'], l['y'], color=col, s=250, marker='h', edgecolors='black', zorder=6)
        ax.annotate(l['id'], xy=(sub_x, sub_y), xytext=(l['x'], l['y']),
                    arrowprops=dict(arrowstyle='->', color=col, lw=2, alpha=0.6))

    # Draw Whiteboard
    for r in data.get('reflectors', []):
        ax.plot([r['x']-0.4, r['x']+0.4], [r['y'], r['y']], color='gray', lw=5, solid_capstyle='round')
        ax.text(r['x'], r['y']+0.1, "WHITEBOARD", ha='center', fontsize=8, weight='bold')

    st.pyplot(fig)

def draw_3d(data, rw, rd, rh):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_zlim(0, rh)
    
    sub_x, sub_y, sub_z = rw/2, rd*0.6, 1.2
    ax.scatter(sub_x, sub_y, sub_z, color='yellow', s=150, edgecolors='black')
    ax.text(sub_x, sub_y, sub_z + 0.15, f"YOU (H:{sub_z}m)", ha='center')

    for l in data.get('lights', []):
        lx, ly, lz = l['x'], l['y'], l['z']
        col = get_safe_color(l.get('color', 'gold'))
        
        # Calculations
        dx, dy, dz = sub_x-lx, sub_y-ly, sub_z-lz
        hor_angle = np.degrees(np.arctan2(dy, dx)) % 360
        tilt_angle = np.degrees(np.arctan2(dz, np.sqrt(dx**2 + dy**2)))
        
        # Plotting
        ax.scatter(lx, ly, lz, color=col, s=100, edgecolors='black')
        ax.quiver(lx, ly, lz, dx, dy, dz, color=col, length=0.8, normalize=True, alpha=0.5)
        
        label = f"{l['id']}\nH:{lz}m\nHor:{hor_angle:.0f}°\nTilt:{tilt_angle:.0f}°"
        ax.text(lx, ly, lz + 0.2, label, fontsize=8, color='black', weight='bold', ha='center')

    ax.set_xlabel('Width (X)'); ax.set_ylabel('Depth (Y)'); ax.set_zlabel('Height (Z)')
    st.pyplot(fig)

# --- 5. THE REINFORCED AI ENGINE ---
def get_lighting_plan(w, d, h, g1, g2, g3, style):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    full_gear = f"Main: {g1}, Secondary: {g2}, Modifiers: {g3}"
    prompt = f"""
    Return ONLY a JSON for a {w}x{d}x{h}m room. Subject at {w/2}, {d*0.6}, 1.2.
    Gear: {full_gear}. Style: {style}.
    Schema: {{
      "style": str,
      "lights": [{{ "id": str, "x": float, "y": float, "z": float, "color": str, "strength": int, "logic": str }}],
      "reflectors": [{{ "id": str, "x": float, "y": float, "z": float }}]
    }}
    """
    res = model.generate_content(prompt)
    json_match = re.search(r"\{.*\}", res.text, re.DOTALL)
    return json.loads(json_match.group())

# --- 6. EXECUTION ---
if st.button("Generate Technical Layout"):
    if not api_key:
        st.error("Enter API Key")
    else:
        try:
            plan = get_lighting_plan(r_w, r_d, r_h, gear_main, gear_secondary, gear_mod, style)
            c1, c2 = st.columns(2)
            with c1: st.subheader("Top View Map"); draw_2d(plan, r_w, r_d)
            with c2: st.subheader("3D Coordinate View"); draw_3d(plan, r_w, r_d, r_h)
            
            st.divider(); st.header("📋 Setup Cheatsheet")
            for l in plan.get('lights', []):
                with st.expander(f"🔹 {l['id']} - {l.get('strength', 50)}% Power"):
                    st.write(f"**Coordinates:** X:{l['x']}m, Y:{l['y']}m, Z:{l['z']}m")
                    st.info(f"**Strategy:** {l.get('logic', 'Optimize for style.')}")
        except Exception as e:
            st.error(f"Error: {e}")
