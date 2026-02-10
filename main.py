import streamlit as st
import requests
import re
import pandas as pd
import time
import html
import json
import os
import streamlit.components.v1 as components

# --- CẤU HÌNH ---
st.set_page_config(page_title="Hunter Pro Clean", page_icon="⚡", layout="wide")
components.html("""<meta name="google" content="notranslate">""", height=0)

# --- CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif; }
    
    /* INPUT STYLE */
    .stTextArea textarea { 
        background-color: #161b22 !important; 
        color: #58a6ff !important; 
        border: 2px solid #30363d; 
        border-radius: 8px; 
        font-family: monospace; 
    }
    
    /* BUTTON STYLE */
    .stButton>button { 
        width: 100%; border-radius: 8px; font-weight: 600; border: none; height: 40px; 
        background-color: #238636; color: white; transition: 0.2s; 
    }
    .stButton>button:hover { opacity: 0.9; }
    
    /* CARD KẾT QUẢ */
    .card { padding: 8px; margin-bottom: 8px; border-radius: 6px; font-size: 12px; background-color: #161b22; border: 1px solid #30363d; word-wrap: break-word; }
    
    .col-green { border-top: 4px solid #2ea043; } .card-success { border-left: 3px solid #2ea043; }
    .col-yellow { border-top: 4px solid #d29922; } .card-warning { border-left: 3px solid #d29922; }
    .col-red { border-top: 4px solid #f85149; } .card-fail { border-left: 3px solid #f85149; }

    .col-title { text-align: center; font-weight: bold; padding: 10px; margin-bottom: 10px; border-radius: 6px; font-size: 14px; text-transform: uppercase; }
    .bg-green { background-color: #1f4026; color: #4ade80; border: 1px solid #2ea043; }
    .bg-yellow { background-color: #3f2e08; color: #facc15; border: 1px solid #d29922; }
    .bg-red { background-color: #3f1214; color: #f87171; border: 1px solid #f85149; }

    .email-txt { color: #8b949e; margin-bottom: 4px; font-weight: 600; }
    .content-txt { font-family: monospace; }
    
    /* Thanh Loading Chuẩn Màu Xanh */
    .stProgress > div > div > div > div { background-color: #2ea043; }
    </style>
    """, unsafe_allow_html=True)

# --- BỘ NHỚ ---
DB_FILE = 'memory_data.json'

def load_memory():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"res_success": [], "res_warning": [], "res_fail": []}

def save_memory():
    data = {
        "res_success": st.session_state.res_success,
        "res_warning": st.session_state.res_warning,
        "res_fail": st.session_state.res_fail
    }
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

# --- INIT STATE ---
saved_data = load_memory()
if 'res_success' not in st.session_state: st.session_state.res_success = saved_data['res_success']
if 'res_warning' not in st.session_state: st.session_state.res_warning = saved_data['res_warning']
if 'res_fail' not in st.session_state: st.session_state.res_fail = saved_data['res_fail']
if 'check_results' not in st.session_state: st.session_state.check_results = []
if 'input_raw' not in st.session_state: st.session_state.input_raw = ""
if 'temp_scan_queue' not in st.session_state: st.session_state.temp_scan_queue = [] 

# --- LOGIC ---
def parse_excel(text):
    valid = []
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        parts = line.split('\t') if "\t" in line else line.split('|')
        while len(parts) < 4: parts.append("")
        valid.append({ "Raw": line, "Email": parts[0], "Pass": parts[1], "Token": parts[2], "Client_ID": parts[3] })
    return valid

def process_mail_logic(item):
    try:
        data = {"client_id": item['Client_ID'], "grant_type": "refresh_token", "refresh_token": item['Token'], "scope": "https://graph.microsoft.com/Mail.Read"}
        r = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data, timeout=5).json()
        acc = r.get("access_token")
        if not acc: return "FAIL", "Token Die"

        headers = {"Authorization": f"Bearer {acc}"}
        res = requests.get("https://graph.microsoft.com/v1.0/me/messages?$search=\"LinkedIn OR Microsoft\"&$top=5", headers=headers, timeout=8).json()
        
        has_bill_text = False 
        if 'value' in res:
            for mail in res['value']:
                body = mail['body']['content'].lower()
                match = re.search(r'https://www\.linkedin\.com/premium/redeem\?[^\s"\'<>]+', mail['body']['content'])
                if match: return "SUCCESS", html.unescape(match.group(0))
                if "your purchase of microsoft 365 premium" in body: has_bill_text = True
            if has_bill_text: return "WARNING", "Bill: MS 365 Premium"
            return "FAIL", "Không có Link/Bill"
        return "FAIL", "Hộp thư trống"
    except: return "FAIL", "Lỗi mạng"

def check_link_status(url, li_at_cookie):
    if not li_at_cookie: return "⚠️ THIẾU COOKIE"
    headers = { 'authority': 'www.linkedin.com', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36', }
    cookies = {'li_at': li_at_cookie}
    try:
        r = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        c = r.text.lower()
        if "login" in r.url: return "⚠️ COOKIE DIE"
        if "đổi phiếu" in c or "redeem" in c or "activate" in c: return "✅ LIVE"
        if "already" in c or "đã được đổi" in c: return "❌ DIE (Đã dùng)"
        return "❌ DIE (Hết hạn)"
    except: return "⚠️ LỖI"

# --- CALLBACK: RESET KHI CÓ INPUT MỚI ---
def on_click_start_scan():
    if st.session_state.input_raw:
        # 1. RESET SẠCH KẾT QUẢ CŨ (Làm mới từ đầu)
        st.session_state.res_success = []
        st.session_state.res_warning = []
        st.session_state.res_fail = []
        
        # 2. Đẩy dữ liệu mới vào hàng chờ
        st.session_state.temp_scan_queue = parse_excel(st.session_state.input_raw)
        
        # 3. Xóa ô nhập liệu
        st.session_state.input_raw = ""

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ LINKEDIN HUNTER PRO")

tab1, tab2 = st.tabs(["🔥 SĂN & PHÂN LOẠI", "⚡ CHECK LINK"])

with tab1:
    st.text_area("DÁN MAIL VÀO ĐÂY RỒI BẤM NÚT DƯỚI 👇", height=120, placeholder="Email|Pass|Token|ID", key="input_raw")
    
    # Placeholder cho thanh loading
    status_text_placeholder = st.empty()
    progress_bar_placeholder = st.empty()

    c_btn_1, c_btn_2, c_btn_3 = st.columns([2, 1, 1])
    with c_btn_1:
        st.button("🚀 NẠP & QUÉT NGAY", type="primary", on_click=on_click_start_scan)
    with c_btn_2:
        filter_btn = st.button("🧹 LỌC TRÙNG")
    with c_btn_3:
        if st.button("🗑️ XÓA SẠCH"):
            st.session_state.res_success = []
            st.session_state.res_warning = []
            st.session_state.res_fail = []
            save_memory()
            st.rerun()

    # --- LOGIC QUÉT ---
    if st.session_state.temp_scan_queue:
        items = st.session_state.temp_scan_queue
        total = len(items)
        
        # Tạo thanh loading chuẩn Streamlit
        my_bar = progress_bar_placeholder.progress(0)

        for i, item in enumerate(items):
            # Cập nhật text trạng thái
            status_text_placeholder.caption(f"⏳ Đang xử lý ({i+1}/{total}): {item['Email']}")
            
            # Xử lý mail
            status, content = process_mail_logic(item)
            if status == "SUCCESS":
                st.session_state.res_success.append({"Email": item['Email'], "Pass": item['Pass'], "Content": content})
            elif status == "WARNING":
                st.session_state.res_warning.append({"Email": item['Email'], "Pass": item['Pass'], "Content": content})
            else:
                st.session_state.res_fail.append({"Email": item['Email'], "Pass": item['Pass'], "Content": content})
            
            # Lưu và cập nhật thanh chạy
            save_memory()
            my_bar.progress((i + 1) / total)
        
        # Xong việc
        st.session_state.temp_scan_queue = []
        status_text_placeholder.empty() # Xóa chữ trạng thái
        progress_bar_placeholder.empty() # Xóa thanh loading
        st.success("✅ Đã quét xong!")
        time.sleep(1)
        st.rerun()

    # --- LOGIC LỌC TRÙNG ---
    if filter_btn:
        with status_text_placeholder.container():
             st.info("🧹 Đang dọn dẹp dữ liệu trùng...")
             prog = st.progress(0)
             time.sleep(0.3)
             
             if st.session_state.res_success:
                 unique = {r['Content']:r for r in st.session_state.res_success}.values()
                 st.session_state.res_success = list(unique)
             prog.progress(50)
             if st.session_state.res_warning:
                 unique = {r['Email']:r for r in st.session_state.res_warning}.values()
                 st.session_state.res_warning = list(unique)
             if st.session_state.res_fail:
                 unique = {r['Email']:r for r in st.session_state.res_fail}.values()
                 st.session_state.res_fail = list(unique)
             
             save_memory()
             prog.progress(100)
             time.sleep(0.5)
             
        status_text_placeholder.empty()
        st.success("✅ Đã lọc sạch!")
        time.sleep(1); st.rerun()

    st.markdown("---")
    
    # KẾT QUẢ
    col_green, col_yellow, col_red = st.columns(3)

    with col_green:
        st.markdown(f'<div class="col-title bg-green">🟢 CÓ LINK ({len(st.session_state.res_success)})</div>', unsafe_allow_html=True)
        if st.session_state.res_success:
            txt = "\n".join([r['Content'] for r in st.session_state.res_success])
            st.code(txt, language="text")
            for r in st.session_state.res_success:
                st.markdown(f"""<div class="card card-success"><div class="email-txt">📧 {r["Email"]}</div><div class="content-txt" style="color:#4ade80;">{r['Content']}</div></div>""", unsafe_allow_html=True)

    with col_yellow:
        st.markdown(f'<div class="col-title bg-yellow">🟡 CÓ BILL ({len(st.session_state.res_warning)})</div>', unsafe_allow_html=True)
        if st.session_state.res_warning:
            txt = "\n".join([f"{r['Email']}|{r['Pass']}" for r in st.session_state.res_warning])
            st.code(txt, language="text")
            for r in st.session_state.res_warning:
                st.markdown(f"""<div class="card card-warning"><div class="email-txt">📧 {r['Email']}</div><div style="color:#facc15;font-weight:bold;">⚠️ {r['Content']}</div><div style="font-size:10px;color:#666;">Pass: {r['Pass']}</div></div>""", unsafe_allow_html=True)

    with col_red:
        st.markdown(f'<div class="col-title bg-red">🔴 FAIL ({len(st.session_state.res_fail)})</div>', unsafe_allow_html=True)
        if st.session_state.res_fail:
            txt = "\n".join([f"{r['Email']}|{r['Pass']}" for r in st.session_state.res_fail])
            st.code(txt, language="text")
            for r in st.session_state.res_fail:
                st.markdown(f"""<div class="card card-fail"><div class="email-txt">📧 {r['Email']}</div><div style="color:#f87171;">❌ {r['Content']}</div></div>""", unsafe_allow_html=True)

with tab2:
    st.header("⚡ CHECK LIVE/DIE")
    li_at = st.text_input("Dán Cookie li_at:", type="password")
    links_input = st.text_area("Dán list link:", height=150)
    check_status = st.empty()
    check_prog = st.empty()
    
    if st.button("🚀 CHECK NGAY"):
        if li_at and links_input:
            links = [l.strip() for l in links_input.split('\n') if "http" in l]
            st.session_state.check_results = []
            
            bar = check_prog.progress(0)
            
            for i, l in enumerate(links):
                check_status.caption(f"🔎 Checking {i+1}/{len(links)}...")
                s = check_link_status(l, li_at)
                st.session_state.check_results.append({"Link": l, "Status": s})
                bar.progress((i+1)/len(links))
                time.sleep(0.5)
            
            check_status.empty()
            check_prog.empty()
            st.success("Xong!")

    if st.session_state.check_results:
        def color(row): return ['color: #2ea043; font-weight: bold' if "LIVE" in v else 'color: #f85149' if "DIE" in v else 'color: orange' for v in row]
        st.dataframe(pd.DataFrame(st.session_state.check_results).style.apply(color, axis=1), use_container_width=True)