import streamlit as st
from google import genai
from google.genai import types
import urllib.parse
from PIL import Image, ImageOps
import time

st.set_page_config(
    page_title="수행평가 대비 프로그램",
    layout="centered",
    page_icon="📝"
)

# ==========================================
# 🎨 연파랑 및 무채색 UI 커스텀 디자인 적용 & 버전 표시 추가 (우측 하단 고정 - v 1.4)
# ==========================================
st.markdown("""
<style>
    .stApp {
        background-color: #F7F9FC;
        color: #2C3E50;
    }

    [data-testid="stSidebar"] {
        background-color: #EDF2F7;
    }

    .stButton > button {
        background-color: #E2E8F0;
        color: #2D3748;
        border: 1px solid #CBD5E0;
        border-radius: 6px;
        font-weight: 600;
    }

    .stButton > button:hover {
        background-color: #CBD5E0;
        color: #1A202C;
    }

    .stButton > button[kind="primary"] {
        background-color: #3182CE;
        color: white;
        border: none;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #2B6CB0;
    }
    
    /* 우측 하단 버전 표시 고정 스타일 */
    .version-label {
        position: fixed;
        bottom: 10px;
        right: 15px;
        color: #A0AEC0;
        font-size: 14px;
        font-weight: bold;
        z-index: 9999;
        background-color: rgba(255, 255, 255, 0.8);
        padding: 4px 8px;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
<div class="version-label">v 1.4</div>
""", unsafe_allow_html=True)


# ==========================================
# 세션 상태 초기화
# ==========================================
if 'qna_mode' not in st.session_state:
    st.session_state['qna_mode'] = False

if 'material_mode' not in st.session_state:
    st.session_state['material_mode'] = False

if 'saved_api_key' not in st.session_state:
    st.session_state['saved_api_key'] = ""


# ==========================================
# 🛠️ 이미지 크기 최적화 및 회전 버그 해결
# ==========================================
def process_image(img):
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    img_copy = img.copy()
    
    if img_copy.mode in ("RGBA", "P"):
        img_copy = img_copy.convert("RGB")
        
    img_copy.thumbnail((500, 500), Image.Resampling.LANCZOS)
    return img_copy


# ==========================================
# 🛠️ Gemini 오류 처리 및 스마트 재시도 함수 
# ==========================================
def generate_content_with_retry(
    client,
    model_name='gemini-3.6-flash',
    contents=None,
    config=None,
    max_retries=3
):
    if config is None:
        config = types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.7
        )

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            return response

        except Exception as e:
            error_msg = str(e)
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "rate limit" in error_msg.lower():
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 4  
                    st.warning(f"⏳ 순간 요청 한도 초과. 과부하 방지를 위해 {wait_time}초 후 재시도합니다... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    st.error("🚨 API 과부하 상태입니다. 잠시 후 다시 시도해 주세요.")
                    return None
            elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
                st.error("🚨 일일 API 할당량이 소진되었습니다.")
                return None
            else:
                st.error(f"⚠️ API 호출 중 오류가 발생했습니다: {error_msg}")
                return None

    return None


# ==========================================
# ❓ 질문하기 전용 화면 (Q&A 모드)
# ==========================================
if st.session_state['qna_mode']:

    st.title("❓ 무엇이든 질문하세요")

    if st.button("⬅️ 메인 화면으로 돌아가기"):
        st.session_state['qna_mode'] = False
        st.rerun()

    st.info("수행평가 내용, 암기 안 되는 부분, 기타 궁금한 점을 자유롭게 질문해 보세요.")

    user_question = st.text_area(
        "질문 입력",
        height=150,
        placeholder="예: 생명과학 DNA 복제 과정이 너무 헷갈리는데, 쉽게 비유해서 설명해줄 수 있어?"
    )

    if st.button("답변 받기", type="primary"):
        api_key = st.session_state.get('saved_api_key', '')

        if api_key and user_question.strip():
            client = genai.Client(api_key=api_key)

            with st.spinner("답변을 작성하고 있습니다..."):
                try:
                    res_qna = generate_content_with_retry(
                        client,
                        'gemini-3.6-flash',
                        user_question
                    )

                    if res_qna is not None:
                        st.success("답변이 도착했습니다!")
                        st.markdown("### 💡 AI 답변")
                        st.write(res_qna.text)

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("질문을 입력하지 않았거나 API 키가 없습니다.")
    
    st.stop()


# ==========================================
# 📄 복합양식 학습 자료 제작실 (다운로드 전용 고품질 HTML 교재 생성)
# ==========================================
if st.session_state['material_mode']:

    st.title("📑 복합양식 학습 자료 제작실")

    if st.button("⬅️ 메인 화면으로 돌아가기"):
        st.session_state['material_mode'] = False
        st.rerun()

    st.info("💡 이곳은 화면에 글을 띄우는 곳이 아닙니다! 핵심 개념과 이미지가 조화롭게 들어간 **복합양식 학습 자료(HTML 파일)**를 생성하여 다운로드하는 공간입니다.")

    mat_img_file = st.file_uploader(
        "🖼️ 참고 사진/자료 업로드 (선택 사항)",
        type=["jpg", "jpeg", "png"],
        key="mat_img"
    )

    mat_img = None

    if mat_img_file is not None:
        raw_img = Image.open(mat_img_file)
        mat_img = process_image(raw_img)

        st.image(
            mat_img,
            caption="업로드된 사진 (최적화 완료)",
            use_container_width=True
        )

    mat_topic = st.text_area(
        "1. 교재로 만들 핵심 주제나 원본 텍스트",
        height=120,
        placeholder="예: 교과서 본문이나 참고할 지문을 붙여넣으세요."
    )

    mat_request = st.text_area(
        "2. 추가 요청사항 (선택 사항)",
        height=120,
        placeholder="예: 깔끔한 디자인의 표나 시각 자료 배치를 강조해줘."
    )

    if st.button("✨ 복합양식 학습 자료 파일 생성하기", type="primary", use_container_width=True):
        api_key = st.session_state.get('saved_api_key', '')

        if api_key and (mat_topic.strip() or mat_img is not None):
            client = genai.Client(api_key=api_key)
            st.session_state.pop('generated_html_material', None)

            with st.spinner("시각 자료와 개념이 담긴 고품질 학습 자료 파일을 빌드하고 있습니다..."):
                try:
                    contents_mat = []

                    if mat_img is not None:
                        contents_mat.append(mat_img)

                    # 🚨 다운로드용 순수 HTML 구조물 생성을 위한 강력한 프롬프트 (중간 끊김 방지 및 핵심 완성)
                    prompt_complex = """
당신은 최고의 웹 교재 및 복합양식 학습 자료 디자이너입니다.
제공된 자료와 주제를 바탕으로 사용자가 다운로드하여 웹브라우저로 열어볼 수 있는 '완벽한 단독 실행형 HTML 문서 코드'를 처음부터 끝까지 완성도 있게 작성하세요.

[🚨 절대 엄수 규칙]
1. 결과물은 반드시 완벽한 HTML 코드(`<!DOCTYPE html>...</html>`) 전체만 출력하세요. 중간에 코드가 잘리거나 생략되면 절대 안 됩니다. 마크다운 백틱(```html ... ```)이나 설명 글을 절대 붙이지 말고, 순수 HTML 문자열만 처음부터 끝까지 출력하세요.
2. 내부 CSS 스타일을 포함하여 모바일과 PC 모두에서 예쁘고 깔끔하게 보이도록 디자인하세요.
3. 내용 중간중간에 주제와 관련된 시각 자료가 풍부하도록 위키미디어(Wikimedia Commons) 등 검증된 안정적인 공개 이미지 URL을 포함한 `<img>` 태그를 적절히 삽입해 주세요.
4. 수행평가 팁이나 불필요한 잡소리는 빼고, 오직 고품질의 순수 학습 개념 내용과 표, 목록, 이미지로만 문서를 채우세요.
"""
                    if mat_topic.strip():
                        prompt_complex += f"\n[주제/내용]: {mat_topic}"

                    if mat_request.strip():
                        prompt_complex += f"\n[요청사항]: {mat_request}"

                    contents_mat.append(prompt_complex)

                    config_mat = types.GenerateContentConfig(
                        max_output_tokens=8192,
                        temperature=0.7
                    )

                    res_mat = generate_content_with_retry(
                        client,
                        'gemini-3.6-flash',
                        contents_mat,
                        config=config_mat
                    )

                    if res_mat is not None:
                        html_output = res_mat.text.strip()
                        # 혹시라도 마크다운 코드블록 백틱이 포함되어 있다면 깔끔하게 제거
                        if html_output.startswith("```html"):
                            html_output = html_output[7:]
                        if html_output.startswith("```"):
                            html_output = html_output[3:]
                        if html_output.endswith("```"):
                            html_output = html_output[:-3]

                        st.session_state['generated_html_material'] = html_output.strip()
                        st.success("🎉 복합양식 학습 자료 파일이 성공적으로 준비되었습니다!")

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

        else:
            st.warning("주제(내용)를 입력하거나 참고 사진을 첨부해 주세요 (API 키 확인 필수).")

    if 'generated_html_material' in st.session_state:
        st.divider()
        st.success("📥 아래 버튼을 눌러 학습 자료 파일을 다운로드하세요! (다운로드한 파일을 더블클릭하면 이미지가 포함된 완벽한 학습 교재를 볼 수 있습니다)")
        
        html_data = st.session_state['generated_html_material']

        st.download_button(
            label="💾 복합양식 학습 자료 다운로드 (.html)",
            data=html_data.encode('utf-8'),
            file_name="study_material.html",
            mime="text/html",
            use_container_width=True
        )

    st.stop()


# ==========================================
# 📝 메인 화면 시작 (일반 수행평가 준비 & 암기 연습)
# ==========================================
st.title("📝 수행평가 대비 프로그램")

uploaded_img = None
memo_text = ""

api_key = st.sidebar.text_input("🔑 Gemini API 키를 입력하세요", type="password")

if api_key:
    st.session_state['saved_api_key'] = api_key
    client = genai.Client(api_key=api_key)

    mode = st.radio(
        "📌 기능을 선택하세요",
        ["일반 수행평가 준비", "암기 시험 연습"],
        horizontal=True
    )

    st.divider()

    # ==========================================
    # 1. 일반 수행평가 준비 모드
    # ==========================================
    if mode == "일반 수행평가 준비":
        st.subheader("📄 참고 자료 및 안내지 입력")

        uploaded_file = st.file_uploader(
            "참고자료 업로드 (.txt, .jpg, .png)",
            type=["txt", "jpg", "jpeg", "png"]
        )

        ref_text = ""
        ref_img = None

        if uploaded_file is not None:
            if uploaded_file.name.lower().endswith('.txt'):
                ref_text = uploaded_file.read().decode("utf-8")
                st.success("텍스트 파일을 성공적으로 불러왔습니다.")
            else:
                raw_img = Image.open(uploaded_file)
                ref_img = process_image(raw_img)
                st.success("사진 자료를 성공적으로 불러왔습니다.")
                st.image(ref_img, caption="업로드된 사진 (최적화 완료)", use_container_width=True)

        ref_text_input = st.text_area(
            "1. 참고 텍스트",
            value=ref_text,
            height=150,
            placeholder="예: 교과서 본문이나 참고할 지문을 붙여넣으세요. (선택 사항)"
        )

        guide_text = st.text_area(
            "2. 수행평가 안내지 입력",
            height=150,
            placeholder="예: 수행평가 주제, 평가 기준, 유의사항 등을 입력하세요. (사진으로 첨부한 경우 비워두셔도 됩니다.)"
        )

        col_m1, col_m2 = st.columns(2)

        with col_m1:
            if st.button("📝 맞춤형 실전 문제 생성", use_container_width=True, type="primary"):
                
                if guide_text.strip() or ref_text_input.strip() or ref_img is not None:
                    with st.spinner("과부하 방지를 위해 모든 자료를 통합 분석하고 있습니다..."):
                        try:
                            contents_base = []
                            if ref_img is not None:
                                contents_base.append(ref_img)

                            input_text = ""
                            if ref_text_input.strip():
                                input_text += f"[자료]: {ref_text_input}\n"
                            if guide_text.strip():
                                input_text += f"[안내지]: {guide_text}\n"

                            if input_text:
                                contents_base.append(input_text)

                            prompt_combined = """
위 내용을 바탕으로 4가지 항목을 작성해 주세요.
각 항목 사이에는 반드시 `===구분선===` 텍스트를 넣어 분리하세요.

1. 핵심 요약 자료 (간결하게)
===구분선===
2. 감점 예방 주의사항 및 고득점 팁
===구분선===
3. 실전 서술형/작문 문제 (정답 제외, 문제만 출력)
===구분선===
4. 추천 미디어 키워드
'유튜브 검색어: [키워드]
이미지 검색어: [키워드]'
형식으로 작성하세요.
"""
                            res_combined = generate_content_with_retry(
                                client,
                                'gemini-3.6-flash',
                                contents_base + [prompt_combined]
                            )

                            if res_combined is not None:
                                parts = [p.strip() for p in res_combined.text.split('===구분선===')]
                                st.session_state['study_material'] = parts[0] if len(parts) > 0 else "요약 자료를 불러오지 못했습니다."
                                st.session_state['result_tips'] = parts[1] if len(parts) > 1 else "팁 정보를 불러오지 못했습니다."
                                st.session_state['practice_question'] = parts[2] if len(parts) > 2 else "문제를 생성하지 못했습니다."
                                st.session_state['media_info'] = parts[3] if len(parts) > 3 else ""
                                
                                st.session_state['ref_text_input'] = ref_text_input
                                st.session_state['ref_img'] = ref_img
                                st.session_state['guide_text'] = guide_text
                                st.session_state['grading_result'] = None
                                st.session_state['current_mode'] = "일반"
                                
                                st.success("✅ 실전 문제 및 대비 자료가 성공적으로 생성되었습니다!")

                        except Exception as e:
                            st.error(f"오류가 발생했습니다: {e}")
                else:
                    st.warning("안내지 텍스트, 참고 텍스트, 또는 사진 자료 중 하나 이상을 입력해 주세요.")

        with col_m2:
            if st.button("📑 복합양식 학습 자료 제작실 가기", use_container_width=True):
                st.session_state['material_mode'] = True
                st.rerun()

    # ==========================================
    # 2. 암기 시험 연습 모드
    # ==========================================
    elif mode == "암기 시험 연습":
        st.subheader("🧠 암기 자료 첨부 및 세부 설정")

        subject = st.selectbox(
            "과목을 선택하세요",
            ["과학/수학 (공식 암기)", "영어 (지문 암기)", "역사 (단어 및 개념 암기)", "기타 일반 암기"]
        )

        eng_mode = None
        if subject == "영어 (지문 암기)":
            eng_mode = st.radio(
                "테스트 방식을 선택하세요",
                ["한글을 영어로 옮겨 적기 (영작)", "음성으로 말하기 테스트 (Speaking)"]
            )

        uploaded_img_file = st.file_uploader(
            "암기할 사진 업로드 (.jpg, .png)",
            type=["jpg", "jpeg", "png"]
        )

        uploaded_img = None
        if uploaded_img_file is not None:
            raw_img2 = Image.open(uploaded_img_file)
            uploaded_img = process_image(raw_img2)

        memo_text = st.text_area(
            "또는 텍스트 직접 입력",
            height=150,
            placeholder="외울 내용을 여기에 바로 적어도 됩니다."
        )

        if st.button("📝 암기 테스트 문제 출제", use_container_width=True, type="primary"):
            if uploaded_img is not None or memo_text.strip():
                with st.spinner("암기 테스트를 만드는 중입니다..."):
                    try:
                        contents = []
                        if subject == "과학/수학 (공식 암기)":
                            prompt_memo = "제공된 내용을 바탕으로 주관식 빈칸 3문제 출제. 정답 제외."
                        elif subject == "역사 (단어 및 개념 암기)":
                            prompt_memo = "제공된 내용을 바탕으로 개념 확인 3문제 출제. 정답 제외."
                        elif subject == "영어 (지문 암기)" and eng_mode == "한글을 영어로 옮겨 적기 (영작)":
                            prompt_memo = "영어 지문의 한글 해석을 제시하고 영작하는 문제 출제. 정답 제외."
                        elif subject == "영어 (지문 암기)" and eng_mode == "음성으로 말하기 테스트 (Speaking)":
                            prompt_memo = "지문의 핵심 개요 힌트를 주고, '아래 마이크 버튼을 눌러 영어로 말해보세요' 안내 문구 출력."
                        else:
                            prompt_memo = "제공된 내용에 대한 단답형 문제를 출제해 주세요. 정답 제외."

                        if uploaded_img is not None:
                            contents.append(uploaded_img)
                        if memo_text.strip():
                            contents.append(memo_text)
                            
                        contents.append(prompt_memo)

                        res_memo = generate_content_with_retry(
                            client,
                            'gemini-3.6-flash',
                            contents
                        )

                        if res_memo is not None:
                            st.session_state['memo_subject'] = subject
                            st.session_state['memo_eng_mode'] = eng_mode
                            st.session_state['memo_test_q'] = res_memo.text
                            st.session_state['current_mode'] = "암기"
                            st.session_state['memo_grading_result'] = None
                            st.success("✅ 암기 테스트 문제가 생성되었습니다.")

                    except Exception as e:
                        st.error(f"오류가 발생했습니다: {e}")
            else:
                st.warning("암기할 사진이나 텍스트를 입력해 주세요.")

    # ==========================================
    # 결과 출력부
    # ==========================================
    if (
        st.session_state.get('current_mode') == "일반"
        and mode == "일반 수행평가 준비"
        and 'practice_question' in st.session_state
    ):
        st.divider()
        st.subheader("결과 확인 탭")

        tab1, tab2, tab3, tab4 = st.tabs([
            "📚 요약 학습 자료", "✍️ 실전 문제 풀이", "💡 평가 팁 및 주의사항", "🎥 추천 미디어"
        ])

        with tab1:
            st.markdown(st.session_state.get('study_material', ''))

        with tab3:
            st.markdown(st.session_state.get('result_tips', ''))

        with tab4:
            media_text = st.session_state.get('media_info', '')
            st.write(media_text)
            st.write("---")
            st.write("📌 **바로가기 링크** (과부하 방지를 위해 직접 검색 링크를 제공합니다)")

            for line in [l.strip() for l in media_text.split('\n') if l.strip()]:
                if ":" in line:
                    title, keyword = line.split(":", 1)
                    keyword = keyword.strip()
                    if keyword:
                        yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(keyword)}"
                        img_url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(keyword)}"
                        st.markdown(f"- **{title} ({keyword})**: [유튜브 검색]({yt_url}) | [이미지 검색]({img_url})")

        with tab2:
            st.info(st.session_state.get('practice_question', ''))
            user_ans = st.text_area("내 답안 작성", height=220)

            if st.button("✨ AI 채점 및 예상 점수 받기"):
                if user_ans.strip():
                    with st.spinner("AI가 답안을 정밀 채점하고 있습니다..."):
                        try:
                            contents_grade = []
                            if st.session_state.get('ref_img') is not None:
                                contents_grade.append(st.session_state['ref_img'])

                            prompt_grade = f"""
[문제]:
{st.session_state.get('practice_question', '')}

[내 답안]:
{user_ans}

[조건]:
{st.session_state.get('guide_text', '')}

조건 충족 여부, 예상 점수, 감점 요인을 간결하게 채점해 주세요.
"""
                            contents_grade.append(prompt_grade)
                            res_grade = generate_content_with_retry(client, 'gemini-3.6-flash', contents_grade)

                            if res_grade is not None:
                                st.session_state['grading_result'] = res_grade.text
                        except Exception as e:
                            st.error(f"채점 중 오류가 발생했습니다: {e}")
                else:
                    st.warning("답안을 먼저 입력해 주세요.")

            if st.session_state.get('grading_result'):
                st.markdown("### 📊 AI 채점 결과")
                st.write(st.session_state['grading_result'])

    elif (
        st.session_state.get('current_mode') == "암기"
        and mode == "암기 시험 연습"
        and 'memo_test_q' in st.session_state
    ):
        st.divider()
        st.subheader("🧠 실전 암기 테스트")
        st.markdown(st.session_state['memo_test_q'])

        is_speaking_mode = (
            st.session_state.get('memo_subject') == "영어 (지문 암기)" and
            st.session_state.get('memo_eng_mode') == "음성으로 말하기 테스트 (Speaking)"
        )

        user_audio = None
        user_memo_ans = ""

        if is_speaking_mode:
            st.write("🎤 **암기한 지문을 아래 마이크 버튼을 눌러 음성으로 말해보세요:**")
            user_audio = st.audio_input("음성 녹음")
        else:
            user_memo_ans = st.text_area("문제에 대한 정답을 작성해 보세요", height=150)

        if st.button("📝 암기 답안 제출 및 채점하기"):
            if (is_speaking_mode and user_audio is not None) or (not is_speaking_mode and user_memo_ans.strip()):
                with st.spinner("채점 중입니다..."):
                    try:
                        contents = []
                        if is_speaking_mode:
                            audio_bytes = user_audio.read()
                            contents.append(
                                types.Part.from_bytes(
                                    data=audio_bytes,
                                    mime_type=user_audio.type or "audio/wav"
                                )
                            )
                            prompt_memo_grade = f"문제:\n{st.session_state['memo_test_q']}\n음성을 듣고 원본과 대조하여 간결히 채점해 주세요."
                        else:
                            prompt_memo_grade = f"문제:\n{st.session_state['memo_test_q']}\n답안:\n{user_memo_ans}\n원본 기준으로 간결히 채점해 주세요."

                        if uploaded_img is not None:
                            contents.append(uploaded_img)
                        if memo_text.strip():
                            contents.append(memo_text)
                            
                        contents.append(prompt_memo_grade)

                        res_memo_grade = generate_content_with_retry(
                            client,
                            'gemini-3.6-flash',
                            contents
                        )

                        if res_memo_grade is not None:
                            st.session_state['memo_grading_result'] = res_memo_grade.text
                    except Exception as e:
                        st.error(f"채점 중 오류가 발생했습니다: {e}")
            else:
                st.warning("답안을 먼저 입력하거나 녹음해 주세요.")

        if st.session_state.get('memo_grading_result'):
            st.markdown("### 📊 암기 테스트 채점 결과")
            st.write(st.session_state['memo_grading_result'])

    # ==========================================
    # 화면 하단 질문하기 버튼
    # ==========================================
    st.divider()
    col_space1, col_btn, col_space2 = st.columns([1, 2, 1])

    with col_btn:
        if st.button("💬 인공지능에게 질문하기", use_container_width=True):
            st.session_state['qna_mode'] = True
            st.rerun()

else:
    st.info("👈 왼쪽 사이드바에 Gemini API 키를 입력해 주세요.")

