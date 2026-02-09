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
        
        if "ko-KR" in short_name: flag, tag = "🇰🇷", "[KR]"
        elif "en-US" in short_name: flag, tag = "🇺🇸", "[US]"
        elif "en-GB" in short_name: flag, tag = "🇬🇧", "[UK]"
        elif "zh-CN" in short_name: flag, tag = "🇨🇳", "[CN]"
        else: continue

        gender = "여" if v['Gender'] == "Female" else "남"
        clean_name = short_name.split('-')[-1].replace('Neural', '')
        star = "⭐" if clean_name in ["Aria", "Jenny", "Guy", "Xiaoxiao"] else ""
        
        display_name = f"{flag} {tag} {clean_name} ({gender}) {star}"
        voice_list.append(display_name)
        voice_map[display_name] = short_name
        
    voice_list.sort()
    return voice_list, voice_map

# --- 메인 앱 ---
def main():
    st.title("AI 성우 녹음기 (Web)")
    
    with st.sidebar:
        st.header("설정 (Settings)")
        voice_list, voice_map = get_voices()
        
        # 기본값 (Aria)
        default_idx = 0
        for i, v in enumerate(voice_list):
            if "Aria" in v: default_idx = i; break
            
        selected_display = st.selectbox("목소리 선택", voice_list, index=default_idx)
        selected_id = voice_map[selected_display]
        
        # 감정 선택
        styles = ["general (기본)", "cheerful (명랑)", "sad (슬픔)", "angry (화남)", "terrified (겁먹음)", "shouting (외침)", "whispering (속삭임)", "friendly (친근)", "excited (신남)"]
        selected_style_raw = st.selectbox("감정/스타일", styles)
        selected_style = selected_style_raw.split(' ')[0]

        speed = st.slider("말하기 속도", -50, 50, 0, format="%d%%")
        pitch = st.slider("목소리 톤", -50, 50, 0, format="%dHz")

    text_input = st.text_area("텍스트 입력", height=150, placeholder="Get out of here right now!")

    if st.button("🔊 오디오 생성하기", type="primary", use_container_width=True):
        if not text_input.strip():
            st.error("텍스트를 입력해주세요!")
            return

        with st.spinner("오디오 생성 중..."):
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"audio_{timestamp}.mp3"
            
            # 속도/톤 문자열 변환
            rate_str = f"{'+' if speed >= 0 else ''}{speed}%"
            pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"

            async def gen():
                # [수정된 핵심 로직]
                if selected_style == "general":
                    # 1. 일반 모드: 라이브러리에게 속도/톤 처리를 맡김 (가장 안전)
                    communicate = edge_tts.Communicate(text_input, selected_id, rate=rate_str, pitch=pitch_str)
                    await communicate.save(filename)
                else:
                    # 2. 감정 모드: 우리가 직접 SSML을 짬 -> 라이브러리 간섭 차단
                    # 특수문자 처리 (<, >, &)
                    safe_text = text_input.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    
                    # 엔터키 없이 한 줄로 쭉 이어진 SSML 코드
                    ssml_code = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'><voice name='{selected_id}'><mstts:express-as style='{selected_style}'><prosody rate='{rate_str}' pitch='{pitch_str}'>{safe_text}</prosody></mstts:express-as></voice></speak>"
                    
                    # [중요] rate와 pitch 인자를 아예 안 넣어야(None) 이중 포장이 안 됩니다!
                    communicate = edge_tts.Communicate(ssml_code, selected_id)
                    await communicate.save(filename)

            try:
                run_async(gen())
                st.audio(filename)
                with open(filename, "rb") as f:
                    st.download_button(label="MP3 다운로드", data=f, file_name=filename, mime="audio/mp3", use_container_width=True)
            except Exception as e:
                st.error(f"오류: {e}")

if __name__ == "__main__":
    main()
