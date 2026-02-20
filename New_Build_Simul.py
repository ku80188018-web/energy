import streamlit as st
import pandas as pd

# 1. 한국 지역별 기상 데이터
korea_weather = {
    "서울/경기": [-2.4, 0.4, 5.7, 12.5, 17.8, 22.2, 24.9, 25.7, 21.2, 14.8, 7.2, 0.4],
    "춘천/강원": [-4.6, -1.3, 4.5, 11.6, 17.2, 21.7, 24.5, 24.9, 19.8, 12.5, 5.1, -1.8],
    "대전/충청": [-1.0, 1.5, 7.0, 13.5, 18.9, 23.3, 26.1, 26.6, 21.8, 15.2, 8.2, 1.4],
    "광주/전남": [0.6, 2.5, 7.5, 13.5, 18.7, 22.8, 26.1, 26.9, 22.4, 16.2, 9.4, 3.1],
    "대구/경북": [0.6, 3.0, 8.5, 14.8, 20.3, 24.3, 27.1, 27.6, 22.8, 16.5, 9.5, 2.8],
    "부산/경남": [3.2, 5.2, 9.4, 14.3, 18.7, 22.2, 25.4, 26.9, 23.2, 18.1, 11.7, 5.6],
    "제주": [6.1, 6.8, 10.0, 14.5, 18.5, 22.3, 26.2, 27.2, 23.6, 18.9, 13.4, 8.3]
}

st.set_page_config(page_title="Building Energy Simul", layout="wide")
st.title("🏙️ 한국형 건물 에너지 시뮬레이터")

# 사이드바 입력창
with st.sidebar:
    st.header("📍 기본 설정")
    region = st.selectbox("지역 선택", list(korea_weather.keys()))
    usage = st.selectbox("건물 용도", ["주택", "상업용 건물"])
    floor_area = st.number_input("바닥 면적 (m²)", value=100.0)
    height = st.number_input("층 높이 (m)", value=3.0)
    st.divider()
    t_cool = st.slider("여름 냉방 온도", 24, 28, 26)
    t_heat = st.slider("겨울 난방 온도", 18, 22, 20)

# 메인 탭
tab1, tab2 = st.tabs(["🔍 상세 조건 입력", "📊 시뮬레이션 결과"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🪟 유리 성능")
        wwr = st.slider("창면적비(WWR)", 0.0, 1.0, 0.3)
        u_val = st.number_input("유리 열관류율 (U-value)", value=1.5)
        shgc = st.number_input("열취득계수 (SHGC)", value=0.45)
    with col2:
        st.subheader("💡 내부 발열 (W/m²)")
        p1 = st.number_input("오전(08-16시)", value=30.0)
        p2 = st.number_input("오후(16-00시)", value=15.0)
        p3 = st.number_input("야간(00-08시)", value=5.0)

# 시뮬레이션 실행
if st.button("🚀 에너지 시뮬레이션 실행", use_container_width=True):
    with tab2:
        # 물리 계산 엔진
        wall_area = (floor_area ** 0.5) * 4 * height
        avg_gain = (p1 + p2 + p3) / 3
        total_cool_kwh, total_heat_kwh = 0, 0
        
        for i, t_ext in enumerate(korea_weather[region]):
            t_target = t_cool if i in [5,6,7] else (t_heat if i in [11,0,1] else 22)
            # 산출 수식: 전도 - 일사취득 - 내부발열
            load = ((wall_area * wwr * u_val) + (wall_area * 0.3)) * (t_target - t_ext)
            solar = (wall_area * wwr) * shgc * 165
            net = load - solar - (avg_gain * floor_area)
            
            kwh = (net * 24 * 30) / 1000
            if kwh > 0: total_heat_kwh += kwh
            else: total_cool_kwh += abs(kwh)

        cop_c, cop_h = 3.6, 0.85
        cost_c = (total_cool_kwh / cop_c) * 210
        cost_h = (total_heat_kwh / cop_h) * 155

        # 결과 리포트
        c1, c2 = st.columns(2)
        c1.metric("예상 냉방비", f"{int(cost_c):,} 원")
        c2.metric("예상 난방비", f"{int(cost_h):,} 원")

        st.divider()
        # 산출 근거 기술 (st.markdown 내부에서만 작성)
        st.subheader("📊 에너지 산출 근거")
        explanation = f"""
        본 결과는 아래의 물리적 근거를 바탕으로 산출되었습니다:
        
        1. **전도 열손실 ($Q_{{cond}}$):** 건물 외피({wall_area:.1f}m²)를 통한 열 이동. 
           - 수식: $(U_{{glass}} \cdot A_{{glass}} + U_{{wall}} \cdot A_{{wall}}) \cdot \Delta T$
        2. **일사 열취득 ($Q_{{sol}}$):** 창호를 통해 유입되는 태양 에너지. 
           - 수식: $A_{{glass}} \cdot SHGC \cdot 165W/m²$ (국내 평균 일사량 기준)
        3. **내부 발열 ($Q_{{int}}$):** 입력된 평균 발열 {avg_gain:.1f} W/m² 반영.
        4. **운영 효율:** 냉방 COP {cop_c} 및 난방 효율 {cop_h} 적용.
        """
        st.markdown(explanation)
        st.download_button("📂 결과 보고서 저장", explanation + f"\n냉방비: {cost_c}\n난방비: {cost_h}")