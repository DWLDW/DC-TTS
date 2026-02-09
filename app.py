import streamlit as st
import edge_tts
import asyncio
import os
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="AI Neural Voice Generator", page_icon="🎙️")

# --- 다국어 사전 ---
txt = {
    'ko': {
        'title': "AI 신경망 음성 생성기 (Web)",
        'sidebar_title': "설정 (Settings)",
        'lang_sel': "프로그램 언어",
        'voice_lbl': "목소리 선택",
        'speed_lbl': "말하기 속도",
        'pitch_lbl': "목소리 톤",
        'input_lbl': "텍스트 입력",
        'btn_gen': "🔊 오디오 생성하기",
        'success': "생성 완료! 아래에서 들어보거나 다운로드하세요.",
        'err_empty': "텍스트를 입력해주세요!",
        'download': "MP3 다운로드"
    },
    'en': {
        'title': "AI Neural Voice Generator (Web)",
        'sidebar_title': "Settings",
        'lang_sel': "App Language",
        'voice_lbl': "Select Voice",
        'speed_lbl': "Speech Rate",
        'pitch_lbl': "Voice Pitch",
        'input_lbl': "Enter Text",
        'btn_gen': "🔊 Generate Audio",
        'success': "Done! Listen or download below.",
        'err_empty': "Please enter text!",
        'download': "Download MP3"
    },
    'zh': {
        'title': "AI 神经网络语音生成器 (Web)",
        'sidebar_title': "设置 (Settings)",
        'lang_sel': "程序语言",
        'voice_lbl': "选择语音",
        'speed_lbl': "语速",
        'pitch_lbl': "音调",
        'input_lbl': "输入文本",
        'btn_gen': "🔊 生成音频",
        'success': "完成！请在下方收听或下载。",
        'err_empty': "请输入文本！",
        'download': "下载 MP3"
    }
}

# --- 비동기 함수 (목소리 로딩) ---
@st.cache_data # 데이터를 캐싱해서 속도 향상
def get_voices():
    # 비동기 루프 실행
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    voices = loop.run_until_complete(edge_tts.list_voices())
    loop.close()
    
    voice_list = []
    voice_map = {}
    
    for v in voices:
        short_name = v['ShortName']
        # 필터링 (한/영/중 + Neural)
        if "Neural" not in short_name: continue
        if not any(lang in short_name for lang in ["ko-KR", "en-US", "en-GB", "zh-CN", "zh-TW"]): continue

        # 국기 및 태그
        if "ko-KR" in short_name: flag, tag = "🇰🇷", "[KR]"
        elif "en-US" in short_name: flag, tag = "🇺🇸", "[US]"
        elif "en-GB" in short_name: flag, tag = "🇬🇧", "[UK]"
        elif "zh-CN" in short_name: flag, tag = "🇨🇳", "[CN]"
        elif "zh-TW" in short_name: flag, tag = "🇹🇼", "[TW]"
        else: continue

        gender = "여" if v['Gender'] == "Female" else "남"
        clean_name = short_name.split('-')[-1].replace('Neural', '')
        
        display_name = f"{flag} {tag} {clean_name} ({gender}) ⚡"
        voice_list.append(display_name)
        voice_map[display_name] = short_name
        
    voice_list.sort()
    return voice_list, voice_map

# --- 비동기 함수 (오디오 생성) ---
async def generate_audio_async(text, voice, rate, pitch, filename):
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(filename)

# --- 메인 앱 로직 ---
def main():
    # 1. 사이드바: 언어 설정
    with st.sidebar:
        app_lang = st.selectbox("Language / 言語 / 语言", ["한국어", "English", "中文"])
        
        if app_lang == "한국어": lang_code = 'ko'
        elif app_lang == "English": lang_code = 'en'
        else: lang_code = 'zh'
        
        t = txt[lang_code] # 현재 언어 팩 선택
        
        st.header(t['sidebar_title'])
        
        # 목소리 목록 로딩
        voice_list, voice_map = get_voices()
        
        # 기본값 설정 (SunHi)
        default_idx = 0
        for i, v in enumerate(voice_list):
            if "SunHi" in v: default_idx = i; break
            
        selected_voice_display = st.selectbox(t['voice_lbl'], voice_list, index=default_idx)
        selected_voice_id = voice_map[selected_voice_display]
        
        # 속도 & 톤
        speed = st.slider(t['speed_lbl'], -50, 50, 0, format="%d%%")
        pitch = st.slider(t['pitch_lbl'], -50, 50, 0, format="%dHz")
        
        rate_str = f"{'+' if speed >= 0 else ''}{speed}%"
        pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"

    # 2. 메인 화면
    st.title(t['title'])
    
    text_input = st.text_area(t['input_lbl'], height=200, placeholder="Hello! How are you?")

    if st.button(t['btn_gen'], type="primary"):
        if not text_input.strip():
            st.error(t['err_empty'])
        else:
            with st.spinner("Processing..."):
                # 파일명 생성
                timestamp = datetime.now().strftime("%H%M%S")
                filename = f"audio_{timestamp}.mp3"
                
                # 비동기 실행을 동기식으로 처리
                asyncio.run(generate_audio_async(text_input, selected_voice_id, rate_str, pitch_str, filename))
                
                # 결과 표시
                st.success(t['success'])
                
                # 1. 바로 듣기 플레이어
                st.audio(filename)
                
                # 2. 다운로드 버튼
                with open(filename, "rb") as file:
                    st.download_button(
                        label=t['download'],
                        data=file,
                        file_name=filename,
                        mime="audio/mp3"
                    )
                
                # (옵션) 임시 파일 삭제는 Streamlit 특성상 복잡할 수 있어 생략하거나
                # os.remove(filename)을 다운로드 버튼 클릭 후 처리해야 함.

if __name__ == "__main__":
    main()