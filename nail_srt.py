# =====================================
# 💆‍♀️ 케어 예약 관리 v2.3 (단일 선택)
# =====================================
import streamlit as st
import pandas as pd
import json, os, requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo

# =====================================
# ☁️ Render 서버 설정
# =====================================
RENDER_BASE = "https://roadvision-json-server.onrender.com/"
DATA_DIR = "data"
FILE_NAME = "케어관리.json"
FILE_PATH = os.path.join(DATA_DIR, FILE_NAME)

def render_upload(filename, data):
    try:
        res = requests.post(f"{RENDER_BASE}/upload",
                            json={"filename": filename, "content": data},
                            timeout=10)
        return res.ok
    except Exception as e:
        st.toast(f"Render 업로드 실패: {e}", icon="⚠️")
        return False

def render_download(filename, save_as=None):
    try:
        res = requests.get(f"{RENDER_BASE}/download/{filename}", timeout=10)
        if res.ok:
            data = res.json()
            local_path = save_as or os.path.join("data", filename)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
    except Exception as e:
        st.toast(f"Render 복원 실패: {e}", icon="⚠️")
    return False

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =====================================
# 데이터 복원
# =====================================
if not os.path.exists(FILE_PATH):
    render_download(FILE_NAME)
records_cache = load_json(FILE_PATH, [])
st.session_state.setdefault("records", records_cache)

# =====================================
# 한달지남 자동 갱신 (한국시간)
# =====================================
today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date()
for r in st.session_state["records"]:
    try:
        one_month = datetime.strptime(r["한달시점"], "%Y-%m-%d").date()
        r["한달지남"] = "O" if today_kst >= one_month else "X"
    except:
        pass

# =====================================
# 💅 UI 스타일
# =====================================
st.set_page_config(page_title="케어관리", layout="centered")
st.markdown("""
<style>
section.main, .block-container { padding-top: 2.0rem !important; }
h1 {font-size: 28px !important; text-align:center;}
h2, h3 {font-size: 20px !important; text-align:center;}
label, div, span {font-size: 18px !important;}
input, textarea, select {
  font-size: 18px !important;
  padding: 10px 12px !important;
  border-radius: 10px !important;
  background-color: #f8fafc !important;
  color: #111827 !important;
  border: 1px solid #cbd5e1 !important;
}
/* 버튼 */
div[data-testid="stVerticalBlock"] button,
.stButton>button {
  font-size: 18px !important;
  font-weight: 600 !important;
  padding: 12px 0px !important;
  border-radius: 10px !important;
  background: linear-gradient(180deg, #3b82f6, #2563eb) !important;
  color: #ffffff !important;
  border: none !important;
  transition: all 0.15s ease-in-out;
}
div[data-testid="stVerticalBlock"] button:hover,
.stButton>button:hover {
  background: linear-gradient(180deg, #2563eb, #1d4ed8) !important;
  transform: scale(1.02);
}
[data-testid="stDataFrame"] .stDataFrame {
  font-size: 18px !important;
  border-radius: 8px !important;
}
@media (prefers-color-scheme: dark) {
  html, body {background-color: #0b1220 !important; color: #e5e7eb !important;}
  input, textarea, select {
    background: #111827 !important;
    color: #e5e7eb !important;
    border: 1px solid #334155 !important;
  }
  div[data-testid="stVerticalBlock"] button,
  .stButton>button {
    background: linear-gradient(180deg, #1e3a8a, #1e40af) !important;
    color: #e0e7ff !important;
  }
}
</style>
""", unsafe_allow_html=True)

# =====================================
# 본문
# =====================================
st.title("💆‍♀️ 케어 예약 관리")

# ---------- 1️⃣ 기록 추가 ----------
st.header("🧾 기록 추가")
name = st.text_input("이름 입력")
emp_id = st.text_input("사번 입력")

if st.button("✅ 기록 저장", use_container_width=True):
    if not name or not emp_id:
        st.warning("이름과 사번을 모두 입력하세요.")
    else:
        today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date()
        one_month = today_kst + relativedelta(months=1)
        existing = next((r for r in st.session_state["records"] if r["사번"] == emp_id.strip()), None)
        if existing:
            existing.update({
                "이름": name.strip(),
                "케어일자": today_kst.strftime("%Y-%m-%d"),
                "한달시점": one_month.strftime("%Y-%m-%d"),
                "한달지남": "X",
            })
        else:
            st.session_state["records"].append({
                "사번": emp_id.strip(),
                "이름": name.strip(),
                "케어일자": today_kst.strftime("%Y-%m-%d"),
                "한달시점": one_month.strftime("%Y-%m-%d"),
                "한달지남": "X",
            })
        save_json(FILE_PATH, st.session_state["records"])
        render_upload(FILE_NAME, st.session_state["records"])
        st.toast("저장 완료", icon="✅")
        st.rerun()

# ---------- 2️⃣ 검색 ----------
st.header("🔍 검색 / 필터")
keyword = st.text_input("이름/사번 검색")
df = pd.DataFrame(st.session_state["records"])
if keyword.strip():
    filtered = df[df.apply(lambda x: keyword in x["사번"] or keyword in x["이름"], axis=1)]
    if not filtered.empty:
        filtered["선택"] = False
        selected_filtered = st.data_editor(filtered, use_container_width=True, hide_index=True,
                                           key="search_table",
                                           column_config={"선택": st.column_config.CheckboxColumn("선택")})
        sel = selected_filtered[selected_filtered["선택"] == True]
        if not sel.empty:
            idx = sel.index[0]
            for i in selected_filtered.index:
                selected_filtered.at[i, "선택"] = (i == idx)
            chosen = selected_filtered.loc[idx].to_dict()
            st.session_state["selected_record"] = chosen
            st.toast(f"✅ {chosen['이름']} 선택됨", icon="💡")
            st.rerun()
    else:
        st.info("검색 결과 없음")

# ---------- 3️⃣ 수정 / 삭제 ----------
st.header("✏️ 수정 / 삭제")
record = st.session_state.get("selected_record")
if record:
    st.markdown(f"**🆔 {record['사번']} | {record['이름']}**")
    name_edit = st.text_input("이름 수정", record["이름"], key=f"edit_name_{record['사번']}")
    care_edit = st.date_input("케어일자 수정",
                              datetime.strptime(record["케어일자"], "%Y-%m-%d").date(),
                              key=f"edit_care_{record['사번']}")
    month_edit = st.date_input("한달시점 수정",
                               datetime.strptime(record["한달시점"], "%Y-%m-%d").date(),
                               key=f"edit_month_{record['사번']}")
    flag_edit = st.selectbox("한달지남", ["O", "X"],
                             index=0 if record["한달지남"] == "O" else 1,
                             key=f"edit_flag_{record['사번']}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 수정", use_container_width=True):
            for r in st.session_state["records"]:
                if r["사번"] == record["사번"]:
                    r.update({
                        "이름": name_edit,
                        "케어일자": care_edit.strftime("%Y-%m-%d"),
                        "한달시점": month_edit.strftime("%Y-%m-%d"),
                        "한달지남": flag_edit,
                    })
            save_json(FILE_PATH, st.session_state["records"])
            render_upload(FILE_NAME, st.session_state["records"])
            st.toast("수정 완료", icon="✅")
            st.rerun()
    with c2:
        if st.button("🗑 삭제", use_container_width=True):
            st.session_state["records"] = [r for r in st.session_state["records"] if r["사번"] != record["사번"]]
            save_json(FILE_PATH, st.session_state["records"])
            render_upload(FILE_NAME, st.session_state["records"])
            st.toast("삭제 완료", icon="🗑️")
            st.rerun()
else:
    st.caption("항목을 선택하면 수정/삭제 가능합니다.")

# ---------- 4️⃣ 전체 명단 ----------
st.header("📋 전체 명단")
df = pd.DataFrame(st.session_state["records"])
if len(df) > 0:
    latest_date = max(datetime.strptime(r["케어일자"], "%Y-%m-%d") for r in st.session_state["records"])
    st.markdown(f"<p style='font-size:17px; color:#64748b; text-align:center;'>📅 마지막 저장일: <b>{latest_date.strftime('%Y-%m-%d')} (KST)</b></p>", unsafe_allow_html=True)

    st.markdown("**🆕 최근 저장된 3명 (선택 가능)**")
    recent_df = df.tail(3).reset_index(drop=True)
    recent_df["선택"] = False
    selected_recent = st.data_editor(recent_df, use_container_width=True, hide_index=True,
                                     key="recent_table",
                                     column_config={"선택": st.column_config.CheckboxColumn("선택")})
    sel_recent = selected_recent[selected_recent["선택"] == True]
    if not sel_recent.empty:
        idx = sel_recent.index[0]
        for i in selected_recent.index:
            selected_recent.at[i, "선택"] = (i == idx)
        chosen = selected_recent.loc[idx].to_dict()
        st.session_state["selected_record"] = chosen
        st.toast(f"✅ {chosen['이름']} 선택됨", icon="💡")
        st.rerun()

    with st.expander("전체 명단 보기 ▾"):
        df["선택"] = False
        selected_all = st.data_editor(df, use_container_width=True, hide_index=True,
                                      key="all_table",
                                      column_config={"선택": st.column_config.CheckboxColumn("선택")})
        sel_all = selected_all[selected_all["선택"] == True]
        if not sel_all.empty:
            idx = sel_all.index[0]
            for i in selected_all.index:
                selected_all.at[i, "선택"] = (i == idx)
            chosen = selected_all.loc[idx].to_dict()
            st.session_state["selected_record"] = chosen
            st.toast(f"✅ {chosen['이름']} 선택됨", icon="💡")
            st.rerun()
else:
    st.info("등록된 데이터가 없습니다.")
