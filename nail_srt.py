# nail_srt.py — 케어 예약 관리 (한국시간 + 자동 다크모드 + Render연동 + 직관적 수정/삭제)

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
    ok = render_download(FILE_NAME)
    msg = "☁️ Render 복원 완료" if ok else "⚠️ Render 복원 실패"
else:
    ok, msg = True, "로컬 데이터 사용 중"

records_cache = load_json(FILE_PATH, [])
for r in records_cache:
    r.setdefault("사번", "")
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
# UI 스타일 (자동 다크모드 + 글자크기 균형)
# =====================================
st.set_page_config(page_title="케어관리", layout="centered")
st.markdown("""
<style>
section.main, .block-container { padding-top: 2.0rem !important; }
h1 {font-size: 28px !important; text-align:center;}
h2,h3 {font-size:20px !important;}
label, div, span {font-size:18px !important;}
@media (prefers-color-scheme: dark) {
  html, body { background-color:#0b1220 !important; color:#e5e7eb !important; }
  input,textarea,select {background:#111827!important;color:#e5e7eb!important;border:1px solid #334155!important;}
  button,.stButton>button {background:#1f2937!important;color:#e5e7eb!important;border:1px solid #334155!important;}
}
</style>
""", unsafe_allow_html=True)

# =====================================
# 본문
# =====================================
st.title("💆‍♀️ 케어 예약 관리")

# ---------- 기록 추가 ----------
st.header("🧾 기록 추가 및 수정")
name = st.text_input("이름 입력")
emp_id = st.text_input("사번 입력")

existing = next((r for r in st.session_state["records"] if r["사번"] == emp_id.strip()), None)
if existing:
    st.info(f"📌 최근 케어: {existing['케어일자']} / 다음: {existing['한달시점']}")

if st.button("✅ 기록 저장", use_container_width=True):
    if not name or not emp_id:
        st.warning("이름과 사번을 모두 입력하세요.")
    else:
        today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date()
        one_month = today_kst + relativedelta(months=1)
        updated = False
        for r in st.session_state["records"]:
            if r["사번"] == emp_id.strip():
                r.update({
                    "이름": name.strip(),
                    "케어일자": today_kst.strftime("%Y-%m-%d"),
                    "한달시점": one_month.strftime("%Y-%m-%d"),
                    "한달지남": "O" if today_kst >= one_month else "X",
                })
                updated = True
                break
        if not updated:
            st.session_state["records"].append({
                "이름": name.strip(),
                "사번": emp_id.strip(),
                "케어일자": today_kst.strftime("%Y-%m-%d"),
                "한달시점": one_month.strftime("%Y-%m-%d"),
                "한달지남": "O" if today_kst >= one_month else "X",
            })
        save_json(FILE_PATH, st.session_state["records"])
        render_upload(FILE_NAME, st.session_state["records"])
        st.toast("저장 완료 및 Render 반영", icon="✅")
        st.rerun()

# ---------- 전체 명단 ----------
st.header("📋 전체 명단 (선택 시 수정창 자동 반영)")

df = pd.DataFrame(st.session_state["records"])
if len(df) > 0:
    # 선택 컬럼 추가
    df["선택"] = False

    # 테이블 표시
    selected_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        key="table",
        column_config={
            "선택": st.column_config.CheckboxColumn("선택", help="수정할 항목 선택")
        },
    )

    # ✅ 체크된 행 자동 반영
    selected_rows = selected_df[selected_df["선택"] == True]
    record = None
    if not selected_rows.empty:
        record = selected_rows.iloc[0].to_dict()
    else:
        record = None
else:
    st.info("등록된 데이터가 없습니다.")
    record = None

# ---------- 수정 / 삭제 ----------
st.header("✏️ 수정 / 삭제")

if record:
    st.markdown(f"**🆔 사번:** {record['사번']} / 이름: {record['이름']}")
    name_edit = st.text_input("이름 수정", record["이름"], key="edit_name")
    care_edit = st.date_input("케어일자 수정", datetime.strptime(record["케어일자"], "%Y-%m-%d").date(), key="edit_care")
    month_edit = st.date_input("한달시점 수정", datetime.strptime(record["한달시점"], "%Y-%m-%d").date(), key="edit_month")
    flag_edit = st.selectbox("한달지남", ["O", "X"], index=0 if record["한달지남"] == "O" else 1, key="edit_flag")

    col1, col2 = st.columns(2)
    with col1:
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
    with col2:
        if st.button("🗑️ 삭제", use_container_width=True):
            st.session_state["records"] = [
                r for r in st.session_state["records"] if r["사번"] != record["사번"]
            ]
            save_json(FILE_PATH, st.session_state["records"])
            render_upload(FILE_NAME, st.session_state["records"])
            st.toast("삭제 완료", icon="🗑️")
            st.rerun()
else:
    st.info("수정할 항목을 선택하세요.")


# ---------- 검색 및 필터 ----------
st.header("🔍 검색 / 필터")
col1, col2 = st.columns(2)
with col1:
    keyword = st.text_input("이름/사번 검색")
with col2:
    show_expired = st.toggle("⏰ 한달 지난 사람만 보기")

if len(df) > 0:
    filtered = df.copy()
    if keyword.strip():
        filtered = filtered[filtered.apply(
            lambda x: keyword.lower() in x["이름"].lower() or keyword in x["사번"],
            axis=1)]
    if show_expired:
        filtered = filtered[filtered["한달지남"] == "O"]
    st.dataframe(filtered, use_container_width=True, hide_index=True)

# ---------- 하단 상태 ----------
st.markdown(
    f"<p style='text-align:center;font-size:12px;color:#94a3b8;margin-top:8px;'>"
    f"{'✅' if ok else '⚠️'} {msg}</p>",
    unsafe_allow_html=True
)
