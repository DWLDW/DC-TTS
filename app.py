import streamlit as st
import edge_tts
import asyncio
import io
import re

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="Readingtown TTS", page_icon="🎧")

# --- 2. 세션 상태 초기화 ---
if 'file_counters' not in st.session_state:
    st.session_state.file_counters = {}

# --- 3. UI 텍스트 ---
txt = {
    'en': {
        'title': "Readingtown TTS (Pro)",
        'sidebar_header': "Settings",
        'voice_label': "Select Voice",
        'prefix_label': "File Prefix (e.g., 1a1)",
        'input_label': "Enter Text",
        'btn_label': "🔊 Generate Audio",
        'download_label': "Download MP3",
        'err_empty': "Please enter text!"
    },
    'ko': {
        'title': "리딩타운 TTS (Pro)",
        'sidebar_header': "설정 (Settings)",
        'voice_label': "목소리 선택",
        'prefix_label': "파일 이름 접두어 (예: 1a1)",
        'input_label': "텍스트 입력",
        'btn_label': "🔊 오디오 생성하기",
        'download_label': "MP3 다운로드",
        'err_empty': "텍스트를 입력해주세요!"
    },
    'zh': {
        'title': "Readingtown 语音生成器 (Pro)",
        'sidebar_header': "设置 (Settings)",
        'voice_label': "选择语音",
        'prefix_label': "文件名设置 (例如: 1a1)",
        'input_label': "输入文本",
        'btn_label': "🔊 生成音频",
        'download_label': "下载 MP3",
        'err_empty': "请输入文本！"
    }
}

# --- 4. 비동기 실행 함수 (웹 호환성 최적화) ---
async def generate_audio_stream(text, voice, rate, pitch, volume):
    # Pygame 없이 메모리(RAM)에서 오디오 데이터만 생성합니다.
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
    out_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            out_buffer.write(chunk["data"])
    return out_buffer

# --- 5. 목소리 목록 ---
@st.cache_data
def get_voices():
    # 비동기 루프 충돌 방지
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    voices = loop.run_until_complete(edge_tts.list_voices())
    loop.close()
    
    premium_list = []
    normal_list = []
    voice_map = {}
    elite_ids = ["en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural", "zh-CN-XiaoxiaoNeural"]
    
    for v in voices:
        if "Neural" not in v['ShortName']: continue
        short_name = v['ShortName']
        
        if "ko-KR" in short_name: flag, tag = "🇰🇷", "[KR]"
        elif "en-US" in short_name: flag, tag = "🇺🇸", "[US]"
        elif "en-GB" in short_name: flag, tag = "🇬🇧", "[UK]"
        elif "zh-CN" in short_name: flag, tag = "🇨🇳", "[CN]"
        else: continue

        gender = "Female" if v['Gender'] == "Female" else "Male"
        clean_name = short_name.split('-')[-1].replace('Neural', '')
        
        if short_name in elite_ids:
            display_name = f"🌟 [Premium] {flag} {clean_name} ({gender})"
            voice_map[display_name] = short_name
            premium_list.append(display_name)
        else:
            display_name = f"{flag} {tag} {clean_name} ({gender})"
            voice_map[display_name] = short_name
            normal_list.append(display_name)
            
    premium_list.sort()
    normal_list.sort()
    return premium_list + normal_list, voice_map

def sanitize_filename(text):
    clean = re.sub(r'[\\/*?:"<>|]', "", text)
    return clean[:15].strip()

# --- 6. 메인 앱 ---
def main():
    with st.sidebar:
        lang_sel = st.selectbox("Language / 언어", ["English", "한국어", "中文"])
        if lang_sel == "English": lc = 'en'
        elif lang_sel == "한국어": lc = 'ko'
        else: lc = 'zh'
        
        t = txt[lc]
        st.header(t['sidebar_header'])
        
        voice_list, voice_map = get_voices()
        default_idx = 0
        for i, v in enumerate(voice_list):
            if "Aria" in v: default_idx = i; break
        
        selected_display = st.selectbox(t['voice_label'], voice_list, index=default_idx)
        selected_id = voice_map[selected_display]
        
        st.divider()
        speed = st.slider("Speed", -50, 50, 0, format="%d%%")
        pitch = st.slider("Pitch", -50, 50, 0, format="%dHz")
        volume = st.slider("Volume", -50, 50, 0, format="%d%%")

    st.title(t['title'])
    
    col1, col2 = st.columns([1, 3])
    with col1:
        file_prefix = st.text_input(t['prefix_label'], value="1a1")
    
    text_input = st.text_area(t['input_label'], height=150, placeholder="Enter text here...")

    if st.button(t['btn_label'], type="primary", use_container_width=True):
        if not text_input.strip():
            st.error(t['err_empty'])
        else:
            with st.spinner("Processing..."):
                rate_str = f"{'+' if speed >= 0 else ''}{speed}%"
                pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
                volume_str = f"{'+' if volume >= 0 else ''}{volume}%"

                try:
                    # asyncio.run으로 안전하게 비동기 함수 실행
                    audio_buffer = asyncio.run(generate_audio_stream(
                        text_input, selected_id, rate_str, pitch_str, volume_str
                    ))
                    
                    snippet = sanitize_filename(text_input)
                    if file_prefix not in st.session_state.file_counters:
                        st.session_state.file_counters[file_prefix] = 1
                    else:
                        st.session_state.file_counters[file_prefix] += 1
                    
                    count = st.session_state.file_counters[file_prefix]
                    final_name = f"[{file_prefix}] ({count}) {snippet}.mp3"

                    # 결과 표시
                    st.success(f"Ready: {final_name}")
                    st.audio(audio_buffer)
                    
                    st.download_button(
                        label=f"💾 {t['download_label']}",
                        data=audio_buffer,
                        file_name=final_filename, # 오타 수정: final_name
                        mime="audio/mp3",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
