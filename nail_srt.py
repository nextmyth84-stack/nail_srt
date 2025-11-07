import streamlit as st
import pandas as pd
import json, os, requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os, streamlit as st

#file_path = "data/케어관리.json"
#if os.path.exists(file_path):
#    os.remove(file_path)
#    st.success("✅ 로컬 케어관리.json 삭제 완료")
#else:
#    st.info("ℹ️ 이미 파일이 삭제되어 있습니다.")



# =====================================
# 🌐 Render 서버 URL
# =====================================
RENDER_BASE = "https://roadvision-json-server.onrender.com"  # ← 네 Render 주소로 교체
DATA_DIR = "data"
FILE_NAME = "케어관리.json"
FILE_PATH = os.path.join(DATA_DIR, FILE_NAME)

# =====================================
# 📦 공용 함수
# =====================================
def render_upload(filename):
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        return False, "로컬 파일 없음"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, "application/json")}
            res = requests.post(f"{RENDER_BASE}/upload", files=files, timeout=10)
        if res.status_code == 200:
            return True, "Render 업로드 완료"
        else:
            return False, f"업로드 실패 ({res.status_code})"
    except Exception as e:
        return False, f"업로드 오류: {e}"

def render_download(filename):
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = os.path.join(DATA_DIR, filename)
    try:
        res = requests.get(f"{RENDER_BASE}/download?file={filename}", timeout=10)
        if res.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(res.content)
            return True, "Render 복원 완료"
        else:
            return False, f"복원 실패 ({res.status_code})"
    except Exception as e:
        return False, f"복원 오류: {e}"

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
# 🗂 데이터 복원
# =====================================
if not os.path.exists(FILE_PATH):
    ok, msg = render_download(FILE_NAME)
else:
    ok, msg = True, "로컬 데이터 사용 중"

records_cache = load_json(FILE_PATH, [])
st.session_state.setdefault("records", records_cache)

# =====================================
# 🧾 한달지남 자동 갱신
# =====================================
today = datetime.now().date()
for r in st.session_state["records"]:
    try:
        one_month_date = datetime.strptime(r["한달시점"], "%Y-%m-%d").date()
        r["한달지남"] = "O" if today >= one_month_date else "X"
    except:
        pass

# =====================================
# 🧾 UI 본문
# =====================================
st.set_page_config(page_title="케어 예약 관리", layout="centered")
st.title("💆‍♀️ 케어 예약 관리")

st.subheader("🧾 케어 기록 추가")

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("이름 입력:")
with col2:
    emp_id = st.text_input("사번 입력:")

# ✅ 기존 기록 요약 표시 (사번 기준)
if emp_id.strip():
    existing = next((r for r in st.session_state["records"] if r["사번"] == emp_id.strip()), None)
    if existing:
        st.markdown(
            f"<p style='font-size:13px; color:#64748b;'>"
            f"📌 {existing['이름']}님의 마지막 케어일: <b>{existing['케어일자']}</b> / "
            f"한달시점: <b>{existing['한달시점']}</b></p>",
            unsafe_allow_html=True,
        )

if st.button("기록 추가") and name.strip() and emp_id.strip():
    today = datetime.now().date()
    one_month = today + relativedelta(months=1)
    updated = False

    for r in st.session_state["records"]:
        if r["사번"] == emp_id.strip():
            r["이름"] = name.strip()
            r["케어일자"] = today.strftime("%Y-%m-%d")
            r["한달시점"] = one_month.strftime("%Y-%m-%d")
            r["한달지남"] = "O" if today >= one_month else "X"
            updated = True
            break

    if not updated:
        st.session_state["records"].append({
            "이름": name.strip(),
            "사번": emp_id.strip(),
            "케어일자": today.strftime("%Y-%m-%d"),
            "한달시점": one_month.strftime("%Y-%m-%d"),
            "한달지남": "O" if today >= one_month else "X",
        })
        st.success(f"✅ {name} ({emp_id}) 님의 새 케어 기록이 추가되었습니다.")
    else:
        st.warning(f"♻️ {name} ({emp_id}) 님의 케어 기록이 갱신되었습니다.")

    # ✅ 저장 및 업로드
    save_json(FILE_PATH, st.session_state["records"])
    ok, msg = render_upload(FILE_NAME)

# =====================================
# 📋 표 및 검색 + 필터
# =====================================
if st.session_state["records"]:
    st.divider()
    st.subheader("📋 전체 케어 명단")
    df = pd.DataFrame(st.session_state["records"])
    st.dataframe(df, use_container_width=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔍 검색")
        keyword = st.text_input("이름 또는 사번으로 검색:")
    with col2:
        st.write("")
        show_expired = st.button("⏰ 한달 지난 사람만 보기")

    if keyword.strip():
        filtered = df[df.apply(lambda x: keyword.strip().lower() in x["이름"].lower() or keyword.strip() in x["사번"], axis=1)]
        if not filtered.empty:
            st.dataframe(filtered, use_container_width=True)
        else:
            st.warning("검색 결과가 없습니다.")
    elif show_expired:
        filtered = df[df["한달지남"] == "O"]
        if not filtered.empty:
            st.dataframe(filtered, use_container_width=True)
        else:
            st.info("한달이 지난 사람이 없습니다.")
else:
    st.info("아직 기록이 없습니다. 이름과 사번을 입력하고 [기록 추가] 버튼을 눌러보세요.")

# =====================================
# 📥 다운로드 & 상태표시 (하단)
# =====================================
if st.session_state["records"]:
    df = pd.DataFrame(st.session_state["records"])
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 엑셀 다운로드", csv, "케어관리_현황.csv", "text/csv")

# ✅ Render 상태 하단 표시
st.markdown(
    f"<p style='text-align:center; font-size:13px; color:#94a3b8; margin-top:20px;'>"
    f"{'✅' if ok else '⚠️'} {msg}</p>",
    unsafe_allow_html=True
)
