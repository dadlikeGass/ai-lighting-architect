# --- THE QUOTA-FRIENDLY VERSION ---
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import json
import re
import google.generativeai as genai

st.set_page_config(page_title="Lighting Architect Pro", layout="wide")
st.title("💡 Lighting Architect Pro")

api_key = st.secrets.get("GEMINI_KEY") or st.sidebar.text_input("Enter Gemini API Key", type="password")

# --- UI INPUTS ---
with st.sidebar:
    st.header("Room Dimensions")
    r_w = st.number_input("Width (X)", value=3.5)
    r_d = st.number_input("Depth (Y)", value=3.0)
    r_h = st.number_input("Height (Z)", value=2.8)
    st.divider()
    gear = st.text_area("Gear", "100W COB, 20W Stick, 80cm Whiteboard")
    style = st.selectbox("Vibe", ["Cinematic Moody", "Clean & Professional", "High-Contrast Noir"])

# --- DRAWING ENGINE (No changes needed) ---
def get_safe_color(c):
    c = str(c).lower().strip()
    m = {"amber":"orange", "tungsten":"darkorange", "warm":"orange", "cool":"cyan"}
    res = m.get(c, c)
    return res if mcolors.is_color_like(res) else "gold"

def get_clock_pos(lx, ly, sx, sy):
    dx, dy = lx - sx, ly - sy
    angle = np.degrees(np.arctan2(dy, dx)) % 360
    clocks = {90:12, 60:1, 30:2, 0:3, 330:4, 300:5, 270:6, 240:7, 210:8, 180:9, 150:10, 120:11}
    closest = min(clocks.keys(), key=lambda x:abs(x-angle))
    return clocks[closest]

def draw_2d(data, rw, rd):
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_aspect('equal')
    sub_x, sub_y = rw/2, rd*0.6
    ax.plot(sub_x, sub_y, 'yo', markersize=15); ax.plot(rw/2, 0.5, 'bs', markersize=10)
    for l in data.get('lights', []):
        col = get_safe_color(l.get('color', 'gold'))
        ax.plot(l['x'], l['y'], 'o', color=col); ax.annotate(l['id'], xy=(sub_x, sub_y), xytext=(l['x'], l['y']), arrowprops=dict(arrowstyle='->', color=col))
    st.pyplot(fig)

def draw_3d(data, rw, rd, rh):
    fig = plt.figure(figsize=(7, 6)); ax = fig.add_subplot(111, projection='3d')
    ax.set_xlim(0, rw); ax.set_ylim(0, rd); ax.set_zlim(0, rh)
    sub_x, sub_y, sub_z = rw/2, rd*0.6, 1.2
    ax.scatter(sub_x, sub_y, sub_z, color='yellow', s=100)
    for l in data.get('lights', []):
        col = get_safe_color(l.get('color', 'gold'))
        ax.quiver(l['x'], l['y'], l['z'], sub_x-l['x'], sub_y-l['y'], sub_z-l['z'], color=col, length=0.8, normalize=True)
    st.pyplot(fig)

# --- REINFORCED AI ENGINE (Switched to Flash-Lite) ---
def get_lighting_plan(w, d, h, gear, style):
    genai.configure(api_key=api_key)
    # SWITCHED TO LITE MODEL FOR HIGHER QUOTA
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    prompt = f"Return ONLY a JSON for a {w}x{d}x{h}m room. Subject at {w/2}, {d*0.6}, 1.2. Gear: {gear}. Style: {style}. Schema: {{'style': str, 'lights': [{{'id': str, 'x': float, 'y': float, 'z': float, 'color': str, 'strength': int, 'logic': str}}]}}"
    
    res = model.generate_content(prompt)
    json_match = re.search(r"\{.*\}", res.text, re.DOTALL)
    return json.loads(json_match.group()) if json_match else json.loads(res.text)

# --- EXECUTION ---
if st.button("Generate Layout"):
    if not api_key:
        st.error("Enter API Key")
    else:
        try:
            plan = get_lighting_plan(r_w, r_d, r_h, gear, style)
            colA, colB = st.columns(2)
            with colA: st.subheader("Top View"); draw_2d(plan, r_w, r_d)
            with colB: st.subheader("3D View"); draw_3d(plan, r_w, r_d, r_h)
            
            st.divider(); st.header("📋 Setup Cheatsheet")
            for l in plan.get('lights', []):
                clock = get_clock_pos(l['x'], l['y'], r_w/2, r_d*0.6)
                with st.expander(f"🔹 {l['id']} - {l.get('strength', 50)}% Power"):
                    st.write(f"**Horizontal:** {clock} o'clock | **Height:** {l.get('z', 1.5):.1f}m")
                    st.info(f"**Logic:** {l.get('logic', 'Adds depth.')}")
        except Exception as e:
            if "429" in str(e):
                st.error("⚠️ Quota Exceeded! Please wait 60 seconds and try again. Flash-Lite has a limited 'per minute' cap.")
            else:
                st.error(f"Error: {e}")
