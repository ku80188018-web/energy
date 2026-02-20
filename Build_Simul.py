import streamlit as st
import pandas as pd

# 1. 지역별 기상 데이터 (한국 주요 도시)
korea_weather = {
    "서울/경기": [-2.4, 0.4, 5.7, 12.5, 17.8, 22.2, 24.9, 25.7, 21.2, 14.8, 7.2, 0.4],
    "춘천/강원": [-4.6, -1.3, 4.5, 11.6, 17.2, 21.7, 24.5, 24.9, 19.8, 12.5, 5.1, -1.8],
    "대전/충청": [-1.0, 1.5, 7.0, 13.5, 18.9, 23.3, 26.1, 26.6, 21.8, 15.2, 8.2, 1.4],
    "광주/전남": [0.6, 2.5, 7.5, 13.5, 18.7, 22.8, 26.1, 26.9, 22.4, 16.2, 9.4, 3.1],
    "대구/경북": [0.6, 3.0, 8.5, 14.8, 20.3, 24.3, 27.1, 27.6, 22.8, 16.5, 9.5, 2.8],
    "부산/경남": [3.2, 5.2, 9.4, 14.3, 18.7, 22.2, 25.4, 26.9, 23.2, 18.1, 11.7, 5.6],
    "제주": [6.1, 6.8, 10.0, 14.5, 18.5, 22.3, 26.2, 27.2, 23.6, 18.9, 13.4, 8.3]
}

st.set_page_config(page_title="한국 에너지 시뮬레이터", layout="wide")

st.title("🏙️ 한국형 건물 에너지 시뮬레이터")
st.info("삼성 Galaxy Jump3 등 모바일 기기에서 설치 없이 즉시 작동합니다.")

# 사이드바: 기본 설정
with st.sidebar:
    st.header("📍 기본 정보 설정")
    region = st.selectbox("대상 지역", list(korea_weather.keys()))
    usage = st.selectbox("건물 용도", ["주택", "상업용 건물"])
    floor_area = st.number_input("건물 바닥 면적 (m²)", value=300.0)
    height = st.number_input("층 높이 (m)", value=3.5)
    
    st.divider()
    st.header("🌡️ 설정 온도 (℃)")
    t_cool = st.slider("여름 냉방 온도", 22, 30, 26)
    t_heat = st.slider("겨울 난방 온도", 16, 24, 20)

# 메인 화면: 3개 탭 구성
tab1, tab2 = st.tabs(["🔍 상세 입력", "📊 시뮬레이션 결과"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🪟 유리 성능")
        wwr = st.slider("창면적비(WWR)", 0.0, 1.0, 0.4)
        u_val = st.number_input("유리 열관류율 (U-value)", value=1.5)
        shgc = st.number_input("열취득계수 (SHGC)", value=0.45)
    
    with col2:
        st.subheader("💡 시간대별 내부 발열 (W/m²)")
        p1 = st.number_input("08:00 ~ 16:00 발열", value=30.0)
        p2 = st.number_input("16:00 ~ 00:00 발열", value=15.0)
        p3 = st.number_input("00:00 ~ 08:00 발열", value=5.0)
        avg_gain = (p1 + p2 + p3) / 3

# 계산 로직
if st.button("🚀 시뮬레이션 실행", use_container_width=True):
    with tab2:
        # 물리 계산 (간이 에너지 균형 모델)
        wall_area = (floor_area ** 0.5) * 4 * height # 정방형 건물 가정
        total_cool_kwh, total_heat_kwh = 0, 0
        
        for i, t_ext in enumerate(korea_weather[region]):
            t_target = t_cool if i in [5,6,7] else (t_heat if i in [11,0,1] else 22)
            
            # 열전도 + 일사취득 - 내부발열
            load = ((wall_area * wwr * u_val) + (wall_area * 0.3)) * (t_target - t_ext)
            solar = (wall_area * wwr) * shgc * 170
            net = load - solar - (avg_gain * floor_area)
            
            kwh = (net * 24 * 30) / 1000
            if kwh > 0: total_heat_kwh += kwh
            else: total_cool_kwh += abs(kwh)
        
        # 비용 및 COP
        cop_c, cop_h = 3.6, 0.85
        cost_c = (total_cool_kwh / cop_c) * 210
        cost_h = (total_heat_kwh / cop_h) * 155
        
        # 결과 표시
        c1, c2 = st.columns(2)
        c1.metric("연간 냉방비", f"{int(cost_c):,} 원", f"COP {cop_c}")
        c2.metric("연간 난방비", f"{int(cost_h):,} 원", f"효율 {cop_h}")
        
        st.divider()
        st.subheader("📝 분석 결과 요약")
        result_text = f"""지역: {region} ({usage})
- 연간 냉방 에너지: {total_cool_kwh:,.1f} kWh
- 연간 난방 에너지: {total_heat_kwh:,.1f} kWh
- 평균 내부 발열: {avg_gain:.1f} W/m²
- 적용 유효 면적: {floor_area} m²"""
        st.text(result_text)
        
        st.download_button("📂 결과 보고서 저장 (.txt)", result_text)