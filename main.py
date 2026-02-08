import streamlit as st
import requests
import re
import pandas as pd
import time
import html
import random
import streamlit.components.v1 as components

# --- CẤU HÌNH ---
st.set_page_config(page_title="LinkedIn Hunter Pro", page_icon="🚀", layout="wide")
components.html("""<meta name="google" content="notranslate">""", height=0)

# --- CSS: DARK MODE ---
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif; }
    
    /* Input & Button */
    .stTextArea textarea { background-color: #0d1117 !important; color: #58a6ff !important; border: 1px solid #30363d; }
    .stTextInput input { background-color: #161b22 !important; color: #00FF94 !important; border: 1px solid #30363d; font-weight: bold; }
    
    .stButton>button { 
        width: 100%; border-radius: 6px; font-weight: 600; border: none; height: 38px;
        background-color: #238636; color: white; transition: 0.2s;
    }
    .stButton>button:hover { opacity: 0.9; }

    /* KẾT QUẢ STYLE MỚI (Email trên - Link dưới) */
    .res-card {
        background-color: #161b22; 
        border: 1px solid #30363d; 
        border-radius: 8px; 
        padding: 10px; 
        margin-bottom: 10px;
    }
    .res-email { color: #8b949e; font-size: 13px; font-weight: bold; margin-bottom: 5px; display: flex; align-items: center; }
    .res-idx { background-color: #238636; color: white; padding: 2px 6px; border-radius: 4px; margin-right: 8px; font-size: 11px; }

    /* Header cột */
    .col-header { font-size: 16px; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #30363d; padding-bottom: 5px; }
    .text-green { color: #238636; border-color: #238636; }
    .text-blue { color: #58a6ff; border-color: #1f6feb; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE ---
if 'queue' not in st.session_state: st.session_state.queue = []
if 'results' not in st.session_state: st.session_state.results = []
if 'check_results' not in st.session_state: st.session_state.check_results = []
if 'input_raw' not in st.session_state: st.session_state.input_raw = "" # Biến để clear input

# --- LOGIC ---
def parse_excel(text):
    valid = []
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        parts = line.split('\t') if "\t" in line else line.split('|')
        while len(parts) < 4: parts.append("")
        valid.append({
            "Raw": line, 
            "Email": parts[0], 
            "Pass": parts[1], 
            "Token": parts[2], 
            "Client_ID": parts[3]
        })
    return valid

def add_data():
    """Hàm thêm dữ liệu và tự xóa ô nhập"""
    if st.session_state.input_raw:
        st.session_state.queue.extend(parse_excel(st.session_state.input_raw))
        st.session_state.input_raw = "" # Clear ô nhập ngay lập tức

def get_link_with_retry(item):
    try:
        data = {"client_id": item['Client_ID'], "grant_type": "refresh_token", "refresh_token": item['Token'], "scope": "https://graph.microsoft.com/Mail.Read"}
        r = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data, timeout=5).json()
        acc = r.get("access_token")
        if not acc: return None
        res = requests.get("https://graph.microsoft.com/v1.0/me/messages?$search=\"Claim your LinkedIn Premium Career\"&$top=1", headers={"Authorization": f"Bearer {acc}"}, timeout=5).json()
        if 'value' in res and res['value']:
            match = re.search(r'https://www\.linkedin\.com/premium/redeem\?[^\s"\'<>]+', res['value'][0]['body']['content'])
            if match: return html.unescape(match.group(0))
    except: pass
    return None

def check_link_status(url, li_at_cookie):
    if not li_at_cookie: return "⚠️ THIẾU COOKIE"
    headers = {
        'authority': 'www.linkedin.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'vi-VN,vi;q=0.9,en-US;q=0.6,en;q=0.5',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    cookies = {'li_at': li_at_cookie}
    try:
        session = requests.Session()
        r = session.get(url, headers=headers, cookies=cookies, timeout=10, allow_redirects=True)
        content = r.text.lower()
        
        if "login" in r.url: return "⚠️ COOKIE DIE"
        if "đổi phiếu" in content or "redeem" in content or "activate" in content: return "✅ LIVE"
        if "already been redeemed" in content or "đã được đổi" in content: return "❌ DIE (Đã dùng)"
        if "offer is no longer active" in content: return "❌ DIE (Hết hạn)"
        return "❓ UNKNOWN"
    except: return "⚠️ LỖI MẠNG"

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 LINKEDIN HUNTER PRO")

tab1, tab2 = st.tabs(["📦 KHO & QUÉT", "⚡ CHECK LINK (LIVE/DIE)"])

# ================= TAB 1: SĂN MAIL =================
with tab1:
    # INPUT TỰ XÓA
    with st.expander("➕ DÁN DỮ LIỆU VÀO ĐÂY (Raw Excel/Text)", expanded=False):
        # Dùng key='input_raw' để quản lý nội dung
        st.text_area("", height=100, label_visibility="collapsed", placeholder="Email | Pass | Token | ID", key="input_raw")
        # Nút bấm gọi hàm add_data
        st.button("THÊM VÀO KHO", on_click=add_data)
    
    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_right = st.columns(2)
    
    # --- CỘT TRÁI: KHO MAIL ---
    with c_left:
        st.markdown(f'<div class="col-header text-green">KHO ĐANG CHỜ ({len(st.session_state.queue)}) 📦</div>', unsafe_allow_html=True)
        
        if st.session_state.queue:
            if st.button("🗑️ XÓA KHO MAIL"): st.session_state.queue=[]; st.rerun()
            st.markdown("---")
            for i, item in enumerate(st.session_state.queue, 1):
                c_stt, c_code, c_del = st.columns([0.8, 8, 1])
                with c_stt: st.markdown(f"<div style='padding-top:10px;font-weight:bold;color:#8b949e'>#{i}</div>", unsafe_allow_html=True)
                with c_code: st.code(item['Raw'], language="text")
                with c_del:
                    if st.button("❌", key=f"del_q_{i}"):
                        st.session_state.queue.pop(i-1); st.rerun()
        else:
            st.info("Kho trống! Dán dữ liệu rồi bấm Thêm nha ní.")

    # --- CỘT PHẢI: KẾT QUẢ (STYLE MỚI) ---
    with c_right:
        st.markdown(f'<div class="col-header text-blue">KẾT QUẢ ({len(st.session_state.results)}) 📥</div>', unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        
        # LOGIC QUÉT VỚI TEXT DUI DUI
        with b1:
            if st.button("🔥 BẮT ĐẦU QUÉT"):
                if st.session_state.queue:
                    new_q = []
                    status_box = st.empty() # Khung hiện text chạy
                    bar = st.progress(0)
                    
                    # Danh sách câu thoại vui nhộn
                    funny_texts = [
                        "🕵️‍♂️ Đang lẻn vào nhà Microsoft...", 
                        "🚀 Đang phóng tên lửa đi lấy Link...", 
                        "🏃💨 Chạy nhanh hết mức có thể...", 
                        "☕ Làm ngụm cà phê đợi xíu nha...", 
                        "🔎 Đang soi từng cái Mail...",
                        "🐢 Từ từ... Hà Nội không vội được đâu...",
                        "💎 Sắp có hàng ngon rồi..."
                    ]
                    
                    for i, item in enumerate(st.session_state.queue):
                        # Random câu thoại
                        msg = random.choice(funny_texts)
                        status_box.info(f"{msg} ({i+1}/{len(st.session_state.queue)})")
                        
                        link = get_link_with_retry(item)
                        if link: st.session_state.results.append({"Email": item['Email'], "Link": link})
                        else: new_q.append(item)
                        bar.progress((i+1)/len(st.session_state.queue)); time.sleep(0.5)
                    
                    status_box.success("✅ Xong rồi nè! Lụm lúa!")
                    st.session_state.queue=new_q; time.sleep(1); st.rerun()
        
        with b2:
            if st.button("🔍 LỌC TRÙNG"):
                if st.session_state.results:
                    unique = {r['Link']:r for r in st.session_state.results}.values()
                    st.session_state.results = list(unique)
                    st.success("Đã lọc!"); time.sleep(1); st.rerun()

        st.markdown("---")
        
        if st.session_state.results:
            c_copy, c_del = st.columns([2, 1])
            with c_copy:
                if st.button("📋 COPY ALL (CHỈ LINK)"):
                    txt = "\n".join([r['Link'] for r in st.session_state.results])
                    st.code(txt, language="text")
            with c_del:
                if st.button("🗑️ XÓA LOG"): st.session_state.results=[]; st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)

            # HIỂN THỊ KẾT QUẢ: EMAIL TRÊN - LINK DƯỚI
            for i, res in enumerate(st.session_state.results, 1):
                # Tạo Card chứa
                st.markdown(f"""
                <div class="res-card">
                    <div class="res-email">
                        <span class="res-idx">#{i}</span> 📧 {res['Email']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                # Link nằm ngay dưới
                st.code(res['Link'], language="text")
        else:
            st.caption("Chưa có link nào...")

# ================= TAB 2: CHECK LINK =================
with tab2:
    st.header("🕵️ CHECK LIVE/DIE")
    li_at = st.text_input("Dán Cookie li_at:", value="", type="password")
    links_input = st.text_area("Dán list link:", height=150)
    
    if st.button("🚀 CHECK NGAY"):
        if links_input and li_at:
            links = [l.strip() for l in links_input.split('\n') if "http" in l]
            st.session_state.check_results = []
            bar = st.progress(0)
            status_check = st.empty()
            
            for i, link in enumerate(links):
                status_check.info(f"🔎 Đang check cái thứ {i+1}...")
                status = check_link_status(link, li_at)
                st.session_state.check_results.append({"Link": link, "Status": status})
                bar.progress((i+1)/len(links)); time.sleep(1)
            status_check.success("Check xong!")
            
    if st.session_state.check_results:
        def color(row):
             return ['color: #238636; font-weight: bold' if "LIVE" in v else 'color: #da3633' if "DIE" in v else 'color: orange' for v in row]
        st.dataframe(pd.DataFrame(st.session_state.check_results).style.apply(color, axis=1), use_container_width=True)