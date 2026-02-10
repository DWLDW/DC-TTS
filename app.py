import streamlit as st
import edge_tts
import asyncio
import io
import re

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="Readingtown TTS", page_icon="🎧")

# --- 2. 세션 초기화 ---
if 'file_counters' not in st.session_state:
    st.session_state.file_counters = {}

# --- 3. 다국어 UI ---
txt = {
    'en': {
        'title': "Readingtown TTS (Ultimate)",
        'sidebar_header': "Settings",
        'lang_label': "Interface Language",
        'voice_label': "Select Voice",
        'speed_label': "Speed",
        'pitch_label': "Pitch",
        'vol_label': "Volume",
        'prefix_label': "File Name Prefix (e.g., 1a1)",
        'input_label': "Enter Text",
        'btn_label': "🔊 Generate Audio",
        'download_label': "Download MP3",
        'err_empty': "Please enter text!",
        'caption': "Try 'Multilingual' voices for best quality!"
    },
    'ko': {
        'title': "리딩타운 TTS (모든 목소리)",
        'sidebar_header': "설정 (Settings)",
        'lang_label': "프로그램 언어",
        'voice_label': "목소리 선택",
        'speed_label': "말하기 속도",
        'pitch_label': "목소리 톤 (높낮이)",
        'vol_label': "소리 크기 (볼륨)",
        'prefix_label': "파일 이름 설정 (예: 1a1)",
        'input_label': "텍스트 입력",
        'btn_label': "🔊 오디오 생성하기",
        'download_label': "MP3 다운로드",
        'err_empty': "텍스트를 입력해주세요!",
        'caption': "'Multilingual'이라고 적힌 목소리가 최신 모델입니다!"
    },
    'zh': {
        'title': "Readingtown 语音生成器 (完整版)",
        'sidebar_header': "设置 (Settings)",
        'lang_label': "界面语言",
        'voice_label': "选择语音",
        'speed_label': "语速",
        'pitch_label': "音调",
        'vol_label': "音量",
        'prefix_label': "文件名设置 (例如: 1a1)",
        'input_label': "输入文本",
        'btn_label': "🔊 生成音频",
        'download_label': "下载 MP3",
        'err_empty': "请输入文本！",
        'caption': "推荐尝试 'Multilingual' 多语言语音！"
    }
}

# --- 4. 비동기 헬퍼 ---
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# --- 5. 목소리 목록 ---
@st.cache_data
def get_voices():
    voices = run_async(edge_tts.list_voices())
    
    premium_list = []
    multilingual_list = []
    standard_list = []
    voice_map = {}
    
    expressive_ids = ["en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural", "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"]
    multilingual_ids = ["en-US-AndrewMultilingualNeural", "en-US-AvaMultilingualNeural", "en-US-BrianMultilingualNeural", "en-US-EmmaMultilingualNeural"]

    for v in voices:
        short_name = v['ShortName']
        if "Neural" not in short_name: continue
        
        if "ko-KR" in short_name: flag, tag = "🇰🇷", "[KR]"
        elif "en-US" in short_name: flag, tag = "🇺🇸", "[US]"
        elif "en-GB" in short_name: flag, tag = "🇬🇧", "[UK]"
        elif "en-AU" in short_name: flag, tag = "🇦🇺", "[AU]"
        elif "zh-CN" in short_name: flag, tag = "🇨🇳", "[CN]"
        elif "zh-TW" in short_name: flag, tag = "🇹🇼", "[TW]"
        else: continue

        gender = "Female" if v['Gender'] == "Female" else "Male"
        clean_name = short_name.split('-')[-1].replace('Neural', '').replace('Multilingual', '')
        
        if short_name in expressive_ids:
            display_name = f"🌟 [Premium] {flag} {clean_name} ({gender})"
            voice_map[display_name] = short_name
            premium_list.append(display_name)
        elif short_name in multilingual_ids or "Multilingual" in short_name:
            display_name = f"🚀 [New] {flag} {clean_name} ({gender})"
            voice_map[display_name] = short_name
            multilingual_list.append(display_name)
        else:
            display_name = f"{flag} {tag} {clean_name} ({gender})"
            voice_map[display_name] = short_name
            standard_list.append(display_name)
            
    premium_list.sort()
    multilingual_list.sort()
    standard_list.sort()
    return premium_list + multilingual_list + standard_list, voice_map

# --- 6. 파일명 정리 ---
def sanitize_filename(text):
    clean = re.sub(r'[\\/*?:"<>|]', "", text)
    clean = " ".join(clean.split())
    return clean[:15].strip()

# --- 7. 메인 앱 ---
def main():
    with st.sidebar:
        app_lang_sel = st.selectbox("Language / 언어 / 语言", ["English", "한국어", "中文"])
        if app_lang_sel == "English": lang_code = 'en'
        elif app_lang_sel == "한국어": lang_code = 'ko'
        else: lang_code = 'zh'
        
        t = txt[lang_code]
        st.header(t['sidebar_header'])
        
        voice_list, voice_map = get_voices()
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
    
    col1, col2 = st.columns([1, 3])
    with col1:
        file_prefix = st.text_input(t['prefix_label'], value="1a1")
    
    text_input = st.text_area(t['input_label'], height=150, placeholder="Try the new Multilingual voices!")

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
                    text_input, selected_id, rate=rate_str, pitch=pitch_str, volume=volume_str
                )
                out_buffer = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        out_buffer.write(chunk["data"])
                return out_buffer

            try:
                # 1. 오디오 생성
                audio_buffer = run_async(gen())
                
                # 2. 파일명 생성 (여기서 에러가 났었음 -> 수정완료)
                snippet = sanitize_filename(text_input)
                
                if file_prefix not in st.session_state.file_counters:
                    st.session_state.file_counters[file_prefix] = 1
                else:
                    st.session_state.file_counters[file_prefix] += 1
                
                count_num = st.session_state.file_counters[file_prefix]
                final_filename = f"[{file_prefix}] ({count_num}) {snippet}.mp3"
                
                # 3. 결과 출력
                st.audio(audio_buffer)
                
                st.download_button(
                    label=f"💾 {t['download_label']} : {final_filename}", 
                    data=audio_buffer,
                    file_name=final_filename,
                    mime="audio/mp3",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
