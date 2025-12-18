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
    st.header("Room Dimensions")
    r_w = st.number_input("Width (X) in meters", value=3.5)
    r_d = st.number_input("Depth (Y) in meters", value=3.0)
    r_h = st.number_input("Height (Z) in meters", value=2.8)
    st.divider()
    gear = st.text_area("Your Gear", "100W COB light, 20W Stick light, 80cm Whiteboard")
    style = st.selectbox("Style Vibe", ["Cinematic Moody", "Clean & Professional", "High-Contrast Noir"])

# --- 3. LOGIC & CLEANING FUNCTIONS ---
def get_safe_color(c):
    c = str(c).lower().strip()
    m = {"amber":"orange", "tungsten":"darkorange", "warm":"orange", "cool":"cyan", "daylight":"azure"}
    res = m.get(c, c)
    return res if mcolors.is_color_like(res) else "gold"

def get_clock_pos(lx, ly, sx, sy):
    dx, dy = lx - sx, ly - sy
    angle = np.degrees(np.arctan2(dy, dx)) % 360
    # Map degrees to clock positions (Approximate)
    clocks = {90:12, 60:1, 30:2, 0:3, 330:4, 300:5, 270:6, 240:7, 210:8, 180:9, 150:10, 120:11}
    closest = min(clocks.keys(), key=lambda x:abs(x-angle))
    return clocks[closest]

# --- 4. DRAWING ENGINES ---
def draw_2d(data, rw, rd):
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)
    sub_x, sub_y = rw/2, rd*0.6
    ax.plot(sub_x, sub_y, 'yo', markersize=15, label="Subject")
    ax.plot(rw/2, 0.5, 'bs', markersize=10, label="Camera")
    for l in data.get('lights', []):
        col = get_safe_color(l.get('color', 'gold'))
        ax.plot(l['x'], l['y'], 'o', color=col, markersize=10)
        ax.annotate(l['id'], xy=(sub_x, sub_y), xytext=(l['x'], l['y']),
                    arrowprops=dict(arrowstyle='->', color=col, lw=2))
    st.pyplot(fig)

def draw_3d(data, rw, rd, rh):
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_zlim(0, rh)
    sub_x, sub_y, sub_z = rw/2, rd*0.6, 1.2
    ax.scatter(sub_x, sub_y, sub_z, color='yellow', s=100)
    for l in data.get('lights', []):
        col = get_safe_color(l.get('color', 'gold'))
        ax.quiver(l['x'], l['y'], l['z'], sub_x-l['x'], sub_y-l['y'], sub_z-l['z'], 
                  color=col, length=0.8, normalize=True)
        ax.scatter(l['x'], l['y'], l['z'], color=col, s=50)
    st.pyplot(fig)

# --- 5. THE REINFORCED AI ENGINE ---
def get_lighting_plan(w, d, h, gear, style):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Stricter JSON-only prompt
    prompt = f"""
    Return ONLY a JSON object for a {w}x{d}x{h}m room. No conversational text.
    Subject at {w/2}, {d*0.6}, 1.2.
    Schema: {{"style": "{style}", "lights": [{{"id": "Key", "x": 1, "y": 1, "z": 1.8, "color": "orange", "strength": 80, "logic": "Place at 4 o'clock"}}]}}
    Gear: {gear}. Use realistic positions.
    """
    
    res = model.generate_content(prompt)
    text = res.text
    
    # JSON EXTRACTION SHIELD: Finds the first '{' and last '}'
    try:
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(text) # Fallback
    except Exception as e:
        st.error("AI sent malformed data. Try clicking generate again.")
        raise e

# --- 6. EXECUTION ---
if st.button("Generate Layout"):
    if not api_key:
        st.error("Please enter a Gemini API Key in the sidebar.")
    else:
        try:
            plan = get_lighting_plan(r_w, r_d, r_h, gear, style)
            c1, c2 = st.columns(2)
            with c1: st.subheader("Top View (2D)"); draw_2d(plan, r_w, r_d)
            with c2: st.subheader("Perspective (3D)"); draw_3d(plan, r_w, r_d, r_h)
            
            st.divider()
            st.header("📋 Setup Cheatsheet")
            for l in plan.get('lights', []):
                clock = get_clock_pos(l['x'], l['y'], r_w/2, r_d*0.6)
                with st.expander(f"🔹 {l['id']} - {l.get('strength', 50)}% Power"):
                    st.write(f"**Horizontal:** Place at your **{clock} o'clock** position.")
                    st.write(f"**Vertical:** Set stand height to **{l.get('z', 1.5):.1f}m**.")
                    st.write(f"**Aiming:** Point light directly at the subject.")
                    st.info(f"**The Logic:** {l.get('logic', 'Adds separation and depth.')}")
        except Exception as e:
            st.error(f"Failed to parse AI output. Error: {e}")
