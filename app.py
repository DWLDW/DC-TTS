import streamlit as st
import edge_tts
import asyncio
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="ReadingTown AI Voice", page_icon="🎙️")

# --- 비동기 헬퍼 ---
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# --- 목소리 목록 ---
@st.cache_data
def get_voices():
    voices = run_async(edge_tts.list_voices())
    voice_list = []
    voice_map = {}
    
    for v in voices:
        short_name = v['ShortName']
        if "Neural" not in short_name: continue
        
        # 언어 필터링
        if "ko-KR" in short_name: flag, tag = "🇰🇷", "[KR]"
        elif "en-US" in short_name: flag, tag = "🇺🇸", "[US]"
        elif "en-GB" in short_name: flag, tag = "🇬🇧", "[UK]"
        elif "zh-CN" in short_name: flag, tag = "🇨🇳", "[CN]"
        else: continue

        gender = "여" if v['Gender'] == "Female" else "남"
        clean_name = short_name.split('-')[-1].replace('Neural', '')
        
        display_name = f"{flag} {tag} {clean_name} ({gender})"
        voice_list.append(display_name)
        voice_map[display_name] = short_name
        
    voice_list.sort()
    return voice_list, voice_map

# --- 메인 앱 ---
def main():
    st.title("AI 성우 녹음기 (Pro)")
    st.caption("속도, 톤, 볼륨을 자유롭게 조절하세요.")
    
    with st.sidebar:
        st.header("설정 (Settings)")
        voice_list, voice_map = get_voices()
        
        # 기본값 (Aria)
        default_idx = 0
        for i, v in enumerate(voice_list):
            if "Aria" in v: default_idx = i; break
            
        selected_display = st.selectbox("목소리 선택", voice_list, index=default_idx)
        selected_id = voice_map[selected_display]
        
        st.write("---")
        # 1. 속도 (Speed)
        speed = st.slider("말하기 속도 (Speed)", -50, 50, 0, format="%d%%")
        
        # 2. 톤 (Pitch) - 복구 완료!
        pitch = st.slider("목소리 톤 (Pitch)", -50, 50, 0, format="%dHz", help="왼쪽: 굵은 목소리 / 오른쪽: 가는 목소리")
        
        # 3. 볼륨 (Volume) - 신규 추가!
        volume = st.slider("소리 크기 (Volume)", -50, 50, 0, format="%d%%", help="소리가 너무 작으면 키워보세요.")

    text_input = st.text_area("텍스트 입력", height=150, placeholder="Hello! Welcome to ReadingTown.")

    if st.button("🔊 오디오 생성하기", type="primary", use_container_width=True):
        if not text_input.strip():
            st.error("텍스트를 입력해주세요!")
            return

        with st.spinner("오디오 생성 중..."):
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"audio_{timestamp}.mp3"
            
            # 파라미터 문자열 변환
            rate_str = f"{'+' if speed >= 0 else ''}{speed}%"
            pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
            volume_str = f"{'+' if volume >= 0 else ''}{volume}%"

            async def gen():
                # [안전 제일] SSML 코드를 쓰지 않고, 라이브러리 정식 기능을 사용합니다.
                # 이렇게 하면 코드를 읽는 버그가 절대 생기지 않습니다.
                communicate = edge_tts.Communicate(
                    text_input, 
                    selected_id, 
                    rate=rate_str, 
                    pitch=pitch_str, 
                    volume=volume_str
                )
                await communicate.save(filename)

            try:
                run_async(gen())
                
                # 듣기 및 다운로드
                st.audio(filename)
                with open(filename, "rb") as f:
                    st.download_button(
                        label="MP3 다운로드",
                        data=f,
                        file_name=filename,
                        mime="audio/mp3",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"오류: {e}")

if __name__ == "__main__":
    main()
