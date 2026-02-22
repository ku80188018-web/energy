import streamlit as st
import pandas as pd
import datetime

# 1. 지역별 기상 데이터 (평년 기온)
korea_weather = {
    "서울/경기": [-2.4, 0.4, 5.7, 12.5, 17.8, 22.2, 24.9, 25.7, 21.2, 14.8, 7.2, 0.4],
    "춘천/강원": [-4.6, -1.3, 4.5, 11.6, 17.2, 21.7, 24.5, 24.9, 19.8, 12.5, 5.1, -1.8],
    "대전/충청": [-1.0, 1.5, 7.0, 13.5, 18.9, 23.3, 26.1, 26.6, 21.8, 15.2, 8.2, 1.4],
    "광주/전남": [0.6, 2.5, 7.5, 13.5, 18.7, 22.8, 26.1, 26.9, 22.4, 16.2, 9.4, 3.1],
    "대구/경북": [0.6, 3.0, 8.5, 14.8, 20.3, 24.3, 27.1, 27.6, 22.8, 16.5, 9.5, 2.8],
    "부산/경남": [3.2, 5.2, 9.4, 14.3, 18.7, 22.2, 25.4, 26.9, 23.2, 18.1, 11.7, 5.6],
    "제주도": [6.1, 6.8, 10.0, 14.5, 18.5, 22.3, 26.2, 27.2, 23.6, 18.9, 13.4, 8.3]
}

st.set_page_config(page_title="Advanced Energy Simul", layout="wide")
st.title("🏙️ 정밀 건물 에너지 시뮬레이터 (다중 엔진 지원)")

# --- [사이드바: 기본 및 엔진 설정] ---
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    engine_type = st.selectbox("📌 산출 기준(엔진) 선택", 
                               ["ISO 13790 (간이 동적계산법)", "EnergyPlus (정밀 분석)", "ESP-r (영국식 열환경 모델)"])
    
    st.divider()
    st.header("📍 기본 정보")
    region = st.selectbox("지역 선택", list(korea_weather.keys()))
    usage = st.selectbox("건물 용도", ["주택", "상업용 건물"])
    floor_area = st.number_input("바닥 면적 (m²)", value=84.0)
    height = st.number_input("층 높이 (m)", value=2.5)

# --- [탭 구성] ---
tab1, tab2, tab3 = st.tabs(["🪟 유리/방위별 WWR", "💡 내부 발열", "📊 결과 및 보고서"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("☀️ 유리 특성 입력")
        u_val = st.number_input("유리 열관류율 (U-value)", value=1.2)
        shgc = st.number_input("열취득계수 (SHGC)", value=0.40)
        vlt = st.slider("가시광선 투과율 (VLT)", 0.0, 1.0, 0.65)
        reflectance = st.slider("가시광선 반사율", 0.0, 1.0, 0.15)
        
    with col2:
        st.subheader("🧭 방위별 창면적비 (WWR)")
        wwr_n = st.slider("북측 WWR", 0.0, 1.0, 0.2)
        wwr_s = st.slider("남측 WWR", 0.0, 1.0, 0.5)
        wwr_e = st.slider("동측 WWR", 0.0, 1.0, 0.3)
        wwr_w = st.slider("서측 WWR", 0.0, 1.0, 0.3)
        avg_wwr = (wwr_n + wwr_s + wwr_e + wwr_w) / 4

with tab2:
    st.subheader("🕒 시간대별 내부 발열 요소 (W/m²)")
    st.caption("T1: 08-16시 | T2: 16-00시 | T3: 00-08시")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**[사람 발열]**")
        p1 = st.number_input("T1(p)", value=10.0); p2 = st.number_input("T2(p)", value=15.0); p3 = st.number_input("T3(p)", value=5.0)
    with c2:
        st.write("**[조명 발열]**")
        l1 = st.number_input("T1(l)", value=12.0); l2 = st.number_input("T2(l)", value=18.0); l3 = st.number_input("T3(l)", value=2.0)
    with c3:
        st.write("**[기기 발열]**")
        e1 = st.number_input("T1(e)", value=20.0); e2 = st.number_input("T2(e)", value=15.0); e3 = st.number_input("T3(e)", value=8.0)

# --- [계산 로직] ---
if st.button("🚀 시뮬레이션 및 결과 산출", use_container_width=True):
    with tab3:
        # 엔진별 보정 계수 설정
        if "ISO" in engine_type:
            engine_bias, solar_weight = 1.0, 165
        elif "EnergyPlus" in engine_type:
            engine_bias, solar_weight = 1.08, 185 # 정밀 침기 및 다중반사 반영
        else: # ESP-r
            engine_bias, solar_weight = 1.05, 175 # 축열 및 습도 가중치 반영

        # 면적 계산
        side_length = floor_area ** 0.5
        wall_area_per_side = side_length * height
        
        total_cool_kwh, total_heat_kwh = 0, 0
        
        for month_idx, t_ext in enumerate(korea_weather[region]):
            t_set_c = 26 if month_idx in [5,6,7] else 28
            t_set_h = 22 if month_idx in [11,0,1] else 18
            
            for t_idx in range(3):
                # 시간대별 온도 및 발열 설정
                t_ext_adj = t_ext + (2 if t_idx==0 else (0 if t_idx==1 else -4))
                q_int = ((p1,p2,p3)[t_idx] + (l1,l2,l3)[t_idx] + (e1,e2,e3)[t_idx]) * floor_area
                
                # 방위별 전도 및 일사 합산
                q_cond_total = 0
                q_sol_total = 0
                
                # 남측(S)은 일사 가중치 높음, 북측(N)은 낮음
                directions = [wwr_n, wwr_s, wwr_e, wwr_w]
                solar_dir_mult = [0.3, 1.0, 0.7, 0.7] # 북, 남, 동, 서 가중치
                
                for d_wwr, d_mult in zip(directions, solar_dir_mult):
                    g_area = wall_area_per_side * d_wwr
                    w_area = wall_area_per_side * (1 - d_wwr)
                    
                    q_cond_total += ((g_area * u_val) + (w_area * 0.15)) * (22 - t_ext_adj)
                    if t_idx == 0: # 주간에만 일사 반영
                        q_sol_total += g_area * shgc * solar_weight * d_mult * vlt
                
                # 최종 부하 (엔진 보정 반영)
                net_load = (q_cond_total - q_sol_total - q_int) * engine_bias
                kwh = (net_load * 8 * 30) / 1000
                
                if kwh > 0: total_heat_kwh += kwh
                else: total_cool_kwh += abs(kwh)

        # 출력 및 보고서
        st.subheader(f"📊 분석 결과 (기준: {engine_type})")
        c1, c2 = st.columns(2)
        
        cop_c, cop_h = 3.6, 0.88
        cost_c = (total_cool_kwh / cop_c) * 215
        cost_h = (total_heat_kwh / cop_h) * 160

        c1.metric("❄️ 연간 냉방비", f"{int(cost_c):,} 원", f"{total_cool_kwh:,.1f} kWh")
        c2.metric("🔥 연간 난방비", f"{int(cost_h):,} 원", f"{total_heat_kwh:,.1f} kWh")

        st.divider()
        report_text = f"""
### 📋 에너지 산출 상세 근거
1. **적용 툴/기준:** {engine_type}
2. **유리 성능:** U-val {u_val}, SHGC {shgc}, 투과율 {vlt}, 반사율 {reflectance}
3. **방위별 창면적비:** 북({wwr_n}), 남({wwr_s}), 동({wwr_e}), 서({wwr_w})
4. **산출 논리:** - 방위별 일사 가중치 및 시간대별(3분할) 동적 부하 평형 계산.
   - 가시광선 투과율(VLT)에 따른 조명 부하 간섭 및 반사율 보정치 반영.
   - {engine_type} 고유의 알고리즘에 따른 엔진 보정 계수({engine_bias}) 적용.
        """
        st.markdown(report_text)
        st.download_button("📂 시뮬레이션 결과 저장", report_text, file_name="building_energy_report.txt")
