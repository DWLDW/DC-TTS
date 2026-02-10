import streamlit as st
import edge_tts
import asyncio
import io
from datetime import datetime

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="Readingtown TTS", page_icon="🎧")

# --- 2. 다국어 UI 사전 ---
txt = {
    'en': {
        'title': "Readingtown TTS (Pro)",
        'sidebar_header': "Settings",
        'lang_label': "Interface Language",
        'voice_label': "Select Voice",
        'speed_label': "Speed",
        'pitch_label': "Pitch",
        'vol_label': "Volume",
        'input_label': "Enter Text",
        'btn_label': "🔊 Generate Audio",
        'download_label': "Download MP3",
        'err_empty': "Please enter text!",
        'caption': "Premium voices are marked with 🌟."
    },
    'ko': {
        'title': "리딩타운 TTS (Pro)",
        'sidebar_header': "설정 (Settings)",
        'lang_label': "프로그램 언어",
        'voice_label': "목소리 선택",
        'speed_label': "말하기 속도",
        'pitch_label': "목소리 톤 (높낮이)",
        'vol_label': "소리 크기 (볼륨)",
        'input_label': "텍스트 입력",
        'btn_label': "🔊 오디오 생성하기",
        'download_label': "MP3 다운로드",
        'err_empty': "텍스트를 입력해주세요!",
        'caption': "🌟 표시가 붙은 목소리가 가장 품질이 좋습니다."
    },
    'zh': {
        'title': "Readingtown 语音生成器 (Pro)",
        'sidebar_header': "设置 (Settings)",
        'lang_label': "界面语言",
        'voice_label': "选择语音",
        'speed_label': "语速",
        'pitch_label': "音调",
        'vol_label': "音量",
        'input_label': "输入文本",
        'btn_label': "🔊 生成音频",
        'download_label': "下载 MP3",
        'err_empty': "请输入文本！",
        'caption': "带 🌟 标记的语音质量最高。"
    }
}

# --- 3. 비동기 헬퍼 ---
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# --- 4. 목소리 목록 가져오기 (프리미엄 우선 정렬) ---
@st.cache_data
def get_voices():
    voices = run_async(edge_tts.list_voices())
    
    premium_list = [] # 좋은 목소리 담을 통
    normal_list = []  # 일반 목소리 담을 통
    voice_map = {}
    
    # 마이크로소프트 공인 '고성능(Expressive)' 목소리 리스트
    elite_ids = [
        "en-US-AriaNeural", 
        "en-US-GuyNeural", 
        "en-US-JennyNeural", 
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunxiNeural"
    ]
    
    for v in voices:
        short_name = v['ShortName']
        if "Neural" not in short_name: continue
        
        # 언어 필터링
        if "ko-KR" in short_name: flag, tag = "🇰🇷", "[KR]"
        elif "en-US" in short_name: flag, tag = "🇺🇸", "[US]"
        elif "en-GB" in short_name: flag, tag = "🇬🇧", "[UK]"
        elif "zh-CN" in short_name: flag, tag = "🇨🇳", "[CN]"
        else: continue

        gender = "Female" if v['Gender'] == "Female" else "Male"
        clean_name = short_name.split('-')[-1].replace('Neural', '')
        
        # 프리미엄 여부 확인
        if short_name in elite_ids:
            display_name = f"🌟 [Premium] {flag} {clean_name} ({gender})"
            voice_map[display_name] = short_name
            premium_list.append(display_name)
        else:
            display_name = f"{flag} {tag} {clean_name} ({gender})"
            voice_map[display_name] = short_name
            normal_list.append(display_name)
        
    # 정렬: 프리미엄 먼저 가나다순, 그 뒤에 일반형 가나다순
    premium_list.sort()
    normal_list.sort()
    
    return premium_list + normal_list, voice_map

# --- 5. 메인 앱 로직 ---
def main():
    with st.sidebar:
        app_lang_sel = st.selectbox("Language / 언어 / 语言", ["English", "한국어", "中文"])
        
        if app_lang_sel == "English": lang_code = 'en'
        elif app_lang_sel == "한국어": lang_code = 'ko'
        else: lang_code = 'zh'
        
        t = txt[lang_code]
        st.header(t['sidebar_header'])
        
        voice_list, voice_map = get_voices()
        
        # 기본값 선택 (Aria가 있으면 Aria, 없으면 첫 번째)
        default_idx = 0
        for i, v in enumerate(voice_list):
            if "Aria" in v: default_idx = i; break
            
        selected_display = st.selectbox(t['voice_label'], voice_list, index=default_idx)
        selected_id = voice_map[selected_display]
        
        st.divider()
        speed = st.slider(t['speed_label'], -50, 50, 0, format="%d%%")
        pitch = st.slider(t['pitch_label'], -50, 50, 0, format="%dHz")
        volume = st.slider(t['vol_label'], -50, 50, 0, format="%d%%")

    st.title(t['title'])
    st.caption(t['caption'])
    
    text_input = st.text_area(t['input_label'], height=150, placeholder="Hello! Try the Premium voices.")

    if st.button(t['btn_label'], type="primary", use_container_width=True):
        if not text_input.strip():
            st.error(t['err_empty'])
            return

        with st.spinner("Processing..."):
            rate_str = f"{'+' if speed >= 0 else ''}{speed}%"
            pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
            volume_str = f"{'+' if volume >= 0 else ''}{volume}%"

            async def gen():
                communicate = edge_tts.Communicate(
                    text_input, 
                    selected_id, 
                    rate=rate_str, 
                    pitch=pitch_str, 
                    volume=volume_str
                )
                
                out_buffer = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        out_buffer.write(chunk["data"])
                return out_buffer

            try:
                audio_buffer = run_async(gen())
                st.audio(audio_buffer)
                
                from datetime import datetime
                timestamp = datetime.now().strftime("%H%M%S")
                
                st.download_button(
                    label=t['download_label'],
                    data=audio_buffer,
                    file_name=f"Readingtown_{timestamp}.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
