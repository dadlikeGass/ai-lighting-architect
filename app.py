import streamlit as st
import matplotlib.pyplot as plt
import json
import google.generativeai as genai

# 1. Page Config
st.set_page_config(page_title="Lighting Architect", layout="centered")
st.title("💡 AI Lighting Architect")

# 2. Get API Key from Secrets (Better for Security)
# On Streamlit Cloud, go to 'Settings' -> 'Secrets' and add: GEMINI_KEY = "your-key-here"
api_key = st.secrets.get("GEMINI_KEY") or st.sidebar.text_input("Enter Gemini API Key", type="password")

# 3. User Inputs
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        room_w = st.number_input("Room Width (m)", value=3.5)
        room_h = st.number_input("Room Depth (m)", value=3.0)
    with col2:
        gear = st.text_area("Your Gear", value="100W COB, 20W Stick, Whiteboard")
        style = st.selectbox("Vibe", ["Cinematic Moody", "Clean & Professional"])

# 4. Gemini Logic
def get_lighting_plan(w, d, gear, style):
    genai.configure(api_key=api_key)
    # Using 'gemini-1.5-flash' for high speed and free tier stability
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Act as a Cinematographer. Create a lighting plan for a {w}x{d}m room.
    Subject is at x={w/2}, y={d*0.6}. Camera is at x={w/2}, y=0.5.
    Output ONLY valid JSON. 
    JSON Structure: 
    {{
        "lights": [
            {{"id": "Key Light", "x": 2.8, "y": 1.0, "color": "red"}},
            {{"id": "Rim Light", "x": 0.5, "y": 2.5, "color": "green"}}
        ]
    }}
    Gear: {gear}. Style: {style}.
    """
    
    response = model.generate_content(prompt)
    # Clean up the response text in case Gemini adds ```json markdown
    json_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(json_text)

# 5. Plotting
def draw_map(data, rw, rh):
    fig, ax = plt.subplots(figsize=(8,6))
    ax.set_xlim(0, rw); ax.set_ylim(0, rh)
    ax.set_aspect('equal')
    # Subject & Camera
    ax.plot(rw/2, rh*0.6, 'yo', markersize=20, label="Subject")
    ax.plot(rw/2, 0.5, 'bs', markersize=12, label="Camera")
    # Lights
    for l in data['lights']:
        ax.plot(l['x'], l['y'], 'o', color=l['color'], markersize=12, label=l['id'])
        ax.annotate('', xy=(rw/2, rh*0.6), xytext=(l['x'], l['y']),
                    arrowprops=dict(arrowstyle='->', color=l['color'], alpha=0.5))
    st.pyplot(fig)

# 6. Button
if st.button("Generate Lighting Layout"):
    if not api_key:
        st.warning("Please provide an API key in the sidebar or Secrets.")
    else:
        try:
            plan = get_lighting_plan(room_w, room_h, gear, style)
            draw_map(plan, room_w, room_h)
            st.success("Plan generated!")
        except Exception as e:
            st.error(f"Error: {e}")
