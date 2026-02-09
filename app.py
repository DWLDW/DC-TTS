import streamlit as st
import edge_tts
import asyncio
import os
from datetime import datetime
import xml.sax.saxutils # 텍스트 안전하게 변환하는 도구

# --- 페이지 설정 ---
st.set_page_config(page_title="ReadingTown AI Voice", page_icon="🎙️")

# --- 언어별 텍스트 설정 ---
txt = {
    'ko': {
        'title': "AI 성우 녹음기 (SSML 버그 수정완료)",
        'voice_lbl': "목소리 선택 (⭐표시가 연기 천재)",
        'style_lbl': "감정/스타일 (Style)",
        'speed_lbl': "말하기 속도",
        'pitch_lbl': "목소리 톤",
        'input_lbl': "텍스트 입력",
        'btn_gen': "🔊 오디오 생성하기",
        'download': "MP3 다운로드",
        'err_empty': "텍스트를 입력해주세요!"
    },
    'en': {
        'title': "AI Neural Voice Generator (SSML Fixed)",
        'voice_lbl': "Select Voice (⭐ = Expressive)",
        'style_lbl': "Emotion/Style",
        'speed_lbl': "Speech Rate",
        'pitch_lbl': "Voice Pitch",
        'input_lbl': "Enter Text",
        'btn_gen': "🔊 Generate Audio",
        'download': "Download MP3",
        'err_empty': "Please enter text!"
    },
    'zh': {
        'title': "AI 神经网络语音生成器 (SSML修复版)",
        'voice_lbl': "选择语音 (⭐ = 情感丰富)",
        'style_lbl': "情感/风格",
        'speed_lbl': "语速",
        'pitch_lbl': "音调",
        'input_lbl': "输入文本",
        'btn_gen': "🔊 生成音频",
        'download': "下载 MP3",
        'err_empty': "请输入文本！"
    }
}

# --- 비동기 함수 헬퍼 ---
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# --- 목소리 목록 가져오기 ---
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
        
        # 감정 표현 가능 여부 체크
        # Aria, Jenny, Guy, Xiaoxiao가 감정을 잘 살립니다.
        star = "⭐" if clean_name in ["Aria", "Jenny", "Guy", "Xiaoxiao"] else ""
        
        display_name = f"{flag} {tag} {clean_name} ({gender}) {star}"
        voice_list.append(display_name)
        voice_map[display_name] = short_name
        
    voice_list.sort()
    return voice_list, voice_map

# --- 메인 앱 ---
def main():
    with st.sidebar:
        app_lang = st.selectbox("Language / 언어", ["한국어", "English", "中文"])
        if app_lang == "한국어": lang_code = 'ko'
        elif app_lang == "English": lang_code = 'en'
        else: lang_code = 'zh'
        
        t = txt[lang_code]
        
        st.header("Settings")
        
        voice_list, voice_map = get_voices()
        
        # 기본값 (Aria)
        default_idx = 0
        for i, v in enumerate(voice_list):
            if "Aria" in v: default_idx = i; break
            
        selected_display = st.selectbox(t['voice_lbl'], voice_list, index=default_idx)
        selected_id = voice_map[selected_display]
        
        # 감정 스타일 선택
        styles = ["general", "cheerful", "sad", "angry", "terrified", "shouting", "whispering", "friendly", "excited"]
        selected_style = st.selectbox(t['style_lbl'], styles)

        speed = st.slider(t['speed_lbl'], -50, 50, 0, format="%d%%")
        pitch = st.slider(t['pitch_lbl'], -50, 50, 0, format="%dHz")

    st.title(t['title'])
    text_input = st.text_area(t['input_lbl'], height=150, placeholder="Example: Get out of here right now!")

    if st.button(t['btn_gen'], type="primary", use_container_width=True):
        if not text_input.strip():
            st.error(t['err_empty'])
            return

        with st.spinner("Generating Audio..."):
            rate_str = f"{'+' if speed >= 0 else ''}{speed}%"
            pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
            
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"audio_{timestamp}.mp3"
            
            # 특수문자 (<, >, &)가 있으면 SSML이 깨질 수 있으므로 안전하게 변환
            safe_text = xml.sax.saxutils.escape(text_input)

            async def gen():
                if selected_style == "general":
                    # 일반 모드 (속도, 톤 적용)
                    communicate = edge_tts.Communicate(text_input, selected_id, rate=rate_str, pitch=pitch_str)
                    await communicate.save(filename)
                else:
                    # 감정 모드 (SSML)
                    # [중요] f""" 바로 다음에 줄바꿈 없이 <speak>가 오도록 하거나
                    # 나중에 .strip()으로 공백을 싹 제거해야 합니다.
                    ssml_content = f"""
<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'>
    <voice name='{selected_id}'>
        <mstts:express-as style='{selected_style}'>
            <prosody rate='{rate_str}' pitch='{pitch_str}'>
                {safe_text}
            </prosody>
        </mstts:express-as>
    </voice>
</speak>
"""
                    # [핵심 수정] .strip()을 붙여서 맨 앞뒤의 공백/줄바꿈을 제거함
                    # 이제 AI가 "<speak"를 정확히 인식합니다.
                    communicate = edge_tts.Communicate(ssml_content.strip(), selected_id)
                    await communicate.save(filename)

            try:
                run_async(gen())
                st.audio(filename)
                with open(filename, "rb") as f:
                    st.download_button(
                        label=t['download'],
                        data=f,
                        file_name=filename,
                        mime="audio/mp3",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Error: {e}")
                st.warning("이 목소리는 해당 감정을 지원하지 않을 수 있습니다.")

if __name__ == "__main__":
    main()
