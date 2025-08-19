import streamlit as st
import os
from dotenv import load_dotenv

# Pastikan package google-generativeai sudah diinstall
try:
    import google.generativeai as genai
except ImportError:
    st.error("Modul 'google-generativeai' belum terinstall. Jalankan perintah berikut di terminal:\n\npip install google-generativeai\n")
    st.stop()

try:
    import PyPDF2
except ImportError:
    st.error("Modul 'PyPDF2' belum terinstall. Jalankan perintah berikut di terminal:\n\npip install PyPDF2\n")
    st.stop()

try:
    import pandas as pd
except ImportError:
    st.error("Modul 'pandas' belum terinstall. Jalankan perintah berikut di terminal:\n\npip install pandas\n")
    st.stop()

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def extract_text_from_excel(excel_file):
    try:
        df = pd.read_excel(excel_file)
        return df.to_string(index=False)
    except Exception as e:
        return f"Error membaca file Excel: {e}"

# Load environment variables from .env file
load_dotenv()

# Initialize the Gemini API client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY belum diatur di file .env. Silakan tambahkan baris berikut ke file .env:\nGEMINI_API_KEY=your_api_key")
    st.stop()
genai.configure(api_key=api_key)

st.title("Simple Chatbot App")

ROLES = {
    "Admin": {
        "system_prompt": "You are the admin. You can upload and manage the knowledge base."
    },
    "AM": {
        "system_prompt": "You are an Account Manager (AM). Jawab pertanyaan terkait tugas dan tanggung jawab AM berdasarkan knowledge base."
    },
    "HOTD": {
        "system_prompt": "You are Head of the Department (HOTD). Jawab pertanyaan terkait kebijakan dan keputusan HOTD berdasarkan knowledge base."
    },
    "Unit BS": {
        "system_prompt": "You are a staff of Unit BS. Jawab pertanyaan terkait operasional dan tugas Unit BS berdasarkan knowledge base."
    }
}

with st.sidebar:
    st.header("Monitoring End Contract Witel JKO")
    st.subheader("🎭 Select Role")
    selected_role = st.selectbox(
        "Choose your role:",
        options=list(ROLES.keys())
    )
    st.subheader("📚 Knowledge Base")

    # Hanya Admin yang bisa upload/reset file
    if selected_role == "Admin":
        admin_pass = st.text_input("Admin password (hanya admin bisa upload file)", type="password")
        if admin_pass == "admin123":  # Ganti dengan password yang hanya Anda tahu
            uploaded_file = st.file_uploader(
                "Upload your knowledge base file (PDF, TXT, XLSX)", 
                type=["pdf", "txt", "xlsx"]
            )
            if uploaded_file:
                if "knowledge_base" not in st.session_state:
                    st.session_state.knowledge_base = []
                if uploaded_file.type == "application/pdf":
                    text = extract_text_from_pdf(uploaded_file)
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    text = extract_text_from_excel(uploaded_file)
                else:
                    text = uploaded_file.read().decode("utf-8")
                st.session_state.knowledge_base = [text]
                st.session_state.knowledge_base_filename = uploaded_file.name
                st.success(f"File '{uploaded_file.name}' uploaded and processed.")

            if st.button("Reset Knowledge Base"):
                st.session_state.knowledge_base = []
                st.session_state.knowledge_base_filename = ""
                st.success("Knowledge base berhasil direset.")
        else:
            st.info("Masukkan password admin untuk upload knowledge base.")
    else:
        # Role selain Admin hanya bisa melihat nama file knowledge base
        kb_filename = st.session_state.get("knowledge_base_filename", "")
        if kb_filename:
            st.info(f"Knowledge base file: **{kb_filename}**")
        else:
            st.warning("Knowledge base belum diupload oleh admin.")

# Pastikan knowledge base sudah ada sebelum chat
if "knowledge_base" not in st.session_state or not st.session_state.knowledge_base:
    st.warning("Knowledge base belum diupload oleh admin.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

model = genai.GenerativeModel("gemini-1.5-flash")

prompt = st.chat_input("Tanyakan sesuatu sesuai knowledge base!")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    system_prompt = ROLES[selected_role]["system_prompt"]
    knowledge_base_text = ""
    if "knowledge_base" in st.session_state and st.session_state.knowledge_base:
        knowledge_base_text = "\n\nKnowledge Base:\n" + "\n".join(st.session_state.knowledge_base)
    full_prompt = f"{system_prompt}\n{knowledge_base_text}\nUser: {prompt}"

    try:
        response = model.generate_content(full_prompt)
        assistant_reply = response.text
    except Exception as e:
        assistant_reply = f"Terjadi error saat memproses permintaan: {e}"

    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
    with st.chat_message("assistant"):
        st.markdown(assistant_reply)