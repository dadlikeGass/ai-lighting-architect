import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import json
import google.generativeai as genai

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="AI Lighting Architect", layout="centered")
st.title("💡 AI Lighting Architect")
st.markdown("Professional cinematic lighting blueprints for small spaces.")

# Secure API Key Entry
# Checks Streamlit Secrets first, then falls back to sidebar input
api_key = st.secrets.get("GEMINI_KEY") or st.sidebar.text_input("Enter Gemini API Key", type="password")

# --- 2. USER INPUTS ---
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        # Room dimensions with min/max constraints
        room_w = st.number_input("Room Width (meters)", value=3.5, min_value=1.0, step=0.1)
        room_h = st.number_input("Room Depth (meters)", value=3.0, min_value=1.0, step=0.1)
    with col2:
        gear = st.text_area("Your Lighting Gear", value="100W COB light, 20W Stick light, 80cm Whiteboard")
        style = st.selectbox("Style / Vibe", ["Cinematic Moody", "Clean & Professional", "High-Contrast Noir"])

# --- 3. THE UPDATED DRAWING ENGINE ---
def draw_map(data, rw, rh):
    """Generates the 2D sketch with labels and math-based angles."""
    # Create the figure
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, rw)
    ax.set_ylim(0, rh)
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)

    # A. SUBJECT (You)
    # Placed slightly back from center (60% depth)
    sub_x, sub_y = rw / 2, rh * 0.6
    ax.plot(sub_x, sub_y, 'yo', markersize=22, label="Subject", zorder=5)
    ax.text(sub_x, sub_y + 0.25, "SUBJECT (YOU)", ha='center', weight='bold', fontsize=10)

    # B. CAMERA
    # Placed at the front (y=0.5m)
    cam_x, cam_y = rw / 2, 0.5
    ax.plot(cam_x, cam_y, 'bs', markersize=14, label="Camera", zorder=5)
    ax.text(cam_x, cam_y - 0.3, "CAMERA", ha='center', color='blue', weight='bold')

    # C. LIGHT SOURCES & ANNOTATIONS
    details_list = []
    # Loop through lights provided by AI
    for l in data.get('lights', []):
        lx, ly, l_id, l_col = l['x'], l['y'], l['id'], l['color']
        
        # Plot Light Icon
        ax.plot(lx, ly, 'o', color=l_col, markersize=14, zorder=6)
        
        # Calculate Math Angle toward Subject
        dx, dy = sub_x - lx, sub_y - ly
        angle_rad = np.arctan2(dy, dx)
        angle_deg = np.degrees(angle_rad) % 360
        
        # Draw Label & Arrow
        ax.annotate(l_id.upper(), xy=(sub_x, sub_y), xytext=(lx, ly),
                    arrowprops=dict(arrowstyle='->', color=l_col, lw=2.5, shrinkB=15),
                    ha='center', va='bottom', color=l_col, weight='bold', fontsize=9)
        
        details_list.append(f"• {l_id.upper()}: Pos({lx:.1f}m, {ly:.1f}m) | Aim: {angle_deg:.0f}°")

    # D. REFLECTOR (Whiteboard)
    # Loop through reflectors provided by AI
    for r in data.get('reflectors', []):
        rx, ry = r['x'], r['y']
        # Represented as a 0.8m thick gray line using a Rectangle patch
        rect = patches.Rectangle((rx-0.4, ry-0.05), 0.8, 0.1, color='gray', alpha=0.6, zorder=4)
        ax.add_patch(rect)
        ax.text(rx, ry + 0.15, "WHITEBOARD", ha='center', fontsize=8, color='gray', weight='bold')

    # E. CHEAT SHEET SUMMARY BOX
    info_str = f"PLAN: {data.get('style', style)}\n" + "\n".join(details_list)
    props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='lightgray')
    ax.text(0.02, 0.02, info_str, transform=ax.transAxes, fontsize=9,
            verticalalignment='bottom', bbox=props, family='monospace')

    plt.title("AI LIGHTING BLUEPRINT (TOP-DOWN)", fontsize=15, pad=20, weight='bold')
    st.pyplot(fig)

# --- 4. THE AI ENGINE (GEMINI) ---
def get_lighting_plan(w, d, gear_list, style_name):
    genai.configure(api_key=api_key)
    
    # Using standard stable model
    # If this fails, try 'gemini-1.5-pro' or check API key permissions
  
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Act as a professional Cinematographer. Create a 2D lighting plan for a room {w}m wide x {d}m deep.
    Subject: ({w/2}, {d*0.6}). Camera: ({w/2}, 0.5).
    
    Return ONLY a JSON object:
    {{
      "style": "{style_name}",
      "lights": [
        {{"id": "Key Light", "x": {w-0.5}, "y": 0.8, "color": "red"}},
        {{"id": "Rim Light", "x": 0.5, "y": {d-0.5}, "color": "green"}}
      ],
      "reflectors": [
        {{"id": "Whiteboard", "x": {w*0.7}, "y": 1.2}}
      ]
    }}
    
    Gear: {gear_list}. Style: {style_name}. Keep all coordinates within (0,0) to ({w}, {d}).
    """
    
    response = model.generate_content(prompt)
    # Clean up the JSON string from any markdown formatting
    clean_json = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_json)

# --- 5. MAIN EXECUTION ---
if st.button("Generate Lighting Layout"):
    if not api_key:
        st.warning("Please enter a Gemini API Key in the sidebar or Secrets.")
    else:
        try:
            with st.spinner("AI Director is placing the stands..."):
                plan_data = get_lighting_plan(room_w, room_h, gear, style)
                draw_map(plan_data, room_w, room_h)
                st.success("Sketch generated! Use the 'Aim' angles to point your lights.")
        except Exception as e:
            st.error(f"Error: {e}")
