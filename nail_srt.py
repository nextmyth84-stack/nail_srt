import streamlit as st
import pandas as pd
import json, os, requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

# =====================================
# ☁️ Render 서버 설정
# =====================================
RENDER_BASE = "https://roadvision-json-server.onrender.com/"
DATA_DIR = "data"
FILE_NAME = "케어관리.json"
FILE_PATH = os.path.join(DATA_DIR, FILE_NAME)

def render_upload(filename, data):
    """Render 서버 업로드 (JSON 전송 방식)"""
    try:
        res = requests.post(
            f"{RENDER_BASE}/upload",
            json={"filename": filename, "content": data},
            timeout=10,
        )
        return res.ok
    except Exception as e:
        st.warning(f"Render 업로드 실패: {e}")
        return False

def render_download(filename, save_as=None):
    """Render 서버에서 JSON 복원"""
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
        st.warning(f"Render 복원 실패: {e}")
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
# 🗂 데이터 복원
# =====================================
if not os.path.exists(FILE_PATH):
    ok = render_download(FILE_NAME)
    msg = "Render 복원 완료" if ok else "Render 복원 실패"
else:
    ok, msg = True, "로컬 데이터 사용 중"

records_cache = load_json(FILE_PATH, [])
for r in records_cache:
    if "사번" not in r:
        r["사번"] = ""
st.session_state.setdefault("records", records_cache)

# =====================================
# 한달지남 자동 갱신
# =====================================
today = datetime.now().date()
for r in st.session_state["records"]:
    try:
        one_month_date = datetime.strptime(r["한달시점"], "%Y-%m-%d").date()
        r["한달지남"] = "O" if today >= one_month_date else "X"
    except:
        pass

# =====================================
# UI 시작
# =====================================
st.set_page_config(page_title="케어 예약 관리", layout="centered")
st.title("💆‍♀️ 케어 예약 관리")

st.subheader("🧾 케어 기록 추가")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("이름 입력:")
with col2:
    emp_id = st.text_input("사번 입력:")

# ✅ 기존 기록 요약
if emp_id.strip():
    existing = next((r for r in st.session_state["records"] if r.get("사번") == emp_id.strip()), None)
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

    save_json(FILE_PATH, st.session_state["records"])
    ok = render_upload(FILE_NAME, st.session_state["records"])
    msg = "Render 업로드 완료" if ok else "Render 업로드 실패"

# =====================================
# 표 표시 + 수정/삭제
# =====================================
if st.session_state["records"]:
    st.divider()
    st.subheader("📋 전체 케어 명단")
    df = pd.DataFrame(st.session_state["records"])
    st.dataframe(df, use_container_width=True)

    # ===========================
    # ✏️ 수정 / 삭제 기능
    # ===========================
    st.divider()
    st.subheader("⚙️ 수정 및 삭제")

    target_id = st.selectbox("수정/삭제할 사번 선택:", [r["사번"] for r in st.session_state["records"]])
    target = next((r for r in st.session_state["records"] if r["사번"] == target_id), None)

    if target:
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("이름 수정:", value=target["이름"])
            new_care = st.date_input("케어일 수정:", datetime.strptime(target["케어일자"], "%Y-%m-%d").date())
        with col2:
            new_month = st.date_input("한달시점 수정:", datetime.strptime(target["한달시점"], "%Y-%m-%d").date())
            new_flag = st.selectbox("한달지남:", ["O", "X"], index=0 if target["한달지남"] == "O" else 1)

        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("💾 수정 저장"):
                target["이름"] = new_name
                target["케어일자"] = new_care.strftime("%Y-%m-%d")
                target["한달시점"] = new_month.strftime("%Y-%m-%d")
                target["한달지남"] = new_flag
                save_json(FILE_PATH, st.session_state["records"])
                ok = render_upload(FILE_NAME, st.session_state["records"])
                st.success("✅ 수정 완료 및 Render 반영")
        with btn2:
            if st.button("🗑️ 삭제"):
                st.session_state["records"] = [r for r in st.session_state["records"] if r["사번"] != target_id]
                save_json(FILE_PATH, st.session_state["records"])
                ok = render_upload(FILE_NAME, st.session_state["records"])
                st.warning("🗑️ 해당 기록 삭제 및 Render 반영 완료")

    # ===========================
    # 🔍 검색 및 필터
    # ===========================
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
# 다운로드 & 하단 상태표시
# =====================================
if st.session_state["records"]:
    df = pd.DataFrame(st.session_state["records"])
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 엑셀 다운로드", csv, "케어관리_현황.csv", "text/csv")

st.markdown(
    f"<p style='text-align:center; font-size:13px; color:#94a3b8; margin-top:20px;'>"
    f"{'✅' if ok else '⚠️'} {msg}</p>",
    unsafe_allow_html=True
)
