import streamlit as st
import requests
import re
import pandas as pd
import time
import html
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

    /* Chỉnh lại Code Block cho gọn, căn giữa với STT */
    .stCodeBlock { margin-bottom: 0px !important; }
    div[data-testid="stVerticalBlock"] > div { align-items: center; }
    
    /* STT */
    .stt-label { font-size: 14px; font-weight: bold; color: #8b949e; padding-top: 10px; }

    /* Header cột */
    .col-header { font-size: 16px; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #30363d; padding-bottom: 5px; }
    .text-green { color: #238636; border-color: #238636; }
    .text-blue { color: #58a6ff; border-color: #1f6feb; }
    
    /* Ẩn scrollbar của dataframe cho đẹp */
    .stDataFrame { border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE ---
if 'queue' not in st.session_state: st.session_state.queue = []
if 'results' not in st.session_state: st.session_state.results = []
if 'check_results' not in st.session_state: st.session_state.check_results = []

# --- LOGIC ---
def parse_excel(text):
    valid = []
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        parts = line.split('\t') if "\t" in line else line.split('|')
        while len(parts) < 4: parts.append("")
        # LƯU CẢ DÒNG RAW ĐỂ HIỆN THỊ
        valid.append({
            "Raw": line, 
            "Email": parts[0], 
            "Pass": parts[1], 
            "Token": parts[2], 
            "Client_ID": parts[3]
        })
    return valid

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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.linkedin.com/',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    cookies = {'li_at': li_at_cookie}
    
    try:
        r = requests.get(url, headers=headers, cookies=cookies, timeout=10, allow_redirects=True)
        content = r.text.lower()
        
        if "login" in r.url or "welcome back" in content: return "⚠️ COOKIE DIE (Hết hạn)"
        if "đổi phiếu mua hàng" in content or "premium-chooser__cta" in content: return "✅ LIVE"
        if "redeem gift" in content or "activate subscription" in content: return "✅ LIVE"
        if "already been redeemed" in content or "đã được đổi" in content: return "❌ DIE (Đã dùng)"
        if "offer is no longer active" in content or "không còn hiệu lực" in content: return "❌ DIE (Hết hạn)"
        
        return "❓ UNKNOWN (Check tay)"
        
    except: return "⚠️ LỖI MẠNG"

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 LINKEDIN HUNTER PRO")

tab1, tab2 = st.tabs(["📦 KHO & QUÉT", "⚡ CHECK LINK (LIVE/DIE)"])

# ================= TAB 1: SĂN MAIL =================
with tab1:
    with st.expander("➕ DÁN DỮ LIỆU VÀO ĐÂY (Raw Excel/Text)", expanded=False):
        raw = st.text_area("", height=100, label_visibility="collapsed", placeholder="Email | Pass | Token | ID")
        if st.button("THÊM VÀO KHO"):
            if raw: st.session_state.queue.extend(parse_excel(raw)); st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_right = st.columns(2)
    
    # --- CỘT TRÁI: KHO MAIL (UPDATED) ---
    with c_left:
        st.markdown(f'<div class="col-header text-green">KHO ĐANG CHỜ ({len(st.session_state.queue)}) 📦</div>', unsafe_allow_html=True)
        
        if st.session_state.queue:
            # Nút xóa kho
            if st.button("🗑️ XÓA KHO MAIL"): st.session_state.queue=[]; st.rerun()
            
            st.markdown("---")
            
            # Vòng lặp hiển thị từng dòng
            # enumerate(..., 1) để bắt đầu đếm từ 1
            for i, item in enumerate(st.session_state.queue, 1):
                # Chia cột: [STT] [Nội dung Raw (Copy)] [Nút Xóa]
                c_stt, c_code, c_del = st.columns([0.8, 8, 1])
                
                with c_stt:
                    st.markdown(f"<div class='stt-label'>#{i}</div>", unsafe_allow_html=True)
                
                with c_code:
                    # st.code tự động có nút copy và scroll ngang nếu dài
                    st.code(item['Raw'], language="text")
                
                with c_del:
                    # Nút xóa từng dòng
                    if st.button("❌", key=f"del_q_{i}"):
                        st.session_state.queue.pop(i-1)
                        st.rerun()
        else:
            st.info("Kho đang trống... Dán dữ liệu ở trên đi ní!")

    # --- CỘT PHẢI: KẾT QUẢ ---
    with c_right:
        st.markdown(f'<div class="col-header text-blue">KẾT QUẢ ({len(st.session_state.results)}) 📥</div>', unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔥 BẮT ĐẦU QUÉT"):
                if st.session_state.queue:
                    new_q = []
                    bar = st.progress(0)
                    for i, item in enumerate(st.session_state.queue):
                        link = get_link_with_retry(item)
                        if link: st.session_state.results.append({"Email": item['Email'], "Link": link})
                        else: new_q.append(item)
                        bar.progress((i+1)/len(st.session_state.queue)); time.sleep(0.5)
                    st.session_state.queue=new_q; st.rerun()
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
                if st.button("📋 COPY ALL"):
                    txt = "\n".join([r['Link'] for r in st.session_state.results])
                    st.code(txt, language="text")
            with c_del:
                if st.button("🗑️ XÓA LOG"): st.session_state.results=[]; st.rerun()
            
            for i, res in enumerate(st.session_state.results, 1):
                 # Hiển thị kết quả cũng có STT từ 1
                c_r_stt, c_r_link = st.columns([0.8, 9])
                with c_r_stt: st.markdown(f"<div class='stt-label'>#{i}</div>", unsafe_allow_html=True)
                with c_r_link: st.code(res['Link'], language="text")
        else:
            st.caption("Chưa có link nào...")

# ================= TAB 2: CHECK LINK =================
with tab2:
    st.header("🕵️ CHECK LIVE/DIE")
    li_at = st.text_input("Dán Cookie li_at mới nhất vào đây:", value="", placeholder="Ví dụ: AQEDAWQ6ALwFTvhk...", type="password")
    links_input = st.text_area("Dán list link:", height=150)
    
    if st.button("🚀 CHECK NGAY"):
        if not li_at: st.error("Chưa nhập Cookie kìa ba!")
        elif links_input:
            links = [l.strip() for l in links_input.split('\n') if "http" in l]
            st.session_state.check_results = []
            bar = st.progress(0)
            for i, link in enumerate(links):
                status = check_link_status(link, li_at)
                st.session_state.check_results.append({"Link": link, "Status": status})
                bar.progress((i+1)/len(links)); time.sleep(1)
            st.success("Xong!")
            
    if st.session_state.check_results:
        def color(row):
             return ['color: #238636; font-weight: bold' if "LIVE" in v else 'color: #da3633' if "DIE" in v else 'color: orange' for v in row]
        st.dataframe(pd.DataFrame(st.session_state.check_results).style.apply(color, axis=1), use_container_width=True)