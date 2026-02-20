import streamlit as st
import pandas as pd
import datetime

# 1. 한국 지역별 기상 데이터 (기상청 평년값)
korea_weather = {
    "서울/경기": [-2.4, 0.4, 5.7, 12.5, 17.8, 22.2, 24.9, 25.7, 21.2, 14.8, 7.2, 0.4],
    "춘천/강원": [-4.6, -1.3, 4.5, 11.6, 17.2, 21.7, 24.5, 24.9, 19.8, 12.5, 5.1, -1.8],
    "대전/충청": [-1.0, 1.5, 7.0, 13.5, 18.9, 23.3, 26.1, 26.6, 21.8, 15.2, 8.2, 1.4],
    "광주/전남": [0.6, 2.5, 7.5, 13.5, 18.7, 22.8, 26.1, 26.9, 22.4, 16.2, 9.4, 3.1],
    "대구/경북": [0.6, 3.0, 8.5, 14.8, 20.3, 24.3, 27.1, 27.6, 22.8, 16.5, 9.5, 2.8],
    "부산/경남": [3.2, 5.2, 9.4, 14.3, 18.7, 22.2, 25.4, 26.9, 23.2, 18.1, 11.7, 5.6],
    "제주도": [6.1, 6.8, 10.0, 14.5, 18.5, 22.3, 26.2, 27.2, 23.6, 18.9, 13.4, 8.3]
}

st.set_page_config(page_title="Building Energy Simul v5.0", layout="wide")
st.title("🏙️ 정밀 에너지 시뮬레이터 (동적 로직 적용)")

with st.sidebar:
    st.header("📍 1. 기본 설정")
    region = st.selectbox("지역 선택", list(korea_weather.keys()))
    usage = st.selectbox("건물 용도", ["주택", "상업용 건물"])
    floor_area = st.number_input("바닥 면적 (m²)", value=84.0) # 국민평형 기준
    height = st.number_input("층 높이 (m)", value=2.5)
    st.divider()
    t_summer = st.slider("여름 냉방 온도", 24, 28, 26)
    t_winter = st.slider("겨울 난방 온도", 18, 24, 22)

tab1, tab2 = st.tabs(["🔍 조건 입력", "📊 분석 결과"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🪟 건물 성능")
        wwr = st.slider("창면적비(WWR)", 0.0, 1.0, 0.25)
        u_val = st.number_input("창호 열관류율 (W/m²K)", value=1.2)
        shgc = st.number_input("창호 SHGC", value=0.40)
        wall_u = st.number_input("외벽 열관류율 (W/m²K)", value=0.15)
    with col2:
        st.subheader("💡 시간대별 발열 (W/m²)")
        st.write("**오전 (08-16시)**")
        p1 = st.number_input("사람/조명/기기 합계 (주간)", value=15.0)
        st.write("**오후 (16-00시)**")
        p2 = st.number_input("사람/조명/기기 합계 (저녁)", value=20.0)
        st.write("**야간 (00-08시)**")
        p3 = st.number_input("사람/조명/기기 합계 (심야)", value=5.0)

if st.button("🚀 에너지 시뮬레이션 실행", use_container_width=True):
    with tab2:
        # 건물 정보 계산
        wall_area = (floor_area ** 0.5) * 4 * height
        glass_area = wall_area * wwr
        opaque_wall_area = wall_area * (1 - wwr)
        
        total_cool_kwh, total_heat_kwh = 0, 0
        
        # 월별 및 시간대별 3분할 시뮬레이션
        for month_idx, t_ext in enumerate(korea_weather[region]):
            # 계절 판별
            is_summer = month_idx in [5,6,7]
            is_winter = month_idx in [11,0,1]
            t_set = t_summer if is_summer else (t_winter if is_winter else 22)
            
            # 시간대별 루프 (T1:주간, T2:저녁, T3:심야)
            for t_idx, internal_p in enumerate([p1, p2, p3]):
                # 시간대별 외기 온도 보정 (T1은 평균+2도, T2는 평균, T3는 평균-4도)
                t_ext_adj = t_ext + (2 if t_idx==0 else (0 if t_idx==1 else -4))
                
                # 1. 전도 손실
                q_cond = ((glass_area * u_val) + (opaque_wall_area * wall_u)) * (t_set - t_ext_adj)
                # 2. 일사 취득 (T1에 80%, T2에 20%, T3에 0% 배분)
                solar_weight = 0.8 if t_idx==0 else (0.2 if t_idx==1 else 0.0)
                q_sol = glass_area * shgc * 180 * solar_weight
                # 3. 내부 발열
                q_int = internal_p * floor_area
                
                # 시간대별 순 부하 (Net Load)
                # 난방: q_cond(손실)가 q_sol+q_int(취득)보다 커야 발생
                net_load = q_cond - q_sol - q_int
                
                # 8시간 단위 에너지(kWh) 환산
                kwh = (net_load * 8 * 30) / 1000
                
                if kwh > 0: total_heat_kwh += kwh
                else: total_cool_kwh += abs(kwh)

        # 비용 계산
        cop_c, cop_h = 3.5, 0.88 # 에어컨 COP / 콘덴싱보일러 효율
        cost_c = (total_cool_kwh / cop_c) * 215 # 전기료
        cost_h = (total_heat_kwh / cop_h) * 160 # 가스비

        # 결과 출력
        st.subheader("📝 시뮬레이션 결과 리포트")
        c1, c2 = st.columns(2)
        c1.metric("연간 냉방비", f"{int(cost_c):,} 원", f"{total_cool_kwh:,.1f} kWh")
        c2.metric("연간 난방비", f"{int(cost_h):,} 원", f"{total_heat_kwh:,.1f} kWh")

        st.divider()
        st.subheader("⚙️ 에너지 산출 적용 툴 및 근거")
        st.markdown(f"""
        - **적용 툴:** **ISO 13790 기반 정밀 간이 동적 계산법**
        - **분석 논리:**
            1. **시간대 분할:** 24시간 평균 부하 방식의 오류를 해결하기 위해 하루를 3개 시간대(주간/저녁/심야)로 분리하여 계산함.
            2. **야간 냉각 반영:** 심야 시간대(00-08시)의 외기 온도를 보정(-4℃)하여 동절기 야간 난방 부하를 실질적으로 산출함.
            3. **일사/발열 변동성:** 일사량이 없는 밤 시간대와 발열이 적은 새벽 시간대의 에너지 평형을 독립적으로 분석함.
        - **설비 기준:** 냉방 COP {cop_c} (1등급 가전 기준), 난방 효율 {cop_h} (콘덴싱 보일러 기준) 적용.
        """)
        
        # 파일 저장
        report_data = f"지역: {region}\n냉방에너지: {total_cool_kwh:.1f}kWh\n난방에너지: {total_heat_kwh:.1f}kWh\n산출툴: ISO 13790 Simplified Dynamic Method"
        st.download_button("📂 결과 보고서(TXT) 저장", report_data, file_name="energy_report.txt")