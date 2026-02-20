import streamlit as st
import pandas as pd
import datetime

# 1. 한국 주요 지역별 기상 데이터
korea_weather = {
    "서울/경기": [-2.4, 0.4, 5.7, 12.5, 17.8, 22.2, 24.9, 25.7, 21.2, 14.8, 7.2, 0.4],
    "춘천/강원": [-4.6, -1.3, 4.5, 11.6, 17.2, 21.7, 24.5, 24.9, 19.8, 12.5, 5.1, -1.8],
    "대전/충청": [-1.0, 1.5, 7.0, 13.5, 18.9, 23.3, 26.1, 26.6, 21.8, 15.2, 8.2, 1.4],
    "광주/전남": [0.6, 2.5, 7.5, 13.5, 18.7, 22.8, 26.1, 26.9, 22.4, 16.2, 9.4, 3.1],
    "대구/경북": [0.6, 3.0, 8.5, 14.8, 20.3, 24.3, 27.1, 27.6, 22.8, 16.5, 9.5, 2.8],
    "부산/경남": [3.2, 5.2, 9.4, 14.3, 18.7, 22.2, 25.4, 26.9, 23.2, 18.1, 11.7, 5.6],
    "제주도": [6.1, 6.8, 10.0, 14.5, 18.5, 22.3, 26.2, 27.2, 23.6, 18.9, 13.4, 8.3]
}

st.set_page_config(page_title="Building Energy Simul", layout="wide")
st.title("🏙️ 한국형 건물 에너지 시뮬레이터 (v4.0)")

# 사이드바 설정
with st.sidebar:
    st.header("📍 1. 기본 설정")
    region = st.selectbox("지역 선택", list(korea_weather.keys()))
    usage = st.selectbox("건물 용도", ["주택", "상업용 건물"])
    floor_area = st.number_input("바닥 면적 (m²)", value=100.0)
    height = st.number_input("층 높이 (m)", value=3.0)
    st.divider()
    t_summer = st.slider("여름 냉방 온도", 24, 28, 26)
    t_winter = st.slider("겨울 난방 온도", 18, 22, 20)

tab1, tab2 = st.tabs(["🔍 상세 입력", "📊 결과 및 근거"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🪟 유리 성능")
        wwr = st.slider("창면적비(WWR)", 0.0, 1.0, 0.3)
        u_val = st.number_input("유리 열관류율 (U-value)", value=1.5)
        shgc = st.number_input("열취득계수 (SHGC)", value=0.45)
    with col2:
        st.subheader("💡 시간대별 내부 발열 (W/m²)")
        # 사람 발열
        st.write("**사람 (People)**")
        p1, p2, p3 = st.columns(3)
        p1_val = p1.number_input("08-16(p)", value=10.0)
        p2_val = p2.number_input("16-00(p)", value=5.0)
        p3_val = p3.number_input("00-08(p)", value=2.0)
        # 조명 발열
        st.write("**조명 (Lighting)**")
        l1, l2, l3 = st.columns(3)
        l1_val = l1.number_input("08-16(l)", value=15.0)
        l2_val = l2.number_input("16-00(l)", value=10.0)
        l3_val = l3.number_input("00-08(l)", value=2.0)
        # 장비 발열
        st.write("**장비 (Equipment)**")
        e1, e2, e3 = st.columns(3)
        e1_val = e1.number_input("08-16(e)", value=20.0)
        e2_val = e2.number_input("16-00(e)", value=15.0)
        e3_val = e3.number_input("00-08(e)", value=5.0)

if st.button("🚀 시뮬레이션 실행", use_container_width=True):
    with tab2:
        # 시간대별 합산
        t1_gain = p1_val + l1_val + e1_val
        t2_gain = p2_val + l2_val + e2_val
        t3_gain = p3_val + l3_val + e3_val
        avg_gain = (t1_gain + t2_gain + t3_gain) / 3
        
        # 계산 엔진
        wall_area = (floor_area ** 0.5) * 4 * height
        total_cool, total_heat = 0, 0
        for i, t_ext in enumerate(korea_weather[region]):
            t_set = t_summer if i in [5,6,7] else (t_winter if i in [11,0,1] else 22)
            load = ((wall_area * wwr * u_val) + (wall_area * 0.3)) * (t_set - t_ext)
            solar = (wall_area * wwr) * shgc * 165
            net = load - solar - (avg_gain * floor_area)
            kwh = (net * 24 * 30) / 1000
            if kwh > 0: total_heat += kwh
            else: total_cool += abs(kwh)

        cop_c, cop_h = 3.6, 0.85
        cost_c = (total_cool / cop_c) * 210
        cost_h = (total_heat / cop_h) * 155

        # 출력
        st.success(f"✅ {region} 지역 계산 완료")
        m1, m2 = st.columns(2)
        m1.metric("연간 냉방비", f"{int(cost_c):,} 원", f"소모량: {total_cool:,.1f}kWh")
        m2.metric("연간 난방비", f"{int(cost_h):,} 원", f"소모량: {total_heat:,.1f}kWh")

        st.divider()
        st.subheader("📊 산출 근거 안내")
        explanation = f"""
        **1. 입력 발열 분석 (W/m²)**
        - 08:00~16:00 합계: {t1_gain:.1f}
        - 16:00~00:00 합계: {t2_gain:.1f}
        - 00:00~08:00 합계: {t3_gain:.1f}
        
        **2. 물리 수식 근거**
        - **냉난방 부하:** 전도열손실 - 일사취득 - 내부발열
        - **비용 산정:** 냉방(COP {cop_c}, 210원/kWh), 난방(효율 {cop_h}, 155원/kWh)
        - **기상 데이터:** 기상청 제공 {region} 평년 외기온도 적용
        """
        st.markdown(explanation)
        st.download_button("📂 결과 보고서 저장", f"지역: {region}\n{explanation}")