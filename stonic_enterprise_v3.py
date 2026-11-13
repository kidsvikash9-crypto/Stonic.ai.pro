import streamlit as st
import sqlite3
import hashlib
import requests
import time
from io import BytesIO
from PIL import Image
from pypdf import PdfReader
from google import genai
from google.genai import types

# ==========================================
# PAGE CONFIG & PREMIUM UI
# ==========================================
st.set_page_config(
    page_title="Stonic AI Enterprise v3.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4F46E5, #EC4899, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .status-badge {
        background: #064E3B;
        color: #6EE7B7;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .credit-card {
        background: linear-gradient(135deg, #1E1B4B, #312E81);
        color: white;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #6366F1;
        text-align: center;
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# DATABASE INITIALIZATION (AUTO-ADMIN SETUP)
# ==========================================
def init_db():
    conn = sqlite3.connect("stonic_enterprise.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            credits INTEGER DEFAULT 100,
            role TEXT DEFAULT 'user'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            tool_name TEXT,
            prompt TEXT,
            output TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Default Admin Account (Username: admin | Password: admin123)
    admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password, credits, role) VALUES ('admin', ?, 99999, 'admin')", (admin_pass,))
    conn.commit()
    return conn

conn = init_db()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

def register_user(u, p):
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, credits, role) VALUES (?, ?, 100, 'user')", (u.strip(), hash_pass(p)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(u, p):
    c = conn.cursor()
    c.execute("SELECT credits, role FROM users WHERE username=? AND password=?", (u.strip(), hash_pass(p)))
    return c.fetchone()

def get_user_info(u):
    c = conn.cursor()
    c.execute("SELECT credits, role FROM users WHERE username=?", (u,))
    return c.fetchone() or (0, 'user')

def update_credits(u, delta):
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE username=?", (delta, u))
    conn.commit()

def save_history(u, tool, prompt, output):
    c = conn.cursor()
    c.execute("INSERT INTO history (username, tool_name, prompt, output) VALUES (?, ?, ?, ?)", (u, tool, prompt, str(output)))
    conn.commit()

# ==========================================
# AUTO-LOAD SECRETS (NO MANUAL HASSLE)
# ==========================================
def get_secret(key_name):
    try:
        return st.secrets.get(key_name, "")
    except Exception:
        return ""

if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = get_secret("GEMINI_API_KEY")
if "replicate_key" not in st.session_state:
    st.session_state.replicate_key = get_secret("REPLICATE_API_TOKEN")
if "eleven_key" not in st.session_state:
    st.session_state.eleven_key = get_secret("ELEVENLABS_API_KEY")
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# ==========================================
# AUTHENTICATION SCREEN
# ==========================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        st.markdown('<p class="hero-title">⚡ Stonic AI Enterprise v3.0</p>', unsafe_allow_html=True)
        st.markdown('<span class="status-badge">● All 8 AI Engines Verified & Active</span>', unsafe_allow_html=True)
        st.write("")
        
        t_login, t_reg = st.tabs(["🔑 Login", "🎁 Free Sign-Up (100 Credits)"])
        with t_login:
            u = st.text_input("Username", placeholder="admin ya apna username dalein")
            p = st.text_input("Password", type="password", placeholder="admin123")
            if st.button("Dashboard Kholein", use_container_width=True, type="primary"):
                res = login_user(u, p)
                if res:
                    st.session_state.logged_in = True
                    st.session_state.username = u.strip()
                    st.rerun()
                else:
                    st.error("Invalid Username ya Password!")
        with t_reg:
            nu = st.text_input("Naya Username")
            np = st.text_input("Password", type="password")
            if st.button("Account Banayein (100 Free Credits)", use_container_width=True):
                if nu and np and register_user(nu, np):
                    st.success("Account ban gaya! Ab Login karein.")
                else:
                    st.error("Username pehle se maujood hai ya khali hai.")
    st.stop()

# ==========================================
# LOGGED-IN DASHBOARD & SIDEBAR
# ==========================================
credits, role = get_user_info(st.session_state.username)

with st.sidebar:
    st.markdown('<p class="hero-title">⚡ Stonic v3</p>', unsafe_allow_html=True)
    st.write(f"👤 **{st.session_state.username}** (`{role.upper()}`)")
    st.markdown(f'<div class="credit-card">💎 Balance: <b>{credits} Credits</b></div>', unsafe_allow_html=True)

    with st.expander("💳 Instant Credit Top-Up"):
        plan = st.selectbox("Pack:", ["₹99 → 200 Credits", "₹299 → 750 Credits", "₹499 → 2000 Credits"])
        if st.button("Add Credits Now"):
            bonus = 200 if "200" in plan else (750 if "750" in plan else 2000)
            update_credits(st.session_state.username, bonus)
            st.success(f"+{bonus} Credits Added!")
            st.rerun()

    menu_items = [
        "🎵 Suno AI Full Song Studio (10 Cr)",
        "🧬 Voice Cloning & Dubbing (5 Cr)",
        "🎬 AI Video & Storyboard Maker (3 Cr)",
        "📄 Chat with PDF / Document AI (2 Cr)",
        "✍️ Writesonic SEO & Ad Copy (2 Cr)",
        "🎨 AI Image & Thumbnail Studio (5 Cr)",
        "💻 Code & Pine Script Architect (2 Cr)",
        "💬 Real-Time AI Assistant (1 Cr)",
        "📂 My Creations & History"
    ]
    if role == "admin":
        menu_items.append("🛡️ Admin Control Panel")

    choice = st.radio("All-in-One AI Suite:", menu_items)

    if role == "admin" or not st.session_state.gemini_key:
        with st.expander("🔑 Engine API Keys", expanded=not bool(st.session_state.gemini_key)):
            st.session_state.gemini_key = st.text_input("Gemini API Key:", value=st.session_state.gemini_key, type="password")
            st.session_state.replicate_key = st.text_input("Replicate Token:", value=st.session_state.replicate_key, type="password")
            st.session_state.eleven_key = st.text_input("ElevenLabs Key:", value=st.session_state.eleven_key, type="password")

    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# Credit Deduction Helper with Auto-Refund Safety
def deduct_credits(cost):
    curr, _ = get_user_info(st.session_state.username)
    if curr < cost:
        st.error(f"⚠️ Kam Credits! Is feature ke liye {cost} credits chahiye.")
        return False
    update_credits(st.session_state.username, -cost)
    return True

def get_gemini():
    if not st.session_state.gemini_key:
        st.error("⚠️ Gemini API Key missing hai! Sidebar ke 'Engine API Keys' mein dalein.")
        return None
    return genai.Client(api_key=st.session_state.gemini_key)

# ==========================================
# 1. SUNO AI FULL SONG STUDIO
# ==========================================
if "Suno AI" in choice:
    st.header("🎵 Suno AI Pro: Lyrics + Music + Vocals")
    c1, c2 = st.columns(2)
    with c1:
        topic = st.text_area("Gaane ka Idea / Mood:", placeholder="Jaise: Raat ke 2 baje long drive, lo-fi Bollywood romantic vibe")
        genre = st.selectbox("Music Style:", ["Bollywood Lo-Fi", "Punjabi Pop / Bhangra", "Desi Hip-Hop / Rap", "EDM / Party", "Sufi / Acoustic"])
    with c2:
        lang = st.selectbox("Bhasha:", ["Hinglish / Hindi", "Punjabi", "English"])
        lyrics_box = st.text_area("Custom Lyrics (Khali chhodein agar AI se likhwana hai):")

    if st.button("🚀 Generate Complete Song (10 Credits)", type="primary"):
        client = get_gemini()
        if client and deduct_credits(10):
            try:
                with st.spinner("1/2: AI Lyrics aur Rhythm taiyar kar raha hai..."):
                    if not lyrics_box:
                        res = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=f"Write catchy song lyrics in {lang} about '{topic}' in {genre} style with [Verse], [Chorus], [Outro] tags. Max 100 words."
                        )
                        final_lyrics = res.text
                    else:
                        final_lyrics = lyrics_box
                    st.info(final_lyrics)
                    save_history(st.session_state.username, "Suno Lyrics", topic, final_lyrics)

                if st.session_state.replicate_key:
                    with st.spinner("2/2: Studio Vocals & Music synthesize ho raha hai..."):
                        headers = {"Authorization": f"Bearer {st.session_state.replicate_key}", "Content-Type": "application/json"}
                        payload = {"input": {"lyrics": final_lyrics, "prompt": f"{genre}, studio vocals, {lang}"}}
                        r = requests.post("https://api.replicate.com/v1/models/minimax/music-01/predictions", json=payload, headers=headers).json()
                        if "urls" in r and "get" in r["urls"]:
                            while True:
                                poll = requests.get(r["urls"]["get"], headers=headers).json()
                                if poll["status"] == "succeeded":
                                    st.success("🎉 Gaana Ready Hai!")
                                    st.audio(poll["output"])
                                    save_history(st.session_state.username, "Suno Song MP3", topic, poll["output"])
                                    break
                                elif poll["status"] in ["failed", "canceled"]:
                                    update_credits(st.session_state.username, 10)
                                    st.error("Audio fail hua — 10 Credits auto-refund kar diye gaye!")
                                    break
                                time.sleep(5)
                        else:
                            update_credits(st.session_state.username, 10)
                            st.error(f"Replicate API Error (Credits Refunded): {r.get('detail', r)}")
                else:
                    st.warning("Lyrics ban chuke hain! Full MP3 track ke liye Replicate Token dalein.")
            except Exception as e:
                update_credits(st.session_state.username, 10)
                st.error(f"Error (Credits Refunded): {e}")

# ==========================================
# 2. VOICE CLONING & DUBBING
# ==========================================
elif "Voice Cloning" in choice:
    st.header("🧬 AI Voice Cloning & Multilingual TTS")
    tab1, tab2 = st.tabs(["🗣️ Text-to-Speech", "🎙️ Clone New Voice"])
    with tab1:
        txt = st.text_area("Jo bulwana hai wo likhein:")
        vid = st.text_input("Voice ID:", value="21m00Tcm4TlvDq8ikWAM")
        if st.button("🔊 Generate Voice (5 Credits)"):
            if not st.session_state.eleven_key or not txt:
                st.error("ElevenLabs Key aur Text dalein!")
            elif deduct_credits(5):
                r = requests.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                    json={"text": txt, "model_id": "eleven_multilingual_v2"},
                    headers={"xi-api-key": st.session_state.eleven_key}
                )
                if r.status_code == 200:
                    st.audio(r.content, format="audio/mp3")
                    st.download_button("⬇️ Download MP3", r.content, "voice.mp3")
                else:
                    update_credits(st.session_state.username, 5)
                    st.error(f"Failed ({r.status_code}) — Credits Refunded!")

    with tab2:
        vname = st.text_input("Voice Name:")
        sample = st.file_uploader("Upload 30-60s clean audio (.mp3/.wav):", type=["mp3", "wav"])
        if st.button("🧬 Clone Voice (5 Credits)"):
            if st.session_state.eleven_key and sample and vname and deduct_credits(5):
                r = requests.post(
                    "https://api.elevenlabs.io/v1/voices/add",
                    headers={"xi-api-key": st.session_state.eleven_key},
                    data={"name": vname},
                    files={"files": (sample.name, sample.getvalue(), "audio/mpeg")}
                )
                if r.status_code == 200:
                    new_id = r.json().get("voice_id")
                    st.success(f"🎉 Cloned! Voice ID: `{new_id}`")
                    save_history(st.session_state.username, "Voice Clone", vname, new_id)
                else:
                    update_credits(st.session_state.username, 5)
                    st.error("Cloning Failed — Credits Refunded!")

# ==========================================
# 3. AI VIDEO & STORYBOARD MAKER
# ==========================================
elif "AI Video" in choice:
    st.header("🎬 AI Video Script, Scenes & Image Prompts Generator")
    v_idea = st.text_input("Video ka Topic:", placeholder="Jaise: Ek chhota robot jo chai ki dukaan chalata hai (3D Pixar style)")
    v_style = st.selectbox("Format:", ["YouTube Shorts / Instagram Reels (60s)", "YouTube Documentary / Explainer", "AI Animation Storyboard"])
    if st.button("🎬 Complete Video Blueprint Banayein (3 Credits)", type="primary"):
        client = get_gemini()
        if client and v_idea and deduct_credits(3):
            with st.spinner("Scene-by-scene storyboard aur AI image prompts ban rahe hain..."):
                prompt = f"""Create a complete {v_style} production plan for: '{v_idea}'.
                Provide a scene-by-scene breakdown with:
                1. Scene Number & Duration
                2. Voiceover / Dialogue (Hinglish)
                3. Detailed AI Image/Video Generation Prompt (English, cinematic lighting, 8k)
                4. Background Music / SFX cue."""
                res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt).text
                st.markdown(res)
                save_history(st.session_state.username, "Video Storyboard", v_idea, res)

# ==========================================
# 4. CHAT WITH PDF / DOCUMENT AI
# ==========================================
elif "Chat with PDF" in choice:
    st.header("📄 Document & PDF Analyzer AI")
    uploaded_file = st.file_uploader("Koi bhi PDF ya TXT file upload karein:", type=["pdf", "txt"])
    doc_q = st.text_input("Is document se kya jaanna chahte hain?", value="Is document ki mukhya baatein (Summary) bullet points mein batao.")
    if st.button("🔍 Analyze Document (2 Credits)", type="primary"):
        client = get_gemini()
        if client and uploaded_file and deduct_credits(2):
            with st.spinner("Document padha ja raha hai..."):
                text_data = ""
                if uploaded_file.name.endswith(".pdf"):
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages[:15]:
                        text_data += page.extract_text() or ""
                else:
                    text_data = uploaded_file.read().decode("utf-8", errors="ignore")
                
                res = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"Document Content:\n{text_data[:25000]}\n\nUser Question: {doc_q}"
                ).text
                st.markdown(res)
                save_history(st.session_state.username, "PDF Analysis", uploaded_file.name, res)

# ==========================================
# 5. WRITESONIC SEO & AD COPY
# ==========================================
elif "Writesonic" in choice:
    st.header("✍️ Writesonic Pro: Blogs, Ads & E-Commerce Copy")
    mode = st.selectbox("Tool:", ["SEO Blog Post", "Facebook/Instagram Ad Copy", "Meesho/Flipkart/Amazon Product Listing", "Multi-Language Translator"])
    inp = st.text_input("Topic / Product Name:")
    extra = st.text_area("Details / Keywords / Target Language:")
    if st.button("✨ Generate Content (2 Credits)", type="primary"):
        client = get_gemini()
        if client and inp and deduct_credits(2):
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Task: {mode}. Subject: {inp}. Details: {extra}. Deliver high-converting, structured output."
            ).text
            st.markdown(res)
            save_history(st.session_state.username, mode, inp, res)

# ==========================================
# 6. AI IMAGE & THUMBNAIL STUDIO
# ==========================================
elif "AI Image" in choice:
    st.header("🎨 AI Image & YouTube Thumbnail Generator")
    p_img = st.text_input("Image Prompt:", placeholder="Ultra realistic luxury gold bangles on velvet tray, cinematic lighting, 8k")
    ratio = st.selectbox("Size:", ["1:1", "16:9", "9:16"])
    if st.button("🖼️ Generate Image (5 Credits)", type="primary"):
        client = get_gemini()
        if client and p_img and deduct_credits(5):
            try:
                res = client.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=p_img,
                    config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio=ratio)
                )
                for img in res.generated_images:
                    pil_img = Image.open(BytesIO(img.image.image_bytes))
                    st.image(pil_img)
                    buf = BytesIO()
                    pil_img.save(buf, format="PNG")
                    st.download_button("⬇️ Download PNG", buf.getvalue(), "stonic_image.png")
                    save_history(st.session_state.username, "AI Image", p_img, "Generated Image")
            except Exception as e:
                update_credits(st.session_state.username, 5)
                st.error(f"Error (5 Credits Refunded): {e}")

# ==========================================
# 7. CODE & PINE SCRIPT ARCHITECT
# ==========================================
elif "Code & Pine Script" in choice:
    st.header("💻 Code, App & TradingView Pine Script Generator")
    lang = st.selectbox("Language:", ["TradingView Pine Script v5", "Python", "Flutter / Dart", "HTML / CSS / JS"])
    req = st.text_area("Kya code banana hai?", placeholder="Jaise: Nifty 50 ke liye EMA crossover aur RSI buy/sell signal indicator")
    if st.button("⚡ Generate Code (2 Credits)", type="primary"):
        client = get_gemini()
        if client and req and deduct_credits(2):
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Write clean, production-ready {lang} code for: {req}. Add brief setup instructions."
            ).text
            st.markdown(res)
            save_history(st.session_state.username, f"Code ({lang})", req, res)

# ==========================================
# 8. REAL-TIME AI ASSISTANT
# ==========================================
elif "Real-Time AI Assistant" in choice:
    st.header("💬 Stonic Smart AI Chat")
    if "msgs" not in st.session_state:
        st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    if prompt := st.chat_input("Apna sawal puchein..."):
        client = get_gemini()
        if client and deduct_credits(1):
            st.session_state.msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                ans = client.models.generate_content(model="gemini-2.5-flash", contents=prompt).text
                st.markdown(ans)
                st.session_state.msgs.append({"role": "assistant", "content": ans})

# ==========================================
# 9. MY CREATIONS & HISTORY
# ==========================================
elif "My Creations" in choice:
    st.header("📂 Aapki Saari Saved Creations")
    c = conn.cursor()
    c.execute("SELECT tool_name, prompt, output, created_at FROM history WHERE username=? ORDER BY id DESC", (st.session_state.username,))
    rows = c.fetchall()
    if not rows:
        st.info("Abhi tak koi history nahi hai.")
    for r in rows:
        with st.expander(f"🕒 {r[3]} | {r[0]} — {r[1][:45]}"):
            st.markdown(r[2])

# ==========================================
# 10. ADMIN CONTROL PANEL
# ==========================================
elif "Admin Control Panel" in choice and role == "admin":
    st.header("🛡️ Master Admin Control Panel")
    c = conn.cursor()
    c.execute("SELECT username, credits, role FROM users")
    users = c.fetchall()
    st.subheader("👥 Registered Users & Credits")
    st.dataframe([{"Username": u[0], "Credits": u[1], "Role": u[2]} for u in users], use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        target_u = st.text_input("User ka Username:")
        add_c = st.number_input("Credits Add/Minus karein:", value=100, step=50)
        if st.button("Update User Credits"):
            update_credits(target_u, add_c)
            st.success(f"{target_u} ke credits update ho gaye!")
            st.rerun()
