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
# 🎨 연파랑 및 무채색 UI 커스텀 디자인 적용 & 버전 표시 추가 (우측 하단 고정 - v 1.6)
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
<div class="version-label">v 1.6</div>
""", unsafe_allow_html=True)


# ==========================================
# 세션 상태 초기화 및 API 키 설정 (Streamlit Secrets 연동)
# ==========================================
API_KEYS = st.secrets["GEMINI_API_KEYS"]

if 'api_key_index' not in st.session_state:
    st.session_state['api_key_index'] = 0

if 'qna_mode' not in st.session_state:
    st.session_state['qna_mode'] = False

if 'material_mode' not in st.session_state:
    st.session_state['material_mode'] = False

if 'text_report_mode' not in st.session_state:
    st.session_state['text_report_mode'] = False


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
# 🛠️ Gemini 오류 처리 및 스마트 재시도 함수 (API 자동 순환)
# ==========================================
def get_current_client():
    current_key = API_KEYS[st.session_state['api_key_index']]
    return genai.Client(api_key=current_key)

def generate_content_with_retry(
    model_name='gemini-3.6-flash',
    contents=None,
    config=None,
    max_retries=6
):
    if config is None:
        config = types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.7
        )

    for attempt in range(max_retries):
        client = get_current_client()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            return response

        except Exception as e:
            error_msg = str(e)
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "rate limit" in error_msg.lower() or "quota" in error_msg.lower() or "billing" in error_msg.lower():
                if attempt < max_retries - 1:
                    st.session_state['api_key_index'] = (st.session_state['api_key_index'] + 1) % len(API_KEYS)
                    st.warning(f"⏳ API 한도 초과 또는 할당량 소진. 다음 API 키로 전환하여 재시도합니다... ({attempt + 1}/{max_retries})")
                    time.sleep(1)
                else:
                    st.error("🚨 모든 API 키의 할당량이 소진되었거나 과부하 상태입니다. 잠시 후 다시 시도해 주세요.")
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

    st.info("수행평가 내용, 암기 안 되는 부분, 글쓰기 아이디어 등 궁금한 점을 자유롭게 질문해 보세요.")

    user_question = st.text_area(
        "질문 입력",
        height=150,
        placeholder="예: 생명과학 DNA 복제 과정이 너무 헷갈리는데, 쉽게 비유해서 설명해줄 수 있어?"
    )

    if st.button("답변 받기", type="primary"):
        if user_question.strip():
            with st.spinner("답변을 작성하고 있습니다..."):
                try:
                    res_qna = generate_content_with_retry(
                        model_name='gemini-3.6-flash',
                        contents=user_question
                    )

                    if res_qna is not None:
                        st.success("답변이 도착했습니다!")
                        st.markdown("### 💡 AI 답변")
                        st.write(res_qna.text)

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("질문을 입력하지 않았습니다.")
    
    st.stop()


# ==========================================
# 📄 텍스트 중심 A4 리포트 자료 제작실 (사진 업로드 및 연관성 강화 적용 - v1.6)
# ==========================================
if st.session_state['text_report_mode']:

    st.title("📄 A4 리포트(글/사진) 수행평가 자료 제작실")

    if st.button("⬅️ 메인 화면으로 돌아가기"):
        st.session_state['text_report_mode'] = False
        st.rerun()

    st.info("💡 업로드한 사진과 핵심 주제에 **100% 연관된 내용**으로 수행평가 제출용 또는 학습용 **A4 텍스트 리포트**를 생성합니다.")

    # 사진 업로드 기능 추가
    report_img_files = st.file_uploader(
        "🖼️ 참고할 사진/자료 업로드 (여러 장 선택 가능)",
        type=["jpg", "jpeg", "png"],
        key="report_imgs",
        accept_multiple_files=True
    )

    processed_report_imgs = []
    if report_img_files:
        for f in report_img_files:
            raw_img = Image.open(f)
            processed_report_imgs.append(process_image(raw_img))
        st.success(f"총 {len(processed_report_imgs)}장의 참고 사진이 최적화되었습니다.")

    report_topic = st.text_area(
        "1. 수행평가 주제 또는 세부 내용 입력",
        height=130,
        placeholder="예: 첨부한 자료를 바탕으로 한 생태계 파괴의 원인과 해결 방안 보고서 작성"
    )

    report_style = st.selectbox(
        "2. 문서 스타일 선택",
        ["수행평가 제출용 보고서 초안 (완성된 글)", "학습 개념 정리 노트 (핵심 요약)", "논설문 / 에세이 작성 가이드 및 예시"]
    )

    if st.button("✨ 수행평가 맞춤 A4 리포트 생성하기", type="primary", use_container_width=True):
        if report_topic.strip() or processed_report_imgs:
            st.session_state.pop('generated_text_report', None)

            with st.spinner("제공된 자료와 사진의 핵심 내용을 정밀 분석하여 A4 리포트를 작성하고 있습니다..."):
                try:
                    contents_report = list(processed_report_imgs)

                    prompt_report = f"""
당신은 최고의 수행평가 전문 지도 교사 및 작가입니다.
사용자가 제공한 [참고 사진]과 [주제/내용]을 철저히 분석하여, 무관한 내용은 절대 배제하고 **오직 입력된 자료와 주제에 100% 직결된 내용**으로만 A4 리포트 자료를 작성해주세요.

[문서 스타일]: {report_style}
[주제/내용]: {report_topic}

[엄격한 작성 규칙]
1. 첨부된 사진 속 텍스트나 핵심 개념을 빠짐없이 분석하여 리포트에 적극 반영하세요.
2. 마크다운 형식으로 제목(#, ##), 불렛 포인트(`-`), 강조(`**`)를 사용하여 가독성과 완성도를 극대화하세요.
3. 수행평가 제출용이나 완벽한 학습용으로 즉시 활용할 수 있도록 깊이 있고 정확한 내용으로 구성하세요. 불필요한 잡담이나 인사말은 절대 넣지 마세요.
"""
                    contents_report.append(prompt_report)

                    res_rep = generate_content_with_retry(
                        model_name='gemini-3.6-flash',
                        contents=contents_report
                    )

                    if res_rep is not None:
                        st.session_state['generated_text_report'] = res_rep.text.strip()
                        st.success("🎉 수행평가 맞춤 A4 리포트가 성공적으로 준비되었습니다!")

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("주제 또는 참고 사진을 하나 이상 입력/첨부해 주세요.")

    if 'generated_text_report' in st.session_state:
        st.divider()
        st.markdown("### 👁️ 미리보기")
        st.markdown(st.session_state['generated_text_report'])

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                label="💾 텍스트 파일로 다운로드 (.txt)",
                data=st.session_state['generated_text_report'].encode('utf-8'),
                file_name="study_report.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col_d2:
            st.download_button(
                label="💾 마크다운 파일로 다운로드 (.md)",
                data=st.session_state['generated_text_report'].encode('utf-8'),
                file_name="study_report.md",
                mime="text/markdown",
                use_container_width=True
            )

    st.stop()


# ==========================================
# 📑 복합양식 학습 자료 제작실 (HTML 다운로드)
# ==========================================
if st.session_state['material_mode']:

    st.title("📑 복합양식 학습 자료 제작실 (HTML)")

    if st.button("⬅️ 메인 화면으로 돌아가기"):
        st.session_state['material_mode'] = False
        st.rerun()

    st.info("💡 핵심 개념과 이미지가 조화롭게 들어간 **복합양식 학습 자료(HTML 파일)**를 생성하여 다운로드하는 공간입니다.")

    mat_img_files = st.file_uploader(
        "🖼️ 참고 사진/자료 업로드 (여러 장 선택 가능)",
        type=["jpg", "jpeg", "png"],
        key="mat_imgs",
        accept_multiple_files=True
    )

    processed_mat_imgs = []
    if mat_img_files:
        for f in mat_img_files:
            raw_img = Image.open(f)
            processed_mat_imgs.append(process_image(raw_img))
        st.success(f"총 {len(processed_mat_imgs)}개의 이미지가 업로드 및 최적화되었습니다.")

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
        if mat_topic.strip() or processed_mat_imgs:
            st.session_state.pop('generated_html_material', None)

            with st.spinner("시각 자료와 개념이 담긴 고품질 학습 자료 파일을 빌드하고 있습니다..."):
                try:
                    contents_mat = list(processed_mat_imgs)

                    prompt_complex = """
당신은 최고의 웹 교재 및 복합양식 학습 자료 디자이너입니다.
제공된 자료와 주제에 100% 부합하는 내용만을 바탕으로 사용자가 다운로드하여 웹브라우저로 열어볼 수 있는 '완벽한 단독 실행형 HTML 문서 코드'를 작성하세요.

[🚨 절대 엄수 규칙]
1. 결과물은 반드시 완벽한 HTML 코드(`<!DOCTYPE html>...</html>`) 전체만 출력하세요. 마크다운 백틱(```html ... ```)이나 설명 글을 절대 붙이지 마세요.
2. 내부 CSS 스타일을 포함하여 모바일과 PC 모두에서 예쁘고 깔끔하게 보이도록 디자인하세요.
3. 이미지 엑박 방지를 위해 제공된 주제와 밀접하게 연관된 구체적인 영어 키워드 이미지를 사용하세요:
형식: `<img src="https://image.pollinations.ai/prompt/구체적인_영어_키워드_설명?width=800&height=400&nologo=true" alt="설명" onerror="this.style.display='none'">`
"""
                    if mat_topic.strip():
                        prompt_complex += f"\n[주제/내용]: {mat_topic}"

                    if mat_request.strip():
                        prompt_complex += f"\n[요청사항]: {mat_request}"

                    contents_mat.append(prompt_complex)

                    res_mat = generate_content_with_retry(
                        model_name='gemini-3.6-flash',
                        contents=contents_mat
                    )

                    if res_mat is not None:
                        html_output = res_mat.text.strip()
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
            st.warning("주제(내용)를 입력하거나 참고 사진을 첨부해 주세요.")

    if 'generated_html_material' in st.session_state:
        st.divider()
        st.success("📥 아래 버튼을 눌러 학습 자료 파일을 다운로드하세요!")
        
        st.download_button(
            label="💾 복합양식 학습 자료 다운로드 (.html)",
            data=st.session_state['generated_html_material'].encode('utf-8'),
            file_name="study_material.html",
            mime="text/html",
            use_container_width=True
        )

    st.stop()


# ==========================================
# 📝 메인 화면 시작 (일반 수행평가 준비 & 암기 시험 연습)
# ==========================================
st.title("📝 수행평가 대비 프로그램")

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
    st.subheader("📄 다중 참고 자료 및 안내지 입력")

    uploaded_files = st.file_uploader(
        "참고자료 업로드 (텍스트 및 이미지 여러 장 선택 가능)",
        type=["txt", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    ref_texts_list = []
    ref_imgs_list = []

    if uploaded_files:
        for file in uploaded_files:
            if file.name.lower().endswith('.txt'):
                ref_texts_list.append(file.read().decode("utf-8"))
            else:
                raw_img = Image.open(file)
                ref_imgs_list.append(process_image(raw_img))
        st.success(f"총 텍스트 파일 {len(ref_texts_list)}개, 이미지 {len(ref_imgs_list)}장이 성공적으로 업로드되었습니다.")

    ref_text_input = st.text_area(
        "1. 추가 참고 텍스트",
        height=120,
        placeholder="교과서 본문이나 추가 참고 지문을 입력하세요. (선택 사항)"
    )

    guide_text = st.text_area(
        "2. 수행평가 안내지 입력 (글쓰기 주제, 평가 기준 등)",
        height=120,
        placeholder="예: 보고서 작성 수행평가. 주제에 맞는 글쓰기 초안 작성 도움 및 평가 기준 충족 여부 확인 요청"
    )

    # 자료 제작실 바로가기 버튼들 (상단 배치)
    col_mb1, col_mb2 = st.columns(2)
    with col_mb1:
        if st.button("📄 A4 리포트(글/사진) 자료 제작실", use_container_width=True):
            st.session_state['text_report_mode'] = True
            st.rerun()
    with col_mb2:
        if st.button("📑 복합양식(HTML) 자료 제작실", use_container_width=True):
            st.session_state['material_mode'] = True
            st.rerun()

    st.markdown("---")

    if st.button("📝 맞춤형 실전 문제 및 글쓰기 가이드 생성", use_container_width=True, type="primary"):
        if guide_text.strip() or ref_text_input.strip() or ref_texts_list or ref_imgs_list:
            with st.spinner("모든 자료를 철저히 분석하여 수행평가 맞춤 가이드 및 문제를 생성하고 있습니다..."):
                try:
                    contents_base = list(ref_imgs_list)

                    input_text = ""
                    if ref_texts_list:
                        for i, t in enumerate(ref_texts_list):
                            input_text += f"[참고 텍스트 파일 {i+1}]:\n{t}\n\n"
                    if ref_text_input.strip():
                        input_text += f"[추가 참고 텍스트]:\n{ref_text_input}\n\n"
                    if guide_text.strip():
                        input_text += f"[수행평가 안내지/요청]:\n{guide_text}\n"

                    if input_text:
                        contents_base.append(input_text)

                    prompt_combined = """
제공된 다중 참고 자료와 안내지의 핵심 내용에 100% 집중하여 다음 4가지 항목을 작성해 주세요. (무관한 내용 금지)
각 항목 사이에는 반드시 `===구분선===` 텍스트를 넣어 분리하세요.

1. 핵심 개념 정리 및 수행평가 맞춤 글쓰기/설명 가이드 (글쓰기 수행평가인 경우 직접 훌륭한 예시 글이나 작성 방향을 상세히 제시해주세요)
===구분선===
2. 감점 예방 주의사항 및 고득점 팁
===구분선===
3. 실전 서술형/작문 문제 (또는 핵심 객관식 문제 3문항 포함)
===구분선===
4. 추천 미디어 키워드
'유튜브 검색어: [키워드]
이미지 검색어: [키워드]'
형식으로 작성하세요.
"""
                    res_combined = generate_content_with_retry(
                        model_name='gemini-3.6-flash',
                        contents=contents_base + [prompt_combined]
                    )

                    if res_combined is not None:
                        parts = [p.strip() for p in res_combined.text.split('===구분선===')]
                        st.session_state['study_material'] = parts[0] if len(parts) > 0 else "요약 자료를 불러오지 못했습니다."
                        st.session_state['result_tips'] = parts[1] if len(parts) > 1 else "팁 정보를 불러오지 못했습니다."
                        st.session_state['practice_question'] = parts[2] if len(parts) > 2 else "문제를 생성하지 못했습니다."
                        st.session_state['media_info'] = parts[3] if len(parts) > 3 else ""
                        
                        st.session_state['ref_imgs_list'] = ref_imgs_list
                        st.session_state['guide_text'] = guide_text
                        st.session_state['grading_result'] = None
                        st.session_state['current_mode'] = "일반"
                        
                        st.success("✅ 수행평가 맞춤 자료 및 문제가 성공적으로 생성되었습니다!")

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("안내지 텍스트, 참고 텍스트, 또는 사진 자료 중 하나 이상을 입력해 주세요.")

# ==========================================
# 2. 암기 시험 연습 모드
# ==========================================
elif mode == "암기 시험 연습":
    st.subheader("🧠 다중 암기 자료 첨부 및 세부 설정")

    subject = st.selectbox(
        "과목을 선택하세요",
        ["과학/수학 (공식 및 개념)", "영어 (지문 암기)", "역사 (단어 및 개념)", "기타 일반 암기"]
    )

    test_type = st.radio(
        "출제 유형 선택",
        ["주관식 / 서술형", "객관식 (4지선다)"]
    )

    eng_mode = None
    if subject == "영어 (지문 암기)":
        eng_mode = st.radio(
            "영어 테스트 세부 방식",
            ["한글을 영어로 옮겨 적기 (영작)", "음성으로 말하기 테스트 (Speaking)"]
        )

    uploaded_img_files2 = st.file_uploader(
        "암기할 사진 업로드 (여러 장 선택 가능)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    processed_memo_imgs = []
    if uploaded_img_files2:
        for f in uploaded_img_files2:
            raw_img = Image.open(f)
            processed_memo_imgs.append(process_image(raw_img))

    memo_text = st.text_area(
        "또는 암기할 텍스트 직접 입력",
        height=130,
        placeholder="외울 내용을 여기에 적어주세요."
    )

    if st.button("📝 암기 테스트 문제 출제", use_container_width=True, type="primary"):
        if processed_memo_imgs or memo_text.strip():
            with st.spinner("암기 테스트를 만드는 중입니다..."):
                try:
                    contents = list(processed_memo_imgs)
                    if memo_text.strip():
                        contents.append(memo_text)

                    if test_type == "객관식 (4지선다)":
                        prompt_memo = "제공된 내용에만 100% 기반하여 핵심 객관식 4지선다 문제 3문항을 출제해 주세요. (정답과 해설은 숨기고 문제만 출제)"
                    else:
                        if subject == "영어 (지문 암기)" and eng_mode == "음성으로 말하기 테스트 (Speaking)":
                            prompt_memo = "제공된 지문에만 기반하여 암기 여부를 확인하는 스피킹 테스트를 진행합니다. 핵심 개요 힌트를 주고 음성으로 말해보도록 안내하세요."
                        else:
                            prompt_memo = "제공된 내용에만 100% 기반하여 핵심 암기 주관식/단답형 문제 3문항을 출제해 주세요. (정답 제외)"

                    contents.append(prompt_memo)

                    res_memo = generate_content_with_retry(
                        model_name='gemini-3.6-flash',
                        contents=contents
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
        "📚 요약 및 글쓰기 가이드", "✍️ 실전 문제 및 답안 작성", "💡 평가 팁 및 주의사항", "🎥 추천 미디어"
    ])

    with tab1:
        st.markdown(st.session_state.get('study_material', ''))

    with tab3:
        st.markdown(st.session_state.get('result_tips', ''))

    with tab4:
        media_text = st.session_state.get('media_info', '')
        st.write(media_text)
        st.write("---")
        st.write("📌 **바로가기 링크**")

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
        user_ans = st.text_area("내 답안 또는 글쓰기 결과물 작성", height=220)

        if st.button("✨ AI 정밀 채점 및 피드백 받기"):
            if user_ans.strip():
                with st.spinner("AI가 답안을 정밀 채점하고 피드백을 작성하고 있습니다..."):
                    try:
                        contents_grade = []
                        if st.session_state.get('ref_imgs_list'):
                            contents_grade.extend(st.session_state['ref_imgs_list'])

                        prompt_grade = f"""
[문제/과제]:
{st.session_state.get('practice_question', '')}

[제출한 답안/글]:
{user_ans}

[수행평가 조건/안내지]:
{st.session_state.get('guide_text', '')}

조건 충족 여부, 예상 점수, 구체적인 개선 피드백 및 감점 요인을 간결하게 채점해 주세요.
"""
                        contents_grade.append(prompt_grade)
                        res_grade = generate_content_with_retry(
                            model_name='gemini-3.6-flash',
                            contents=contents_grade
                        )

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
        user_memo_ans = st.text_area("문제에 대한 정답 (객관식 번호 또는 주관식 정답)을 작성해 보세요", height=150)

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
                        prompt_memo_grade = f"문제:\n{st.session_state['memo_test_q']}\n음성을 듣고 원본과 대조하여 정답 여부 및 해설을 간결히 채점해 주세요."
                    else:
                        prompt_memo_grade = f"문제:\n{st.session_state['memo_test_q']}\n제출한 답안:\n{user_memo_ans}\n원본 기준으로 정답 여부와 해설을 간결히 채점해 주세요."

                    contents.append(prompt_memo_grade)

                    res_memo_grade = generate_content_with_retry(
                        model_name='gemini-3.6-flash',
                        contents=contents
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
