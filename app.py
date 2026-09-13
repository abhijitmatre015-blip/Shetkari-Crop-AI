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
# 1. Page Configuration & Custom HTML/CSS/JS Injection
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Crop AI Assistant", page_icon="🌾", layout="centered")

# Custom CSS for Modern AgTech Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Main Background Accent */
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #eef2f6 100%);
    }

    /* Custom Header Styling */
    .app-header {
        background: linear-gradient(135deg, #064e3b 0%, #047857 100%);
        color: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(6, 78, 59, 0.25);
        margin-bottom: 24px;
        text-align: center;
    }
    .app-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        color: #ffffff;
    }
    .app-header p {
        font-size: 1rem;
        color: #a7f3d0;
        margin-top: 8px;
        margin-bottom: 0;
    }

    /* Metric Cards Custom Styling */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        text-align: center;
    }
    
    /* Primary Action Button Custom Styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
        padding: 12px 24px;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Custom HTML Banner Component
st.markdown("""
<div class="app-header">
    <h1>🌾 Shetkari AI / Farmer Crop Assistant</h1>
    <p>Ask any questions or upload a photo of your crop/pest in your local language!</p>
</div>
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
Always respond in simple terms, using the same language the farmer uses (e.g., Marathi, Hindi, English).
If live weather data is provided, use it to give specific advice (e.g., advising against pesticide spraying if rain is expected).
"""

PRIMARY_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-3.6-flash"

# -----------------------------------------------------------------------------
# 3. Resilient API Call Helper 
# -----------------------------------------------------------------------------
def generate_content_with_retry(contents: list) -> str:
    """Generates content with automatic retries and model fallback on 503 errors."""
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.3
    )

    max_retries = 3
    # Try primary model with exponential backoff
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=contents,
                config=config
            )
            return response.text
        except Exception as e:
            err_msg = str(e)
            if ("503" in err_msg or "UNAVAILABLE" in err_msg) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Wait 1s, then 2s before retrying
            else:
                break

    # Fallback model attempt if primary model remains overloaded
    try:
        response = client.models.generate_content(
            model=FALLBACK_MODEL,
            contents=contents,
            config=config
        )
        return response.text
    except Exception as final_err:
        raise final_err

# -----------------------------------------------------------------------------
# 4. Weather & User Input Interface
# -----------------------------------------------------------------------------
# Location Input & Live Weather Display
location = st.text_input("📍 Enter your location / तुमची जागा किंवा गाव निवडा:", "Buldhana")
weather_info = get_live_weather(location)

if "error" not in weather_info:
    col1, col2, col3 = st.columns(3)
    col1.metric("Temperature", f"{weather_info['temp']} °C")
    col2.metric("Humidity", f"{weather_info['humidity']} %")
    col3.metric("Condition", weather_info['condition'].capitalize())
else:
    st.info(f"ℹ️ {weather_info['error']}")

# Query & Image Input Box
user_query = st.text_input("💬 Enter your crop question / तुमचा प्रश्न इथे लिहा:")

uploaded_file = st.file_uploader(
    "📷 Upload a crop/leaf image (optional) / पिकाचे किंवा पानाचे छायाचित्र अपलोड करा:",
    type=["jpg", "jpeg", "png"]
)

image = None
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image Preview", use_container_width=True)

# -----------------------------------------------------------------------------
# 5. Process Request
# -----------------------------------------------------------------------------
if st.button("Get Answer / उत्तर मिळवा", type="primary"):
    if not user_query.strip() and image is None:
        st.warning("Please enter a question or upload an image! / कृपया प्रश्न टाका किंवा फोटो अपलोड करा!")
    else:
        with st.spinner("Analyzing your query and checking live field conditions..."):
            try:
                contents = []
                if image:
                    contents.append(image)

                # Inject live weather data into the prompt
                weather_context = ""
                if "error" not in weather_info:
                    weather_context = f"\n[Live Weather Data: {weather_info['raw_text']}]"

                prompt_text = user_query.strip() if user_query.strip() else "Please analyze this crop/leaf image for diseases, pests, or deficiencies."
                prompt_text += weather_context

                contents.append(prompt_text)

                # Send request to Gemini API
                answer = generate_content_with_retry(contents)
                st.success("Advice / सल्ला:")
                st.write(answer)

                # Custom JavaScript Execution upon Successful Analysis
                components.html("""
                <script>
                    console.log("Shetkari AI analysis successfully completed.");
                </script>
                """, height=0)

            except Exception as e:
                st.error(f"Error connecting to AI: {e}")
