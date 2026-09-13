import os
import time
import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image  
from google import genai
from google.genai import types
from weather import get_live_weather

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Shetkari AI - Multimodal Crop Assistant", 
    page_icon="🌾", 
    layout="wide"
)

# Custom Vanilla CSS (Guaranteed to work in Streamlit without script dependencies)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Top Sticky Header */
    .header-banner {
        background: linear-gradient(135deg, #022c22 0%, #064e3b 100%);
        color: white;
        padding: 18px 24px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .header-title-container {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .header-logo {
        background: linear-gradient(135deg, #10b981 0%, #e5a93c 100%);
        width: 44px;
        height: 44px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
    }
    .header-text h1 {
        margin: 0;
        font-size: 22px;
        font-weight: 800;
        color: #ffffff !important;
    }
    .header-text p {
        margin: 0;
        font-size: 12px;
        color: #a7f3d0 !important;
    }

    /* Weather Card inside Header */
    .weather-box {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 8px 16px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .weather-temp {
        font-size: 18px;
        font-weight: 700;
        color: #ffffff !important;
    }
    .weather-details {
        font-size: 12px;
        color: #dcfce7 !important;
        border-left: 1px solid rgba(255,255,255,0.2);
        padding-left: 12px;
    }

    /* Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, #064e3b 0%, #047857 100%);
        color: white;
        padding: 24px 30px;
        border-radius: 20px;
        margin-bottom: 24px;
    }
    .hero-banner h2 {
        font-size: 24px;
        font-weight: 800;
        margin-top: 6px;
        margin-bottom: 8px;
        color: #ffffff !important;
    }
    .hero-banner p {
        font-size: 14px;
        color: #dcfce7 !important;
        margin: 0;
    }

    /* Section Headers */
    .section-title {
        font-size: 18px;
        font-weight: 700;
        color: #022c22 !important;
        margin-bottom: 4px;
    }
    .section-subtitle {
        font-size: 12px;
        color: #64748b !important;
        margin-bottom: 16px;
    }

    /* Results Card */
    .result-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-top: 10px;
    }
    
    /* Input Label Overrides */
    div[data-widget-label="true"], .stTextInput label, .stTextArea label, .stFileUploader label {
        color: #0f172a !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }

    /* Primary Button Styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #10b981 0%, #047857 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 10px 20px !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. API & Client Configuration
# -----------------------------------------------------------------------------
api_key = None

try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ GEMINI_API_KEY is missing! Please add it to .streamlit/secrets.toml")
    st.stop()

client = genai.Client(api_key=api_key)

SYSTEM_PROMPT = """
You are an expert agricultural assistant for rural farmers in India.
Your job is to provide short, accurate, and easy-to-understand advice about:
- Crop diseases and pest management (including analyzing images of damaged plants/leaves)
- Fertilizers and soil health
- Weather precautions, irrigation, and preventive spraying based on live weather data.

Always respond structured with clear bullet points and bold headers.
Respond using the same language the farmer uses (e.g., Marathi, Hindi, English).
"""

PRIMARY_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-3.6-flash"

def generate_content_with_retry(contents: list) -> str:
    config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.3)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=PRIMARY_MODEL, contents=contents, config=config)
            return response.text
        except Exception as e:
            if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                break
    try:
        response = client.models.generate_content(model=FALLBACK_MODEL, contents=contents, config=config)
        return response.text
    except Exception as final_err:
        raise final_err

# -----------------------------------------------------------------------------
# 3. Header & Weather Component
# -----------------------------------------------------------------------------
if 'current_location' not in st.session_state:
    st.session_state.current_location = "Buldhana"

weather_info = get_live_weather(st.session_state.current_location)
temp_disp = f"{weather_info.get('temp', '28')}°C" if "error" not in weather_info else "N/A"
hum_disp = f"{weather_info.get('humidity', '72')}%" if "error" not in weather_info else "N/A"
cond_disp = weather_info.get('condition', 'Partly Cloudy').capitalize() if "error" not in weather_info else "Data N/A"

st.markdown(f"""
<div class="header-banner">
    <div class="header-title-container">
        <div class="header-logo">🌾</div>
        <div class="header-text">
            <h1>Shetkari AI <span style="font-size:12px; opacity:0.8; font-weight:normal;">Pro v2.5</span></h1>
            <p>Smart Multimodal Crop Assistant & Diagnostics</p>
        </div>
    </div>
    <div class="weather-box">
        <div>
            <div style="font-size:11px; opacity:0.8;">📍 {st.session_state.current_location}, MH</div>
            <div class="weather-temp">{temp_disp}</div>
        </div>
        <div class="weather-details">
            <div>💧 Humidity: <strong>{hum_disp}</strong></div>
            <div>🌤️ Condition: <strong>{cond_disp}</strong></div>
        </div>
    </div>
</div>

<div class="hero-banner">
    <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.9;">✨ AI-Powered Crop Care</div>
    <h2>Instant Crop Disease Diagnosis & Regional Advisory</h2>
    <p>Upload a leaf photo or enter your crop question in Marathi, Hindi, or English to get instant, AI-guided treatments tailored for your field weather.</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. Form Inputs vs AI Output Grid
# -----------------------------------------------------------------------------
left_col, right_col = st.columns([5, 7], gap="large")

with left_col:
    st.markdown("""
    <div class="section-title">📍 Select Location / ठिकाण निवडा</div>
    """, unsafe_allow_html=True)

    location_input = st.text_input("Location Input", st.session_state.current_location, label_visibility="collapsed")
    if location_input != st.session_state.current_location:
        st.session_state.current_location = location_input
        st.rerun()

    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    if q_col1.button("Buldhana", key="b1"):
        st.session_state.current_location = "Buldhana"
        st.rerun()
    if q_col2.button("Khamgaon", key="b2"):
        st.session_state.current_location = "Khamgaon"
        st.rerun()
    if q_col3.button("Malkapur", key="b3"):
        st.session_state.current_location = "Malkapur"
        st.rerun()
    if q_col4.button("Shegaon", key="b4"):
        st.session_state.current_location = "Shegaon"
        st.rerun()

    user_query = st.text_area(
        "💬 Describe Symptoms / काय अडचण आहे?",
        placeholder="e.g. कापसाच्या पानांवर पिवळे ठिपके दिसत आहेत किंवा कोणती फवारणी करावी?",
        height=100
    )

    uploaded_file = st.file_uploader(
        "📷 Upload Plant Leaf Image / रोपाचा फोटो टाका",
        type=["jpg", "jpeg", "png"]
    )

    image = None
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Crop Image", use_container_width=True)

    submit_btn = st.button("Get AI Advice / सल्ला मिळवा", type="primary", use_container_width=True)

with right_col:
    st.markdown("""
    <div class="section-title">🤖 AI Advisory Result</div>
    <div class="section-subtitle">Powered by Gemini Multimodal Reasoning</div>
    """, unsafe_allow_html=True)

    if submit_btn:
        if not user_query.strip() and image is None:
            st.warning("Please enter a question or upload an image! / कृपया प्रश्न टाका किंवा फोटो अपलोड करा!")
        else:
            with st.spinner("Analyzing Crop & Weather Data..."):
                try:
                    contents = []
                    if image:
                        contents.append(image)

                    weather_context = ""
                    if "error" not in weather_info:
                        weather_context = f"\n[Live Weather Data: {weather_info['raw_text']}]"

                    prompt_text = user_query.strip() if user_query.strip() else "Please analyze this crop/leaf image for diseases, pests, or deficiencies."
                    prompt_text += weather_context

                    contents.append(prompt_text)

                    raw_answer = generate_content_with_retry(contents)

                    st.markdown(f"""
                    <div class="result-card">
                        <div style="font-weight:700; color:#064e3b; margin-bottom:8px;">🌿 Diagnostics & Recommendations:</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.write(raw_answer)

                except Exception as e:
                    st.error(f"Error connecting to AI: {e}")
    else:
        st.info("👈 Enter your crop question or upload a leaf photo on the left to view the AI response here.")
