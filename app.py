import streamlit as st
import edge_tts
import asyncio
import os
from datetime import datetime
import xml.sax.saxutils

# --- 페이지 설정 ---
st.set_page_config(page_title="ReadingTown AI Voice", page_icon="🎙️")

# --- 언어별 텍스트 ---
txt = {
    'ko': {
        'title': "AI 성우 녹음기 (최종 수정)",
        'voice_lbl': "목소리 선택 (⭐=감정 가능)",
        'style_lbl': "감정 (Aria/Jenny/Guy/Xiaoxiao 전용)",
        'speed_lbl': "말하기 속도",
        'pitch_lbl': "목소리 톤",
        'input_lbl': "텍스트 입력",
        'btn_gen': "🔊 오디오 생성하기",
        'download': "MP3 다운로드",
        'err_empty': "텍스트를 입력해주세요!"
    },
    'en': {
        'title': "AI Voice Generator (Final Fix)",
        'voice_lbl': "Select Voice (⭐=Expressive)",
        'style_lbl': "Emotion (Style)",
        'speed_lbl': "Speech Rate",
        'pitch_lbl': "Voice Pitch",
        'input_lbl': "Enter Text",
        'btn_gen': "🔊 Generate Audio",
        'download': "Download MP3",
        'err_empty': "Please enter text!"
    },
    'zh': {
        'title': "AI 语音生成器 (最终修复)",
        'voice_lbl': "选择语音 (⭐=支持情感)",
        'style_lbl': "情感 (Style)",
        'speed_lbl': "语速",
        'pitch_lbl': "音调",
        'input_lbl': "输入文本",
        'btn_gen': "🔊 生成音频",
        'download': "下载 MP3",
        'err_empty': "请输入文本！"
    }
}

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
    with st.sidebar:
        app_lang = st.selectbox("Language / 언어", ["한국어", "English", "中文"])
        if app_lang == "한국어": lang_code = 'ko'
        elif app_lang == "English": lang_code = 'en'
        else: lang_code = 'zh'
        
        t = txt[lang_code]
        st.header("Settings")
        
        voice_list, voice_map = get_voices()
        default_idx = 0
        for i, v in enumerate(voice_list):
            if "Aria" in v: default_idx = i; break
            
        selected_display = st.selectbox(t['voice_lbl'], voice_list, index=default_idx)
        selected_id = voice_map[selected_display]
        
        styles = ["general", "cheerful", "sad", "angry", "terrified", "shouting", "whispering", "friendly", "excited"]
        selected_style = st.selectbox(t['style_lbl'], styles)

        speed = st.slider(t['speed_lbl'], -50, 50, 0, format="%d%%")
        pitch = st.slider(t['pitch_lbl'], -50, 50, 0, format="%dHz")

    st.title(t['title'])
    text_input = st.text_area(t['input_lbl'], height=150, placeholder="Example: I am so angry right now!")

    if st.button(t['btn_gen'], type="primary", use_container_width=True):
        if not text_input.strip():
            st.error(t['err_empty'])
            return

        with st.spinner("Generating Audio..."):
            rate_str = f"{'+' if speed >= 0 else ''}{speed}%"
            pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
            
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"audio_{timestamp}.mp3"
            
            # 특수문자 탈출 (XML 에러 방지)
            safe_text = xml.sax.saxutils.escape(text_input)

            async def gen():
                # [핵심 수정] 일반 모드와 감정 모드를 완전히 분리
                if selected_style == "general":
                    communicate = edge_tts.Communicate(text_input, selected_id, rate=rate_str, pitch=pitch_str)
                    await communicate.save(filename)
                else:
                    # [핵심 수정] 줄바꿈 없는 한 줄짜리 SSML 생성 (오류 원천 차단)
                    # xmlns:mstts 주소를 https로 변경
                    ssml_one_line = (
                        f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
                        f"xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'>"
                        f"<voice name='{selected_id}'>"
                        f"<mstts:express-as style='{selected_style}'>"
                        f"<prosody rate='{rate_str}' pitch='{pitch_str}'>"
                        f"{safe_text}"
                        f"</prosody>"
                        f"</mstts:express-as>"
                        f"</voice>"
                        f"</speak>"
                    )
                    
                    # rate, pitch 인자를 아예 안 넣어야(None) 이중 포장이 안 됩니다.
                    communicate = edge_tts.Communicate(ssml_one_line, selected_id)
                    await communicate.save(filename)

            try:
                run_async(gen())
                st.audio(filename)
                with open(filename, "rb") as f:
                    st.download_button(label=t['download'], data=f, file_name=filename, mime="audio/mp3", use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
