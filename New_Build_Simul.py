import streamlit as st
import pandas as pd
import datetime

# 1. 한국 주요 지역별 월평균 기온 데이터 (기상청 평년값)
korea_weather = {
    "서울/경기": [-2.4, 0.4, 5.7, 12.5, 17.8, 22.2, 24.9, 25.7, 21.2, 14.8, 7.2, 0.4],
    "춘천/강원": [-4.6, -1.3, 4.5, 11.6, 17.2, 21.7, 24.5, 24.9, 19.8, 12.5, 5.1, -1.8],
    "대전/충청": [-1.0, 1.5, 7.0, 13.5, 18.9, 23.3, 26.1, 26.6, 21.8, 15.2, 8.2, 1.4],
    "광주/전남": [0.6, 2.5, 7.5, 13.5, 18.7, 22.8, 26.1, 26.9, 22.4, 16.2, 9.4, 3.1],
    "대구/경북": [0.6, 3.0, 8.5, 14.8, 20.3, 24.3, 27.1, 27.6, 22.8, 16.5, 9.5, 2.8],
    "부산/경남": [3.2, 5.2, 9.4, 14.3, 18.7, 22.2, 25.4, 26.9, 23.2, 18.1, 11.7, 5.6],
    "제주도": [6.1, 6.8, 10.0, 14.5, 18.5, 22.3, 26.2, 27.2, 23.6, 18.9, 13.4, 8.3]
}

st.set_page_config(page_title="Korea Building Energy Simul", layout="wide")
st.title("🏙️ 한국형 정밀 건물 에너지 시뮬레이터")
st.info("Galaxy Jump3 최적화: 브라우저에서 즉시 실행 및 결과 저장이 가능합니다.")

# --- [입력 섹션 1: 사이드바] ---
with st.sidebar:
    st.header("📍 1. 기본 정보")
    region = st.selectbox("지역 선택", list(korea_weather.keys()))
    usage = st.selectbox("건물 용도", ["주택", "상업용 건물"])
    
    st.divider()
    st.header("📐 2. 건물 규격")
    width = st.number_input("건물 폭 (m)", value=15.0)
    length = st.number_input("건물 길이 (m)", value=20.0)
    height = st.number_input("층 높이 (m)", value=3.0)
    
    st.divider()
    st.header("🌡️ 3. 설정 온도 (℃)")
    t_summer = st.slider("여름 (냉방)", 22, 30, 26)
    t_winter = st.slider("겨울 (난방)", 16, 24, 20)
    t_mid = st.slider("봄/가을", 20, 24, 22)

# --- [입력 섹션 2: 메인 탭] ---
tab1, tab2 = st.tabs(["🔍 상세 입력 (유리/발열)", "📊 시뮬레이션 결과"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🪟 유리 및 외피 성능")
        wwr = st.slider("창면적비 (WWR)", 0.0, 1.0, 0.35)
        u_val = st.number_input("유리 열관류율 (U-value)", value=1.5)
        shgc = st.number_input("열취득계수 (SHGC)", value=0.45)
        vlt = st.slider("가시광선 투과율 (VLT)", 0.0, 1.0, 0.6)
        wall_u = st.number_input("벽체 열관류율 (W/m²K)", value=0.25)

    with col2:
        st.subheader("💡 내부 발열 (W/m²)")
        st.caption("시간대별: [T1] 08-16시 | [T2] 16-00시 | [T3] 00-08시")
        
        # 각 요소별 시간대별 입력
        p_vals = st.multiselect("사람 발열 (T1, T2, T3)", [0, 5, 10, 15, 20], default=[10, 5, 2])
        l_vals = st.multiselect("조명 발열 (T1, T2, T3)", [0, 5, 10, 15, 20], default=[15, 10, 2])
        e_vals = st.multiselect("장비 발열 (T1, T2, T3)", [0, 5, 10, 15, 20, 30], default=[20, 15, 5])
        
        # 리스트 길이 보정 (에러 방지)
        p_vals = (p_vals + [0,0,0])[:3]
        l_vals = (l_vals + [0,0,0])[:3]
        e_vals = (e_vals + [0,0,0])[:3]

# --- [계산 및 결과] ---
if st.button("🚀 시뮬레이션 실행 및 결과 산출", use_container_width=True):
    with tab2:
        # 1. 면적 및 발열 합산
        floor_area = width * length
        wall_area = 2 * height * (width + length)
        
        t1_total = p_vals[0] + l_vals[0] + e_vals[0]
        t2_total = p_vals[1] + l_vals[1] + e_vals[1]
        t3_total = p_vals[2] + l_vals[2] + e_vals[2]
        avg_gain = (t1_total + t2_total + t3_total) / 3

        # 2. 월별 에너지 루프
        total_cool_kwh, total_heat_kwh = 0, 0
        for i, t_ext in enumerate(korea_weather[region]):
            t_set = t_summer if i in [5,6,7] else (t_winter if i in [11,0,1] else t_mid)
            
            # 물리 엔진 수식
            loss = ((wall_area * wwr * u_val) + (wall_area * (1-wwr) * wall_u)) * (t_set - t_ext)
            solar = (wall_area * wwr) * shgc * 165 # 국내 표준 일사 강도 가중치
            net_load = loss - solar - (avg_gain * floor_area)
            
            kwh = (net_load * 24 * 30) / 1000
            if kwh > 0: total_heat_kwh += kwh
            else: total_cool_kwh += abs(kwh)

        # 3. 비용 환산 (한국 기준)
        cop_c, cop_h = 3.6, 0.85
        cost_c = (total_cool_kwh / cop_c) * 210 # 전기 단가
        cost_h = (total_heat_kwh / cop_h) * 155 # 가스 단가

        # 4. 결과 출력
        st.success(f"✅ {region} 지역 시뮬레이션 완료")
        c1, c2, c3 = st.columns(3)
        c1.metric("연간 냉방 에너지", f"{total_cool_kwh:,.1f} kWh")
        c2.metric("연간 난방 에너지", f"{total_heat_kwh:,.1f} kWh")
        c3.metric("평균 내부발열", f"{avg_gain:.1f} W/m²")

        col_a, col_b = st.columns(2)
        col_a.info(f"❄️ 냉방 비용: {int(cost_c):,} 원\n(적용 COP: {cop_c})")
        col_b.warning(f"🔥 난방 비용: {int(cost_h):,} 원\n(적용 효율: {cop_h})")

        # --- [산출 근거 및 보고서] ---
        st.divider()
        st.subheader("📊 시뮬레이션 산출 근거")
        
        explanation = f"""
### 1. 시간대별 내부 발열 요약 (W/m²)
- **08:00~16:00 (T1):** 총 {t1_total:.1f} (사람:{p_vals[0]}, 조명:{l_vals[0]}, 장비:{e_vals[0]})
- **16:00~00:00 (T2):** 총 {t2_total:.1f} (사람:{p_vals[1]}, 조명:{l_vals[1]}, 장비:{e_vals[1]})
- **00:00~08:00 (T3):** 총 {t3_total:.1f} (사람:{p_vals[2]}, 조명:{l_vals[2]}, 장비:{e_vals[2]})

### 2. 열부하 계산 공식
- **전도 부하 ($Q_{{cond}}$):** 외벽 및 창호를 통한 열 이동량
  - 수식: $(U_{{glass}} \cdot A_{{glass}} + U_{{wall}} \cdot A_{{wall}}) \cdot (T_{{room}} - T_{{out}})$
- **일사 부하 ($Q_{{sol}}$):** 창호를 통해 유입되는 태양 복사 에너지
  - 수식: $A_{{glass}} \cdot SHGC \cdot I_{{solar}}$ (가중 일사강도 165W/m² 적용)
- **내부 부하 ($Q_{{int}}$):** 재실자 및 기기 발열량의 합산값

### 3. 비용 산정 기준
- **냉방비:** (연간 냉방부하 / COP {cop_c}) × 210원/kWh (한국전력 평균 단가)
- **난방비:** (연간 난방부하 / 효율 {cop_h}) × 155원/kWh (도시가스 열량 단가 기준)
        """
        st.markdown(explanation)
        
        # 파일 저장 기능
        full_report = f"보고서 생성일: {datetime.datetime.now()}\n" + explanation
        st.download_button("📂 결과 보고서 저장 (.txt)", full_report, file_name=f"energy_report_{region}.txt")