import streamlit as st
import matplotlib.pyplot as plt
import json
from openai import OpenAI

# 1. Page Configuration
st.set_page_config(page_title="AI Lighting Architect", layout="centered")
st.title("💡 AI Lighting Architect")
st.markdown("Enter your gear and room details to get a cinematic lighting map.")

# 2. Sidebar for API Key (Security)
with st.sidebar:
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    st.info("Your key is not stored. It is only used for this session.")

# 3. User Inputs
col1, col2 = st.columns(2)
with col1:
    room_w = st.number_input("Room Width (m)", value=3.5)
    room_h = st.number_input("Room Depth (m)", value=3.0)
with col2:
    gear = st.text_area("List your gear", value="100W COB light, 20W Stick light, 80cm Whiteboard")
    style = st.selectbox("Video Style", ["Cinematic Moody", "Bright & Clean", "Dark Background"])

# 4. The AI Function
def get_lighting_plan(width, depth, gear_list, style_name):
    client = OpenAI(api_key=api_key)
    
    system_prompt = f"""
    You are a Cinematography Expert. Create a lighting plan for a {width}x{depth}m room.
    Output ONLY a JSON object with this structure:
    {{
        "style": "{style_name}",
        "subject": {{"x": {width/2}, "y": {depth*0.6}}},
        "camera": {{"x": {width/2}, "y": 0.5}},
        "lights": [
            {{"id": "Key", "x": 2.5, "y": 1.0, "target_x": 1.75, "target_y": 1.8, "color": "red"}},
            {{"id": "Rim", "x": 0.5, "y": 2.5, "target_x": 1.75, "target_y": 1.8, "color": "green"}}
        ]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": f"Gear: {gear_list}"}],
        response_format={ "type": "json_object" }
    )
    return json.loads(response.choices[0].message.content)

# 5. The Plotting Logic
def plot_map(data):
    fig, ax = plt.subplots()
    ax.set_xlim(0, room_w)
    ax.set_ylim(0, room_h)
    ax.set_aspect('equal')
    
    # Plot Subject & Camera
    ax.plot(data['subject']['x'], data['subject']['y'], 'yo', markersize=15, label="You")
    ax.plot(data['camera']['x'], data['camera']['y'], 'bs', label="Camera")
    
    # Plot Lights
    for l in data['lights']:
        ax.plot(l['x'], l['y'], marker='o', color=l['color'], label=l['id'])
        ax.annotate('', xy=(l['target_x'], l['target_y']), xytext=(l['x'], l['y']),
                    arrowprops=dict(arrowstyle='->', color=l['color']))
    
    st.pyplot(fig)

# 6. Run the App
if st.button("Generate Layout"):
    if not api_key:
        st.error("Please enter an API key in the sidebar.")
    else:
        with st.spinner("Calculating light paths..."):
            plan = get_lighting_plan(room_w, room_h, gear, style)
            st.success(f"Plan Generated: {plan['style']}")
            plot_map(plan)
