import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import numpy as np
import json
import google.generativeai as genai

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="AI Lighting Architect", layout="centered")
st.title("💡 AI Lighting Architect")
st.markdown("Professional cinematic lighting blueprints for small spaces.")

# Secure API Key Entry (Checks Secrets first, then Sidebar)
api_key = st.secrets.get("GEMINI_KEY") or st.sidebar.text_input("Enter Gemini API Key", type="password")

# --- 2. USER INPUTS (Now with 3D Room Size) ---
with st.container():
    col1, col2, col3 = st.columns(3)
    with col1:
        r_width = st.number_input("Width (X)", value=3.5, min_value=1.0, step=0.1, help="Left to Right wall")
    with col2:
        r_depth = st.number_input("Depth (Y)", value=3.0, min_value=1.0, step=0.1, help="Front to Back wall")
    with col3:
        r_height = st.number_input("Height (Z)", value=2.8, min_value=2.0, step=0.1, help="Floor to Ceiling")

    gear = st.text_area("Your Gear", value="100W COB light, 20W Stick light, 80cm Whiteboard")
    style = st.selectbox("Style / Vibe", ["Cinematic Moody", "Clean & Professional", "High-Contrast Noir"])

# --- 3. HELPER: COLOR SANITIZER (Prevents Crashes) ---
def get_safe_color(color_name):
    """Converts AI color names (e.g., 'Amber') to valid Python colors."""
    color_name = str(color_name).lower().strip()
    custom_map = {
        "amber": "orange", "tungsten": "darkorange", "warm": "orange",
        "cool": "cyan", "daylight": "azure", "bi-color": "y"
    }
    if color_name in custom_map: return custom_map[color_name]
    if mcolors.is_color_like(color_name): return color_name
    return "gold" # Fallback

# --- 4. THE DRAWING ENGINE (2D Map + Z-Height Labels) ---
def draw_map(data, rw, rd, rh):
    """Generates the 2D sketch but lists 3D height in the summary."""
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, rw)
    ax.set_ylim(0, rd)
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)

    # A. SUBJECT (You) - Placed at 60% depth
    sub_x, sub_y = rw / 2, rd * 0.6
    ax.plot(sub_x, sub_y, 'yo', markersize=22, label="Subject", zorder=5)
    ax.text(sub_x, sub_y + 0.25, "SUBJECT (YOU)", ha='center', weight='bold', fontsize=10)

    # B. CAMERA - Placed at front
    cam_x, cam_y = rw / 2, 0.5
    ax.plot(cam_x, cam_y, 'bs', markersize=14, label="Camera", zorder=5)
    ax.text(cam_x, cam_y - 0.3, "CAMERA", ha='center', color='blue', weight='bold')

    # C. LIGHT SOURCES
    details_list = []
    for l in data.get('lights', []):
        lx, ly, lz = l['x'], l['y'], l.get('z', 1.5) # Default to 1.5m if Z missing
        l_id = l['id']
        
        # Color Safe Check
        raw_color = l.get('color', 'gold')
        l_col = get_safe_color(raw_color)
        
        # Plot Light Icon
        ax.plot(lx, ly, 'o', color=l_col, markersize=14, zorder=6)
        
        # Calculate Angle
        dx, dy = sub_x - lx, sub_y - ly
        angle_deg = np.degrees(np.arctan2(dy, dx)) % 360
        
        # Draw Arrow
        ax.annotate(l_id.upper(), xy=(sub_x, sub_y), xytext=(lx, ly),
                    arrowprops=dict(arrowstyle='->', color=l_col, lw=2.5, shrinkB=15),
                    ha='center', va='bottom', color=l_col, weight='bold', fontsize=9)
        
        # Append 3D details to summary list
        details_list.append(f"• {l_id.upper()}: Pos({lx:.1f}, {ly:.1f}) | Height: {lz:.1f}m | Aim: {angle_deg:.0f}°")

    # D. REFLECTOR (Whiteboard)
    for r in data.get('reflectors', []):
        rx, ry = r['x'], r['y']
        rect = patches.Rectangle((rx-0.4, ry-0.05), 0.8, 0.1, color='gray', alpha=0.6, zorder=4)
        ax.add_patch(rect)
        ax.text(rx, ry + 0.15, "WHITEBOARD", ha='center', fontsize=8, color='gray', weight='bold')

    # E. SUMMARY BOX
    info_str = f"ROOM: {rw}x{rd}x{rh}m\nSTYLE: {data.get('style', style)}\n" + "\n".join(details_list)
    props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='lightgray')
    ax.text(0.02, 0.02, info_str, transform=ax.transAxes, fontsize=9,
            verticalalignment='bottom', bbox=props, family='monospace')

    plt.title("AI LIGHTING BLUEPRINT (TOP-DOWN)", fontsize=15, pad=20, weight='bold')
    st.pyplot(fig)

# --- 5. THE AI ENGINE (Gemini 2.5) ---
def get_lighting_plan(w, d, h, gear_list, style_name):
    genai.configure(api_key=api_key)
    
    # UPDATED MODEL VERSION TO 2.5
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Act as a professional Cinematographer. Create a 3D lighting plan for a room {w}m wide x {d}m deep x {h}m high.
    Subject Position: x={w/2}, y={d*0.6}, z=1.2 (seated).
    
    Return ONLY a JSON object. No markdown.
    {{
      "style": "{style_name}",
      "lights": [
        {{"id": "Key Light", "x": {w-0.5}, "y": 0.8, "z": 1.8, "color": "orange"}},
        {{"id": "Rim Light", "x": 0.5, "y": {d-0.5}, "z": 2.0, "color": "cyan"}}
      ],
      "reflectors": [
        {{"id": "Whiteboard", "x": {w*0.7}, "y": 1.2, "z": 1.2}}
      ]
    }}
    
    Gear: {gear_list}. Style: {style_name}.
    Constraints: 
    - Keep x between 0 and {w}.
    - Keep y between 0 and {d}.
    - Keep z between 0 and {h}.
    """
    
    response = model.generate_content(prompt)
    clean_json = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_json)

# --- 6. EXECUTION ---
if st.button("Generate Lighting Layout"):
    if not api_key:
        st.warning("Please enter a Gemini API Key in the sidebar or Secrets.")
    else:
        try:
            with st.spinner("Calculating 3D Angles..."):
                # Pass all 3 dimensions to the AI
                plan_data = get_lighting_plan(r_width, r_depth, r_height, gear, style)
                draw_map(plan_data, r_width, r_depth, r_height)
                st.success("Blueprint Generated! Check the 'Height' in the summary box.")
        except Exception as e:
            st.error(f"Error: {e}")
