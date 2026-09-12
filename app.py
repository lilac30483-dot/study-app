import streamlit as st
from google import genai
from google.genai import types
import urllib.parse
from PIL import Image
import time
import re

st.set_page_config(
    page_title="수행평가 대비 프로그램",
    layout="centered",
    page_icon="📝"
)

# ==========================================
# 🎨 연파랑 및 무채색 UI 커스텀 디자인 적용
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
</style>
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
# 🛠️ 이미지 크기 최적화 (요청량/토큰 최소화)
# ==========================================
def process_image(img):
    img_copy = img.copy()
    # 해상도를 500x500으로 더 줄여서 API 요청 데이터 크기를 대폭 감소시킵니다.
    img_copy.thumbnail((500, 500), Image.Resampling.LANCZOS)
    return img_copy


# ==========================================
# 🛠️ Gemini 오류 처리 및 재시도 함수 (불필요한 대기 제거)
# ==========================================
def generate_content_with_retry(
    client,
    model_name,
    contents,
    config=None,
    max_retries=2  # 재시도 횟수 대폭 축소
):
    for attempt in range(max_retries):
        try:
            if config:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
            else:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
            return response

        except Exception as e:
            error_msg = str(e)
            
            # 1. 일일 할당량 완전 소진(Quota Exceeded)인 경우 -> 기다려도 해결 안 되므로 즉시 중단
            if "quota" in error_msg.lower() or "billing" in error_msg.lower():
                st.error(
                    "🚨 API 일일 무료 사용량을 모두 소진했습니다.\n\n"
                    "대기해도 해결되지 않으므로, 내일 다시 시도하거나 구글 클라우드에서 새로운 API 키를 발급받아 주세요."
                )
                return None

            # 2. 단순 일시적 과부하(429)인 경우 -> 짧게만 대기
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = 5  # 5초만 대기
                    st.warning(f"⏳ 일시적인 요청 지연입니다. {wait_time}초 후 다시 시도합니다... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    st.error("🚨 API 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.")
                    return None
            else:
                # 다른 종류의 오류는 그대로 출력
                raise e

    return None


# ==========================================
# ❓ 질문하기 전용 화면 (Q&A 모드)
# ==========================================
if st.session_state['qna_mode']:

    st.title("❓ 무엇이든 질문하세요")

    if st.button("⬅️ 메인 화면으로 돌아가기"):
        st.session_state['qna_mode'] = False
        st.rerun()

    st.info(
        "수행평가 내용, 암기 안 되는 부분, 기타 궁금한 점을 "
        "인공지능에게 자유롭게 질문해 보세요. "
        "(🌐 인터넷 실시간 검색이 지원됩니다)"
    )

    user_question = st.text_area(
        "질문 입력",
        height=150,
        placeholder="예: 생명과학 DNA 복제 과정이 너무 헷갈리는데, 쉽게 비유해서 설명해줄 수 있어?"
    )

    if st.button("답변 받기", type="primary"):

        api_key = st.session_state.get('saved_api_key', '')

        if api_key and user_question.strip():

            client = genai.Client(api_key=api_key)

            with st.spinner(
                "인터넷을 검색하며 답변을 작성하고 있습니다..."
            ):

                try:

                    config_qna = types.GenerateContentConfig(
                        tools=[{"google_search": {}}]
                    )

                    res_qna = generate_content_with_retry(
                        client,
                        'gemini-3.5-flash',
                        user_question,
                        config=config_qna
                    )

                    # 429 최종 실패 시 None 처리
                    if res_qna is not None:

                        st.success("답변이 도착했습니다!")

                        st.markdown("### 💡 AI 답변")

                        st.write(res_qna.text)

                except Exception as e:

                    st.error(f"오류가 발생했습니다: {e}")

        else:

            st.warning(
                "질문을 입력하지 않았거나 API 키가 없습니다."
            )

    st.stop()


# ==========================================
# 📄 복합 양식 학습 자료 제작 전용 화면
# ==========================================
if st.session_state['material_mode']:

    st.title("📑 고퀄리티 복합 양식 교재 제작실")

    if st.button("⬅️ 메인 화면으로 돌아가기"):

        st.session_state['material_mode'] = False

        st.rerun()

    st.info(
        "글자와 인터넷 실제 사진/도표가 어우러진 "
        "진정한 복합 양식 학습 노트를 제작합니다."
    )

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
        placeholder="예: 고등학교 통합과학 - 빅뱅 우주론과 기본 입자의 생성"
    )

    mat_request = st.text_area(
        "2. 추가 요청사항 (선택 사항)",
        height=120,
        placeholder="예: 원소 생성 과정을 시간 순서대로 표로 정리하고, 이해를 돕기 위한 우주 배경 복사 사진을 본문에 넣어줘."
    )

    if st.button(
        "✨ 복합 양식 학습 자료 생성하기 (인터넷 사진+텍스트)",
        type="primary",
        use_container_width=True
    ):

        api_key = st.session_state.get(
            'saved_api_key',
            ''
        )

        if api_key and (
            mat_topic.strip()
            or mat_img is not None
        ):

            client = genai.Client(
                api_key=api_key
            )

            st.session_state.pop(
                'generated_complex_material',
                None
            )

            with st.spinner(
                "자료를 분석하고 교재를 작성 중입니다..."
            ):

                try:

                    contents_mat = []

                    if mat_img is not None:

                        contents_mat.append(
                            mat_img
                        )

                    prompt_complex = """
당신은 교재 제작 전문가입니다.
제공된 자료로 '고품질 복합 양식 학습 자료'를 만드세요.

[규칙]

1. 구글 검색을 통해 주제와 연관된 실제 인터넷 이미지 URL을 1~2개 찾아
`![설명](URL)` 형식으로 글 사이에 삽입하세요.

2. 특수문자 선 긋기(ASCII Art) 금지.

3. 내용 시각화는 마크다운 표와 글머리 기호만 사용하세요.
"""

                    if mat_topic.strip():

                        prompt_complex += (
                            f"\n[내용]: {mat_topic}"
                        )

                    if mat_request.strip():

                        prompt_complex += (
                            f"\n[요청사항]: {mat_request}"
                        )

                    contents_mat.append(
                        prompt_complex
                    )

                    config_mat = (
                        types.GenerateContentConfig(
                            tools=[
                                {
                                    "google_search": {}
                                }
                            ]
                        )
                    )

                    res_mat = (
                        generate_content_with_retry(
                            client,
                            'gemini-3.5-flash',
                            contents_mat,
                            config=config_mat
                        )
                    )

                    # 429 오류로 최종 실패한 경우
                    if res_mat is not None:

                        st.session_state[
                            'generated_complex_material'
                        ] = res_mat.text

                        st.success(
                            "고퀄리티 복합 양식 학습 자료가 성공적으로 생성되었습니다!"
                        )

                except Exception as e:

                    st.error(
                        f"오류가 발생했습니다: {e}"
                    )

        else:

            st.warning(
                "주제(내용)를 입력하거나 참고 사진을 첨부해 주세요 "
                "(API 키 확인 필수)."
            )

    if (
        'generated_complex_material'
        in st.session_state
    ):

        st.divider()

        st.markdown(
            "### 📄 완성된 복합 양식 학습 노트"
        )

        st.markdown(
            st.session_state[
                'generated_complex_material'
            ]
        )

        st.download_button(
            label="💾 자료 파일 다운로드 (.txt)",
            data=st.session_state[
                'generated_complex_material'
            ].encode('utf-8-sig'),
            file_name="complex_study_material.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.stop()


# ==========================================
# 📝 메인 화면 시작
# ==========================================
st.title("📝 수행평가 대비 프로그램")

uploaded_img = None
memo_text = ""

api_key = st.sidebar.text_input(
    "🔑 Gemini API 키를 입력하세요",
    type="password"
)


if api_key:

    st.session_state[
        'saved_api_key'
    ] = api_key

    client = genai.Client(
        api_key=api_key
    )

    mode = st.radio(
        "📌 기능을 선택하세요",
        [
            "일반 수행평가 준비",
            "암기 시험 연습"
        ],
        horizontal=True
    )

    st.divider()


    # ==========================================
    # 1. 일반 수행평가 준비 모드
    # ==========================================
    if mode == "일반 수행평가 준비":

        st.subheader(
            "📄 참고 자료 및 안내지 입력"
        )

        uploaded_file = st.file_uploader(
            "참고자료 업로드 (.txt, .jpg, .png)",
            type=[
                "txt",
                "jpg",
                "jpeg",
                "png"
            ]
        )

        ref_text = ""
        ref_img = None


        if uploaded_file is not None:

            if (
                uploaded_file.name
                .lower()
                .endswith('.txt')
            ):

                ref_text = (
                    uploaded_file
                    .read()
                    .decode("utf-8")
                )

                st.success(
                    "텍스트 파일을 성공적으로 불러왔습니다."
                )

            else:

                raw_img = Image.open(
                    uploaded_file
                )

                ref_img = process_image(
                    raw_img
                )

                st.success(
                    "사진 자료를 성공적으로 불러왔습니다."
                )

                st.image(
                    ref_img,
                    caption="업로드된 사진 (최적화 완료)",
                    use_container_width=True
                )


        ref_text_input = st.text_area(
            "1. 참고 텍스트",
            value=ref_text,
            height=150,
            placeholder="교과서 본문이나 참고할 지문을 붙여넣으세요."
        )


        guide_text = st.text_area(
            "2. 수행평가 안내지 입력 (필수)",
            height=150,
            placeholder=
            "예: '주제: 환경 오염의 해결 방안', 조건: "
            "원인과 결과를 포함하여 500자 내외로 논술할 것."
        )


        col_m1, col_m2 = st.columns(2)


        # ------------------------------------------
        # 실전 문제 생성
        # ------------------------------------------
        with col_m1:

            if st.button(
                "📝 맞춤형 실전 문제 생성",
                use_container_width=True,
                type="primary"
            ):

                if (
                    guide_text.strip()
                    and (
                        ref_text_input.strip()
                        or ref_img is not None
                    )
                ):

                    with st.spinner(
                        "과부하 방지를 위해 모든 자료를 통합 분석하고 있습니다..."
                    ):

                        try:

                            contents_base = []

                            if ref_img is not None:

                                contents_base.append(
                                    ref_img
                                )

                            contents_base.append(
                                f"[자료]: {ref_text_input}\n"
                                f"[안내지]: {guide_text}"
                            )


                            prompt_combined = """
위 안내지와 자료를 분석하여
4가지 항목을 작성해 주세요.

각 항목 사이에는 반드시
`===구분선===`
텍스트를 넣어 분리하세요.

1. 핵심 요약 자료 (간결하게)

===구분선===

2. 감점 예방 주의사항 및 고득점 팁

===구분선===

3. 실전 서술형/작문 문제
(정답 제외, 문제만 출력)

===구분선===

4. 추천 미디어 키워드

'유튜브 검색어: [키워드]
이미지 검색어: [키워드]'

형식으로 작성하세요.
"""


                            res_combined = (
                                generate_content_with_retry(
                                    client,
                                    'gemini-3.5-flash',
                                    contents_base + [
                                        prompt_combined
                                    ]
                                )
                            )


                            # 429 최종 실패 시
                            if res_combined is not None:

                                parts = [
                                    p.strip()
                                    for p in
                                    res_combined.text.split(
                                        '===구분선==='
                                    )
                                ]


                                st.session_state[
                                    'study_material'
                                ] = (
                                    parts[0]
                                    if len(parts) > 0
                                    else "요약 자료를 불러오지 못했습니다."
                                )


                                st.session_state[
                                    'result_tips'
                                ] = (
                                    parts[1]
                                    if len(parts) > 1
                                    else "팁 정보를 불러오지 못했습니다."
                                )


                                st.session_state[
                                    'practice_question'
                                ] = (
                                    parts[2]
                                    if len(parts) > 2
                                    else "문제를 생성하지 못했습니다."
                                )


                                st.session_state[
                                    'media_info'
                                ] = (
                                    parts[3]
                                    if len(parts) > 3
                                    else ""
                                )


                                st.session_state[
                                    'ref_text_input'
                                ] = ref_text_input


                                st.session_state[
                                    'ref_img'
                                ] = ref_img


                                st.session_state[
                                    'guide_text'
                                ] = guide_text


                                st.session_state[
                                    'grading_result'
                                ] = None


                                st.session_state[
                                    'current_mode'
                                ] = "일반"


                                st.success(
                                    "✅ 실전 문제 및 대비 자료가 성공적으로 생성되었습니다!"
                                )


                        except Exception as e:

                            st.error(
                                f"오류가 발생했습니다: {e}"
                            )

                else:

                    st.warning(
                        "안내지와 참고자료를 모두 입력해 주세요."
                    )


        # ------------------------------------------
        # 복합 양식 교재
        # ------------------------------------------
        with col_m2:

            if st.button(
                "📑 고퀄리티 복합 양식 교재 제작실 가기",
                use_container_width=True
            ):

                st.session_state[
                    'material_mode'
                ] = True

                st.rerun()


    # ==========================================
    # 2. 암기 시험 연습 모드
    # ==========================================
    elif mode == "암기 시험 연습":

        st.subheader(
            "🧠 암기 자료 첨부 및 세부 설정"
        )


        subject = st.selectbox(
            "과목을 선택하세요",
            [
                "과학/수학 (공식 암기)",
                "영어 (지문 암기)",
                "역사 (단어 및 개념 암기)",
                "기타 일반 암기"
            ]
        )


        eng_mode = None


        if subject == "영어 (지문 암기)":

            eng_mode = st.radio(
                "테스트 방식을 선택하세요",
                [
                    "한글을 영어로 옮겨 적기 (영작)",
                    "음성으로 말하기 테스트 (Speaking)"
                ]
            )


        uploaded_img_file = st.file_uploader(
            "암기할 사진 업로드 (.jpg, .png)",
            type=[
                "jpg",
                "jpeg",
                "png"
            ]
        )


        uploaded_img = None


        if uploaded_img_file is not None:

            raw_img2 = Image.open(
                uploaded_img_file
            )

            uploaded_img = process_image(
                raw_img2
            )


        memo_text = st.text_area(
            "또는 텍스트 직접 입력",
            height=150,
            placeholder="외울 내용을 여기에 바로 적어도 됩니다."
        )


        if st.button(
            "📝 암기 테스트 문제 출제",
            use_container_width=True,
            type="primary"
        ):

            if (
                uploaded_img is not None
                or memo_text.strip()
            ):

                with st.spinner(
                    "암기 테스트를 만드는 중입니다..."
                ):

                    try:

                        contents = []


                        if (
                            subject
                            == "과학/수학 (공식 암기)"
                        ):

                            prompt_memo = (
                                "제공된 내용을 바탕으로 "
                                "주관식 빈칸 3문제 출제. "
                                "정답 제외."
                            )


                        elif (
                            subject
                            == "역사 (단어 및 개념 암기)"
                        ):

                            prompt_memo = (
                                "제공된 내용을 바탕으로 "
                                "개념 확인 3문제 출제. "
                                "정답 제외."
                            )


                        elif (
                            subject
                            == "영어 (지문 암기)"
                            and eng_mode
                            == "한글을 영어로 옮겨 적기 (영작)"
                        ):

                            prompt_memo = (
                                "영어 지문의 한글 해석을 제시하고 "
                                "영작하는 문제 출제. "
                                "정답 제외."
                            )


                        elif (
                            subject
                            == "영어 (지문 암기)"
                            and eng_mode
                            == "음성으로 말하기 테스트 (Speaking)"
                        ):

                            prompt_memo = (
                                "지문의 핵심 개요 힌트를 주고, "
                                "'아래 마이크 버튼을 눌러 "
                                "영어로 말해보세요' "
                                "안내 문구 출력."
                            )


                        else:

                            prompt_memo = (
                                "제공된 내용에 대한 "
                                "단답형 문제를 출제해 주세요. "
                                "정답 제외."
                            )


                        if uploaded_img is not None:

                            contents.append(
                                uploaded_img
                            )


                        if memo_text.strip():

                            contents.append(
                                memo_text
                            )


                        contents.append(
                            prompt_memo
                        )


                        res_memo = (
                            generate_content_with_retry(
                                client,
                                'gemini-3.5-flash',
                                contents
                            )
                        )


                        # 429 최종 실패 시
                        if res_memo is not None:

                            st.session_state[
                                'memo_subject'
                            ] = subject


                            st.session_state[
                                'memo_eng_mode'
                            ] = eng_mode


                            st.session_state[
                                'memo_test_q'
                            ] = res_memo.text


                            st.session_state[
                                'current_mode'
                            ] = "암기"


                            st.session_state[
                                'memo_grading_result'
                            ] = None


                            st.success(
                                "✅ 암기 테스트 문제가 생성되었습니다."
                            )


                    except Exception as e:

                        st.error(
                            f"오류가 발생했습니다: {e}"
                        )

            else:

                st.warning(
                    "암기할 사진이나 텍스트를 입력해 주세요."
                )


    # ==========================================
    # 결과 출력부
    # ==========================================

    if (
        st.session_state.get('current_mode') == "일반"
        and mode == "일반 수행평가 준비"
        and 'practice_question'
        in st.session_state
    ):

        st.divider()

        st.subheader(
            "결과 확인 탭"
        )


        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "📚 요약 학습 자료",
                "✍️ 실전 문제 풀이",
                "💡 평가 팁 및 주의사항",
                "🎥 추천 미디어"
            ]
        )


        # ------------------------------------------
        # 요약 자료
        # ------------------------------------------
        with tab1:

            st.markdown(
                st.session_state.get(
                    'study_material',
                    ''
                )
            )


        # ------------------------------------------
        # 평가 팁
        # ------------------------------------------
        with tab3:

            st.markdown(
                st.session_state.get(
                    'result_tips',
                    ''
                )
            )


        # ------------------------------------------
        # 추천 미디어
        # ------------------------------------------
        with tab4:

            media_text = (
                st.session_state.get(
                    'media_info',
                    ''
                )
            )

            st.write(
                media_text
            )

            st.write("---")

            st.write(
                "📌 **바로가기 링크**"
            )


            for line in [
                l.strip()
                for l in
                media_text.split('\n')
                if l.strip()
            ]:

                if ":" in line:

                    title, keyword = line.split(
                        ":",
                        1
                    )

                    keyword = keyword.strip()


                    if keyword:

                        yt_url = (
                            "https://www.youtube.com/results?search_query="
                            f"{urllib.parse.quote(keyword)}"
                        )


                        img_url = (
                            "https://www.google.com/search?tbm=isch&q="
                            f"{urllib.parse.quote(keyword)}"
                        )


                        st.markdown(
                            f"- **{title} ({keyword})**: "
                            f"[유튜브 검색]({yt_url}) | "
                            f"[이미지 검색]({img_url})"
                        )


        # ------------------------------------------
        # 실전 문제 + 채점
        # ------------------------------------------
        with tab2:

            st.info(
                st.session_state.get(
                    'practice_question',
                    ''
                )
            )


            user_ans = st.text_area(
                "내 답안 작성",
                height=220
            )


            if st.button(
                "✨ AI 채점 및 예상 점수 받기"
            ):

                if user_ans.strip():

                    with st.spinner(
                        "AI가 답안을 정밀 채점하고 있습니다..."
                    ):

                        try:

                            contents_grade = []


                            if (
                                st.session_state.get(
                                    'ref_img'
                                )
                                is not None
                            ):

                                contents_grade.append(
                                    st.session_state[
                                        'ref_img'
                                    ]
                                )


                            prompt_grade = f"""
[문제]:
{st.session_state.get('practice_question', '')}

[내 답안]:
{user_ans}

[조건]:
{st.session_state.get('guide_text', '')}

조건 충족 여부,
예상 점수,
감점 요인을
간결하게 채점해 주세요.
"""


                            contents_grade.append(
                                prompt_grade
                            )


                            res_grade = (
                                generate_content_with_retry(
                                    client,
                                    'gemini-3.5-flash',
                                    contents_grade
                                )
                            )


                            # 429 최종 실패 시
                            if res_grade is not None:

                                st.session_state[
                                    'grading_result'
                                ] = res_grade.text


                        except Exception as e:

                            st.error(
                                f"채점 중 오류가 발생했습니다: {e}"
                            )


                else:

                    st.warning(
                        "답안을 먼저 입력해 주세요."
                    )


            if st.session_state.get(
                'grading_result'
            ):

                st.markdown(
                    "### 📊 AI 채점 결과"
                )

                st.write(
                    st.session_state[
                        'grading_result'
                    ]
                )


    # ==========================================
    # 암기 테스트 결과
    # ==========================================
    elif (
        st.session_state.get('current_mode') == "암기"
        and mode == "암기 시험 연습"
        and 'memo_test_q'
        in st.session_state
    ):

        st.divider()

        st.subheader(
            "🧠 실전 암기 테스트"
        )


        st.markdown(
            st.session_state[
                'memo_test_q'
            ]
        )


        is_speaking_mode = (
            st.session_state.get(
                'memo_subject'
            )
            == "영어 (지문 암기)"
            and
            st.session_state.get(
                'memo_eng_mode'
            )
            == "음성으로 말하기 테스트 (Speaking)"
        )


        user_audio = None
        user_memo_ans = ""


        if is_speaking_mode:

            st.write(
                "🎤 **암기한 지문을 아래 마이크 버튼을 눌러 음성으로 말해보세요:**"
            )

            user_audio = st.audio_input(
                "음성 녹음"
            )


        else:

            user_memo_ans = st.text_area(
                "문제에 대한 정답을 작성해 보세요",
                height=150
            )


        if st.button(
            "📝 암기 답안 제출 및 채점하기"
        ):

            if (
                (
                    is_speaking_mode
                    and user_audio is not None
                )
                or
                (
                    not is_speaking_mode
                    and user_memo_ans.strip()
                )
            ):

                with st.spinner(
                    "채점 중입니다..."
                ):

                    try:

                        contents = []


                        if is_speaking_mode:

                            audio_bytes = (
                                user_audio.read()
                            )


                            contents.append(
                                types.Part.from_bytes(
                                    data=audio_bytes,
                                    mime_type=
                                    user_audio.type
                                    or "audio/wav"
                                )
                            )


                            prompt_memo_grade = f"""
문제:
{st.session_state['memo_test_q']}

음성을 듣고
원본과 대조하여
간결히 채점해 주세요.
"""


                        else:

                            prompt_memo_grade = f"""
문제:
{st.session_state['memo_test_q']}

답안:
{user_memo_ans}

원본 기준으로
간결히 채점해 주세요.
"""


                        if uploaded_img is not None:

                            contents.append(
                                uploaded_img
                            )


                        if memo_text.strip():

                            contents.append(
                                memo_text
                            )


                        contents.append(
                            prompt_memo_grade
                        )


                        res_memo_grade = (
                            generate_content_with_retry(
                                client,
                                'gemini-3.5-flash',
                                contents
                            )
                        )


                        # 429 최종 실패 시
                        if res_memo_grade is not None:

                            st.session_state[
                                'memo_grading_result'
                            ] = res_memo_grade.text


                    except Exception as e:

                        st.error(
                            f"채점 중 오류가 발생했습니다: {e}"
                        )


            else:

                st.warning(
                    "답안을 먼저 입력하거나 녹음해 주세요."
                )


        if st.session_state.get(
            'memo_grading_result'
        ):

            st.markdown(
                "### 📊 암기 테스트 채점 결과"
            )

            st.write(
                st.session_state[
                    'memo_grading_result'
                ]
            )


    # ==========================================
    # 화면 하단 질문하기 버튼
    # ==========================================
    st.divider()


    col_space1, col_btn, col_space2 = (
        st.columns(
            [1, 2, 1]
        )
    )


    with col_btn:

        if st.button(
            "💬 인공지능에게 질문하기",
            use_container_width=True
        ):

            st.session_state[
                'qna_mode'
            ] = True

            st.rerun()


# ==========================================
# API 키 미입력
# ==========================================
else:

    st.info(
        "👈 왼쪽 사이드바에 Gemini API 키를 입력해 주세요."
    )

