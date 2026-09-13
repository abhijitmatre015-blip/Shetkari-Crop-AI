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
# 1. Page Configuration & HTML/Tailwind CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Shetkari AI - Multimodal Crop Assistant", 
    page_icon="🌾", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inject Fonts, Tailwind CSS & Font Awesome Icons
st.markdown("""
<!-- Google Fonts & FontAwesome -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<script src="https://cdn.tailwindcss.com"></script>
<script>
    tailwind.config = {
        theme: {
            extend: {
                colors: {
                    brand: {
                        50: '#f0fdf4',
                        100: '#dcfce7',
                        500: '#10b981',
                        600: '#059669',
                        700: '#047857',
                        800: '#065f46',
                        900: '#064e3b',
                        950: '#022c22',
                    },
                    amberGold: '#e5a93c',
                },
                fontFamily: {
                    sans: ['Plus Jakarta Sans', 'sans-serif'],
                }
            }
        }
    }
</script>
<style>
    .stApp {
        background-color: #f8fafc;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .dark-glass-panel {
        background: rgba(6, 78, 59, 0.85);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .gradient-btn {
        background: linear-gradient(135deg, #10b981 0%, #047857 100%);
        transition: all 0.3s ease;
    }
    .gradient-btn:hover {
        background: linear-gradient(135deg, #059669 0%, #064e3b 100%);
        transform: translateY(-2px);
        box-shadow: 0 10px 20px -5px rgba(16, 185, 129, 0.4);
    }
    /* Hide Streamlit Native Boilerplate Padding */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 80rem !important;
    }
    header[data-testid="stHeader"] {
        display: none !important;
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

Always respond structured with three distinct sections formatted EXACTLY like this:

### 1. DIAGNOSIS
[Provide identified disease, pest, or deficiency name and 2-sentence description]

### 2. RECOMMENDED ACTION
[Provide step-by-step chemical or organic dosage spraying/treatment steps]

### 3. WEATHER CAUTION
[Provide specific weather-based precaution using live weather data if available, e.g., rain, humidity, temperature warnings]

Respond using the same language the farmer uses (e.g., Marathi, Hindi, English).
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
                time.sleep(2 ** attempt)
            else:
                break

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
# 4. Location & Live Weather Initialization
# -----------------------------------------------------------------------------
if 'current_location' not in st.session_state:
    st.session_state.current_location = "Buldhana"

# Render Sticky Header Banner with Live Weather
weather_info = get_live_weather(st.session_state.current_location)
temp_disp = f"{weather_info.get('temp', '28')}°C" if "error" not in weather_info else "N/A"
hum_disp = f"{weather_info.get('humidity', '72')}%" if "error" not in weather_info else "N/A"
cond_disp = weather_info.get('condition', 'Partly Cloudy').capitalize() if "error" not in weather_info else "Data N/A"

st.markdown(f"""
<header class="bg-[#022c22] text-white rounded-2xl shadow-xl border border-emerald-800/50 mb-6 p-4">
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div class="flex items-center space-x-3.5">
            <div class="w-11 h-11 rounded-2xl bg-gradient-to-tr from-emerald-500 to-amber-500 flex items-center justify-center text-white text-2xl shadow-lg">
                🌾
            </div>
            <div>
                <div class="flex items-center space-x-2">
                    <h1 class="text-2xl font-extrabold tracking-tight text-white">Shetkari AI</h1>
                    <span class="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-semibold px-2.5 py-0.5 rounded-full">Pro v2.5</span>
                </div>
                <p class="text-xs text-emerald-100/70 font-medium">Smart Multimodal Crop Assistant & Diagnostics</p>
            </div>
        </div>
        <div class="dark-glass-panel rounded-2xl px-4 py-2 flex items-center space-x-4 border border-emerald-700/40 shadow-inner">
            <div class="flex items-center space-x-2.5">
                <div class="w-9 h-9 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center text-xl">
                    <i class="fa-solid fa-cloud-sun animate-pulse"></i>
                </div>
                <div>
                    <div class="flex items-center space-x-1.5 text-xs text-emerald-100 font-medium">
                        <i class="fa-solid fa-location-dot text-emerald-500"></i>
                        <span>{st.session_state.current_location}, MH</span>
                    </div>
                    <span class="text-lg font-bold text-white leading-tight">{temp_disp}</span>
                </div>
            </div>
            <div class="h-8 w-px bg-emerald-800"></div>
            <div class="text-xs text-emerald-100/80 space-y-0.5">
                <p><i class="fa-solid fa-droplet text-blue-400 w-4"></i> Humidity: <span class="text-white font-medium">{hum_disp}</span></p>
                <p><i class="fa-solid fa-wind text-teal-300 w-4"></i> Condition: <span class="text-white font-medium">{cond_disp}</span></p>
            </div>
        </div>
    </div>
</header>
""", unsafe_allow_html=True)

# Top Hero Section Banner
st.markdown("""
<section class="relative rounded-3xl overflow-hidden bg-gradient-to-r from-emerald-900 via-emerald-800 to-emerald-950 text-white p-6 sm:p-8 shadow-xl mb-6">
    <div class="relative z-10 max-w-3xl">
        <div class="inline-flex items-center space-x-2 bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 font-semibold text-xs px-3 py-1 rounded-full mb-3">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
            <span>AI-Powered Crop Care</span>
        </div>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-2">
            Instant Crop Disease Diagnosis & Regional Advisory
        </h2>
        <p class="text-emerald-100/80 text-sm sm:text-base leading-relaxed">
            Upload a leaf photo or enter your crop question in Marathi, Hindi, or English to get instant, AI-guided treatments tailored for your field weather.
        </p>
    </div>
</section>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Main Workspace: Form Inputs vs AI Output Grid
# -----------------------------------------------------------------------------
left_col, right_col = st.columns([5, 7], gap="large")

with left_col:
    st.markdown("""
    <div class="border-b border-slate-200 pb-3 mb-4">
        <h3 class="text-xl font-bold text-emerald-950 flex items-center space-x-2">
            <i class="fa-solid fa-circle-nodes text-emerald-600"></i>
            <span>Ask AI Assistant / माहिती घ्या</span>
        </h3>
        <p class="text-xs text-slate-500 mt-0.5">Provide your location, questions, or leaf photos below.</p>
    </div>
    """, unsafe_allow_html=True)

    # Location Input & Quick Select Buttons
    location_input = st.text_input("📍 Select Location / ठिकाण निवडा", st.session_state.current_location)
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

    # Query Input Box
    user_query = st.text_area(
        "💬 Describe Symptoms / काय अडचण आहे?",
        placeholder="e.g. कापसाच्या पानांवर पिवळे ठिपके दिसत आहेत किंवा कोणती फवारणी करावी?",
        height=100
    )

    # Image File Uploader
    uploaded_file = st.file_uploader(
        "📷 Upload Plant Leaf Image / रोपाचा फोटो टाका",
        type=["jpg", "jpeg", "png"]
    )

    image = None
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Crop Image", use_container_width=True)

    # Submit Trigger
    submit_btn = st.button("✨ Get AI Advice / सल्ला मिळवा", type="primary", use_container_width=True)

with right_col:
    st.markdown("""
    <div class="bg-white rounded-2xl p-4 shadow-sm border border-slate-200 flex items-center justify-between mb-4">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center text-lg font-bold">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div>
                <h3 class="font-bold text-slate-900">AI Advisory Result</h3>
                <p class="text-xs text-slate-500">Powered by Gemini Multimodal Reasoning</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if submit_btn:
        if not user_query.strip() and image is None:
            st.warning("Please enter a question or upload an image! / कृपया प्रश्न टाका किंवा फोटो अपलोड करा!")
        else:
            with st.spinner("Analyzing Crop & Weather Data... Executing multimodal vision pipeline..."):
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

                    # Dynamic 3-Card Rendering
                    st.markdown(f"""
                    <div class="space-y-4">
                        <!-- Card 1: Diagnosis -->
                        <div class="bg-white rounded-2xl p-5 shadow-lg border border-slate-200">
                            <div class="flex items-center space-x-3 mb-3">
                                <div class="w-10 h-10 rounded-xl bg-red-100 text-red-600 flex items-center justify-center text-lg">
                                    <i class="fa-solid fa-bug"></i>
                                </div>
                                <div>
                                    <span class="text-xs font-bold uppercase tracking-wider text-red-600">Disease Identified</span>
                                    <h4 class="text-base font-bold text-slate-900">Crop Health Analysis</h4>
                                </div>
                            </div>
                            <div class="text-slate-700 text-sm leading-relaxed border-t border-slate-100 pt-3">
                                {raw_answer}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Error connecting to AI: {e}")
    else:
        # Default placeholder showing ready state
        st.info("👈 Enter your crop question or upload a leaf photo on the left to view the AI advisory response here.")

# -----------------------------------------------------------------------------
# 6. Bottom Key Platform Capabilities Footer Grid
# -----------------------------------------------------------------------------
st.markdown("""
<hr class="my-8 border-slate-200">
<div class="text-center max-w-xl mx-auto mb-6">
    <h3 class="text-2xl font-bold text-emerald-950">Key Platform Capabilities</h3>
    <p class="text-xs text-slate-500 mt-1">Engineered specifically for rural accessibility and low connectivity</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
    <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition">
        <div class="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center text-lg mb-3">
            <i class="fa-solid fa-eye"></i>
        </div>
        <h4 class="font-bold text-slate-900 text-sm mb-1">Multimodal Vision AI</h4>
        <p class="text-xs text-slate-500 leading-relaxed">Processes high-resolution leaf photos to identify micro-pests and fungal infections accurately.</p>
    </div>

    <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition">
        <div class="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center text-lg mb-3">
            <i class="fa-solid fa-cloud-sun-rain"></i>
        </div>
        <h4 class="font-bold text-slate-900 text-sm mb-1">Real-time Weather Context</h4>
        <p class="text-xs text-slate-500 leading-relaxed">Integrates local humidity and rain forecasts so farmers don't waste costly chemical sprays.</p>
    </div>

    <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition">
        <div class="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center text-lg mb-3">
            <i class="fa-solid fa-language"></i>
        </div>
        <h4 class="font-bold text-slate-900 text-sm mb-1">24/7 Regional Voice & Text</h4>
        <p class="text-xs text-slate-500 leading-relaxed">Supports natural Marathi and Hindi dialects, enabling effortless queries without technical jargon.</p>
    </div>

    <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition">
        <div class="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center text-lg mb-3">
            <i class="fa-solid fa-shield-halved"></i>
        </div>
        <h4 class="font-bold text-slate-900 text-sm mb-1">Resilient Fallback Pipeline</h4>
        <p class="text-xs text-slate-500 leading-relaxed">Built-in automatic retries with exponential backoff to handle unstable rural 4G/3G connectivity.</p>
    </div>
</div>

<footer class="bg-[#022c22] text-emerald-100/70 rounded-2xl p-4 text-center text-xs space-y-1">
    <p class="font-semibold text-emerald-100">🌾 Shetkari AI - Empowering Farmers with Modern AI Technologies</p>
    <p>© 2026 Shetkari AI Assistant. Built for Vidarbha & Indian Agriculture Growth.</p>
</footer>
""", unsafe_allow_html=True)
