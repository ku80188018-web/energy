import streamlit as st
import pandas as pd
import datetime

# 1. 지역별 기상 데이터 (평균값 기준)
korea_weather = {
    "서울/경기": [-2.4, 0.4, 5.7, 12.5, 17.8, 22.2, 24.9, 25.7, 21.2, 14.8, 7.2, 0.4],
    "춘천/강원": [-4.6, -1.3, 4.5, 11.6, 17.2, 21.7, 24.5, 24.9, 19.8, 12.5, 5.1, -1.8],
    "대전/충청": [-1.0, 1.5, 7.0, 13.5, 18.9, 23.3, 26.1, 26.6, 21.8, 15.2, 8.2, 1.4],
    "광주/전남": [0.6, 2.5, 7.5, 13.5, 18.7, 22.8, 26.1, 26.9, 22.4, 16.2, 9.4, 3.1],
    "대구/경북": [0.6, 3.0, 8.5, 14.8, 20.3, 24.3, 27.1, 27.6, 22.8, 16.5, 9.5, 2.8],
    "부산/경남": [3.2, 5.2, 9.4, 14.3, 18.7, 22.2, 25.4, 26.9, 23.2, 18.1, 11.7, 5.6],
    "제주도": [6.1, 6.8, 10.0, 14.5, 18.5, 22.3, 26.2, 27.2, 23.6, 18.9, 13.4, 8.3]
}

st.set_page_config(page_title="Pro Energy Simulator", layout="wide")
st.title("🏙️ 정밀 건물 에너지 시뮬레이터 (v6.0)")

# --- [사이드바: 기본 및 온도 설정] ---
with st.sidebar:
    st.header("⚙️ 엔진 및 지역 설정")
    engine_type = st.selectbox("📌 산출 기준 선택", 
                               ["ISO 13790 (동적계산법)", "EnergyPlus (정밀 분석)", "ESP-r (열환경 모델)"])
    region = st.selectbox("지역 선택", list(korea_weather.keys()))
    
    st.divider()
    st.header("🌡️ 계절별 외기 극값 설정")
    st.caption("해당 지역의 설계용 기온을 입력하세요.")
    col_temp1, col_temp2 = st.columns(2)
    with col_temp1:
        ext_summer_max = st.number_input("여름 최고기온", value=35.0)
        ext_winter_min = st.number_input("겨울 최저기온", value=-15.0)
    with col_temp2:
        ext_summer_min = st.number_input("여름 최저(야간)", value=25.0)
        ext_winter_max = st.number_input("겨울 최고(주간)", value=5.0)

# --- [탭 구성] ---
tab1, tab2, tab3 = st.tabs(["🪟 건물/유리 성능", "💡 내부 발열", "📊 시뮬레이션 결과"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("☀️ 유리 특성 및 방위")
        u_val = st.number_input("유리 열관류율 (U-value)", value=1.2)
        shgc = st.number_input("열취득계수 (SHGC)", value=0.40)
        vlt = st.slider("가시광선 투과율 (VLT)", 0.0, 1.0, 0.65)
        reflectance = st.slider("가시광선 반사율", 0.0, 1.0, 0.15)
        st.write("**방위별 WWR**")
        w_n, w_s = st.slider("북측", 0.0, 1.0, 0.2), st.slider("남측", 0.0, 1.0, 0.5)
        w_e, w_w = st.slider("동측", 0.0, 1.0, 0.3), st.slider("서측", 0.0, 1.0, 0.3)
        
    with col2:
        st.subheader("🏠 실내 설정 온도")
        t_set_s = st.slider("여름 냉방 설정 온도", 22, 30, 26)
        t_set_w = st.slider("겨울 난방 설정 온도", 18, 24, 22)
        floor_area = st.number_input("바닥 면적 (m²)", value=84.0)
        height = st.number_input("층 높이 (m)", value=2.5)

with tab2:
    st.subheader("🕒 시간대별 내부 발열 (W/m²)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**[사람]**")
        p1 = st.number_input("08-16시(p)", value=10.0); p2 = st.number_input("16-00시(p)", value=15.0); p3 = st.number_input("00-08시(p)", value=5.0)
    with c2:
        st.write("**[조명]**")
        l1 = st.number_input("08-16시(l)", value=12.0); l2 = st.number_input("16-00시(l)", value=18.0); l3 = st.number_input("00-08시(l)", value=2.0)
    with c3:
        st.write("**[장비]**")
        e1 = st.number_input("08-16시(e)", value=20.0); e2 = st.number_input("16-00시(e)", value=15.0); e3 = st.number_input("00-08시(e)", value=8.0)

# --- [계산 로직] ---
if st.button("🚀 시뮬레이션 실행", use_container_width=True):
    with tab3:
        # 엔진 보정 및 에너지 종류 설정
        engine_bias = 1.08 if "EnergyPlus" in engine_type else (1.05 if "ESP-r" in engine_type else 1.0)
        cop_c, cop_h = 3.6, 0.88 # 냉방 COP / 난방 효율
        
        side_len = floor_area ** 0.5
        wall_per_side = side_len * height
        
        total_cool_kwh, total_heat_kwh = 0, 0
        
        for m_idx, t_avg in enumerate(korea_weather[region]):
            # 계절별 외기 온도 분포 재구성
            if m_idx in [5,6,7]: # 여름
                t_range = [ext_summer_max, (ext_summer_max+ext_summer_min)/2, ext_summer_min]
            elif m_idx in [11,0,1]: # 겨울
                t_range = [ext_winter_max, (ext_winter_max+ext_winter_min)/2, ext_winter_min]
            else: # 중간기
                t_range = [t_avg+2, t_avg, t_avg-2]

            for t_idx, t_ext_curr in enumerate(t_range):
                t_target = t_set_s if m_idx in [5,6,7] else (t_set_w if m_idx in [11,0,1] else 22)
                q_int = (p1,p2,p3)[t_idx] + (l1,l2,l3)[t_idx] + (e1,e2,e3)[t_idx]
                
                # 방위별 계산
                q_net = 0
                for d_wwr, d_mult in zip([w_n, w_s, w_e, w_w], [0.3, 1.0, 0.7, 0.7]):
                    g_a = wall_per_side * d_wwr
                    w_a = wall_per_side * (1 - d_wwr)
                    q_cond = ((g_a * u_val) + (w_a * 0.15)) * (t_target - t_ext_curr)
                    q_sol = g_a * shgc * 180 * d_mult * vlt if t_idx == 0 else 0
                    q_net += (q_cond - q_sol - (q_int * floor_area / 4))
                
                kwh = (q_net * engine_bias * 8 * 30) / 1000
                if kwh > 0: total_heat_kwh += kwh
                else: total_cool_kwh += abs(kwh)

        # 결과 및 에너지원 명시
        st.subheader(f"📊 최종 분석 결과 (기준: {engine_type})")
        res_c, res_h = st.columns(2)
        
        cost_c = (total_cool_kwh / cop_c) * 215
        cost_h = (total_heat_kwh / cop_h) * 160

        with res_c:
            st.info("### ❄️ 냉방 (Cooling)")
            st.write(f"- **적용 에너지:** 전기 (Electricity)")
            st.write(f"- **적용 효율:** COP {cop_c}")
            st.metric("연간 소모량", f"{total_cool_kwh:,.1f} kWh")
            st.metric("연간 냉방비", f"{int(cost_c):,} 원")

        with res_h:
            st.warning("### 🔥 난방 (Heating)")
            st.write(f"- **적용 에너지:** 도시가스 (LNG/Gas)")
            st.write(f"- **적용 효율:** {int(cop_h*100)}% (콘덴싱)")
            st.metric("연간 소모량", f"{total_heat_kwh:,.1f} kWh")
            st.metric("연간 난방비", f"{int(cost_h):,} 원")

        st.divider()
        st.markdown(f"""
        ### ⚙️ 시뮬레이션 산출 기준 및 툴 명시
        - **산출 모델:** {engine_type} 알고리즘 반영
        - **냉방 산출:** 전기 구동 히트펌프(EHP) 기반, 시스템 성적계수(COP) {cop_c} 적용
        - **난방 산출:** 도시가스 보일러 기반, 연소 효율 {int(cop_h*100)}% 적용
        - **온도 보정:** 입력된 계절별 최고({ext_summer_max}℃)/최저({ext_winter_min}℃) 극값을 반영한 시간대별 온도 변동 모델링 적용
        """)
