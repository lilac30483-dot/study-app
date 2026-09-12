import streamlit as st
from google import genai
from google.genai import types
import urllib.parse
from PIL import Image

st.set_page_config(page_title="수행평가 대비 프로그램", layout="centered", page_icon="📝")

# ==========================================
# 🎨 연파랑 및 무채색 UI 커스텀 디자인 적용
# ==========================================
st.markdown("""
<style>
    /* 전체 배경 및 폰트 컬러 */
    .stApp {
        background-color: #F7F9FC;
        color: #2C3E50;
    }
    /* 사이드바 배경 스타일 */
    [data-testid="stSidebar"] {
        background-color: #EDF2F7;
    }
    /* 버튼 스타일 (연파랑/무채색 톤) */
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
    /* 강조 버튼 스타일 */
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

# 세션 상태 초기화
if 'qna_mode' not in st.session_state:
    st.session_state['qna_mode'] = False
if 'material_mode' not in st.session_state:
    st.session_state['material_mode'] = False
if 'saved_api_key' not in st.session_state:
    st.session_state['saved_api_key'] = ""

# ==========================================
# ❓ 질문하기 전용 화면 (Q&A 모드)
# ==========================================
if st.session_state['qna_mode']:
    st.title("❓ 무엇이든 질문하세요")
    
    if st.button("⬅️ 메인 화면으로 돌아가기"):
        st.session_state['qna_mode'] = False
        st.rerun()
    
    st.info("수행평가 내용, 암기 안 되는 부분, 기타 궁금한 점을 인공지능에게 자유롭게 질문해 보세요.")
    user_question = st.text_area("질문 입력", height=150, placeholder="여기에 질문을 적어주세요.")
    
    if st.button("답변 받기", type="primary"):
        api_key = st.session_state.get('saved_api_key', '')
        if api_key and user_question.strip():
            client = genai.Client(api_key=api_key)
            with st.spinner("답변을 작성하고 있습니다..."):
                try:
                    res_qna = client.models.generate_content(model='gemini-3.5-flash', contents=user_question)
                    st.success("답변이 도착했습니다!")
                    st.markdown("### 💡 AI 답변")
                    st.write(res_qna.text)
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("질문을 입력하지 않았거나 API 키가 없습니다.")
            
    st.stop()

# ==========================================
# 📄 복합 양식 학습 자료 제작 전용 화면
# ==========================================
if st.session_state['material_mode']:
    st.title("📑 복합 양식 학습 자료 제작실")
    
    if st.button("⬅️ 메인 화면으로 돌아가기"):
        st.session_state['material_mode'] = False
        st.rerun()
        
    st.info("글 정보와 그림(시각적 도표/구조화) 정보가 함께 어우러진 복합 양식 학습 자료를 제작하고 파일로 다운로드할 수 있습니다.")
    
    mat_topic = st.text_area("1. 자료의 주제 또는 원본 텍스트/안내지 내용", height=120, placeholder="어떤 수행평가나 내용을 위한 자료인가요?")
    mat_request = st.text_area("2. 자료를 만들 때 반영했으면 하는 요청사항 (작성 방식, 포함할 내용 등)", height=120, placeholder="예: 표와 핵심 요약 글을 섞어서 보기 쉽게 만들어줘.")
    
    if st.button("✨ 복합 양식 자료 생성하기", type="primary", use_container_width=True):
        api_key = st.session_state.get('saved_api_key', '')
        if api_key and mat_topic.strip():
            client = genai.Client(api_key=api_key)
            with st.spinner("글 정보와 시각적 구조를 담은 복합 양식 자료를 구성 중입니다..."):
                try:
                    prompt_complex = f"""
                    다음 내용을 바탕으로 학생이 수행평가 대비에 완벽히 활용할 수 있는 '복합 양식 학습 자료'를 작성해 주세요.
                    [주제 및 내용]
                    {mat_topic}
                    [추가 요청사항]
                    {mat_request}
                    
                    [조건]
                    1. 글 정보(설명, 핵심 개념)와 그림 정보(Markdown 표, 다이어그램 형태 구조화, 시각적 배치 안내 등)를 조화롭게 섞은 복합 양식으로 작성할 것.
                    2. 절대 도움이 되며 핵심을 찌르는 내용으로 구성할 것.
                    3. HTML 태그 없이 깔끔한 마크다운 형식으로 작성할 것.
                    """
                    res_mat = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_complex)
                    st.session_state['generated_complex_material'] = res_mat.text
                    st.success("자료가 성공적으로 생성되었습니다!")
                except Exception as e:
                    st.error(f"생성 중 오류 발생: {e}")
        else:
            st.warning("주제나 내용을 입력해 주세요 (API 키 확인 필수).")
            
    if 'generated_complex_material' in st.session_state:
        st.divider()
        st.markdown("### 📄 생성된 복합 양식 자료 미리보기")
        st.markdown(st.session_state['generated_complex_material'])
        
        st.download_button(
            label="💾 자료 파일 다운로드 (.txt)",
            data=st.session_state['generated_complex_material'],
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

api_key = st.sidebar.text_input("🔑 Gemini API 키를 입력하세요", type="password")

if api_key:
    st.session_state['saved_api_key'] = api_key
    client = genai.Client(api_key=api_key)

    mode = st.radio("📌 기능을 선택하세요", ["일반 수행평가 준비", "암기 시험 연습"], horizontal=True)
    st.divider()

    # ------------------------------------------
    # 1. 일반 수행평가 준비 모드
    # ------------------------------------------
    if mode == "일반 수행평가 준비":
        st.subheader("📄 참고 자료 및 안내지 입력")
        st.caption("텍스트 파일(.txt)이나 사진 파일(.jpg, .png)을 업로드할 수 있습니다.")
        
        uploaded_file = st.file_uploader("참고자료 업로드", type=["txt", "jpg", "jpeg", "png"])
        
        ref_text = ""
        ref_img = None
        
        if uploaded_file is not None:
            if uploaded_file.name.lower().endswith('.txt'):
                ref_text = uploaded_file.read().decode("utf-8")
                st.success("텍스트 파일을 성공적으로 불러왔습니다.")
            else:
                ref_img = Image.open(uploaded_file)
                st.success("사진 자료를 성공적으로 불러왔습니다.")
                st.image(ref_img, caption="업로드된 사진", use_container_width=True)

        ref_text_input = st.text_area("1. 참고 텍스트 (사진을 올렸다면 비워둬도 됩니다)", value=ref_text, height=150, placeholder="텍스트 내용을 붙여넣으세요.")
        guide_text = st.text_area("2. 수행평가 안내지 입력 (필수)", height=150, placeholder="수행평가 유형(글쓰기, 발표, 실험 등), 조건, 유의사항을 적어주세요.")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if st.button("🚀 맞춤형 실전 문제 생성", use_container_width=True, type="primary"):
                if guide_text.strip() and (ref_text_input.strip() or ref_img is not None):
                    with st.spinner("수행평가 유형에 맞는 실전 문제를 생성 중입니다..."):
                        try:
                            contents_base = []
                            if ref_img is not None:
                                contents_base.append(ref_img)
                            contents_base.append(f"[참고 텍스트]: {ref_text_input}\n[수행평가 안내지]: {guide_text}")

                            # 1) 요약 학습 자료 생성
                            prompt_material = "위 자료를 바탕으로 학생이 보기 편하게 '핵심 요약 학습 자료'를 깔끔하게 정리해 주세요."
                            res_material = client.models.generate_content(model='gemini-3.5-flash', contents=contents_base + [prompt_material])
                            st.session_state['study_material'] = res_material.text

                            # 2) 평가 팁 생성
                            prompt_tips = "위 자료를 바탕으로 고득점 꿀팁과 감점 예방 주의사항을 분석해 주세요."
                            res_tips = client.models.generate_content(model='gemini-3.5-flash', contents=contents_base + [prompt_tips])
                            st.session_state['result_tips'] = res_tips.text

                            # 3) 상황 맞춤형 문제 생성 (글쓰기면 글쓰기 조건에 맞는 서술형/작문형 문제 출제)
                            prompt_q = """
                            위 수행평가 안내지와 참고자료를 분석하여 실제 평가에 딱 맞는 실전 문제를 출제해 주세요.
                            [출제 원칙]
                            - 안내지에서 요구하는 수행평가 방식(예: 글쓰기라면 글 작성 요구, 발표라면 대본/발표문 작성 등)에 정확히 부합하는 상황 맞춤형 서술형/작문형 문제를 출제하세요.
                            - 자료에 없는 내용을 억지로 가정해서 풀게 만들지 마세요.
                            - 정답이나 해설은 절대 출력하지 말고 오직 '문제 내용'만 출력하세요.
                            """
                            res_q = client.models.generate_content(model='gemini-3.5-flash', contents=contents_base + [prompt_q])
                            st.session_state['practice_question'] = res_q.text
                            st.session_state['ref_text_input'] = ref_text_input
                            st.session_state['ref_img'] = ref_img
                            st.session_state['guide_text'] = guide_text

                            # 4) 추천 미디어 키워드 생성
                            prompt_media = "위 자료의 핵심 주제와 관련된 검색 키워드를 '유튜브 검색어: [키워드]\n이미지 검색어: [키워드]' 형식으로 추출해 주세요."
                            res_media = client.models.generate_content(model='gemini-3.5-flash', contents=contents_base + [prompt_media])
                            st.session_state['media_info'] = res_media.text

                            st.session_state['grading_result'] = None
                            st.session_state['current_mode'] = "일반"
                            st.success("✅ 실전 문제가 생성되었습니다!")
                        except Exception as e:
                            st.error(f"오류가 발생했습니다: {e}")
                else:
                    st.warning("안내지와 참고자료를 모두 입력해 주세요.")
                    
        with col_m2:
            if st.button("📑 복합 양식 자료 제작실 가기", use_container_width=True):
                st.session_state['material_mode'] = True
                st.rerun()

    # ------------------------------------------
    # 2. 암기 시험 연습 모드
    # ------------------------------------------
    elif mode == "암기 시험 연습":
        st.subheader("🧠 암기 자료 첨부 및 세부 설정")
        
        subject = st.selectbox("과목을 선택하세요", ["과학/수학 (공식 암기)", "영어 (지문 암기)", "역사 (단어 및 개념 암기)", "기타 일반 암기"])
        
        eng_mode = None
        if subject == "영어 (지문 암기)":
            eng_mode = st.radio("테스트 방식을 선택하세요", ["한글을 영어로 옮겨 적기 (영작)", "음성으로 말하기 테스트 (Speaking)"])

        uploaded_img = st.file_uploader("암기할 사진 업로드 (.jpg, .png)", type=["jpg", "jpeg", "png"])
        memo_text = st.text_area("또는 텍스트 직접 입력", height=150, placeholder="외울 내용을 여기에 바로 적어도 됩니다.")
        
        if st.button("🎯 암기 테스트 문제 출제", use_container_width=True, type="primary"):
            if uploaded_img is not None or memo_text.strip():
                with st.spinner("오류 없는 깔끔한 암기 테스트를 만드는 중입니다..."):
                    try:
                        contents = []
                        
                        if subject == "과학/수학 (공식 암기)":
                            prompt_memo = "제공된 내용을 바탕으로 '과학/수학 공식 암기 테스트'용 주관식 빈칸/완성 문제를 3문제 출제해 주세요. HTML 태그나 특수기호 없이 깔끔하게 텍스트로만 작성하고 정답은 미리 적지 마세요."
                        elif subject == "역사 (단어 및 개념 암기)":
                            prompt_memo = "제공된 내용을 바탕으로 '역사 단어 및 개념 테스트'용 문제를 3문제 출제해 주세요. HTML 태그 없이 깔끔한 텍스트로만 작성하고 정답은 미리 적지 마세요."
                        elif subject == "영어 (지문 암기)" and eng_mode == "한글을 영어로 옮겨 적기 (영작)":
                            prompt_memo = "제공된 영어 지문을 바탕으로 한글 해석을 제시하고 영작하는 테스트 문제를 출제해 주세요. 정답은 미리 적지 마세요."
                        elif subject == "영어 (지문 암기)" and eng_mode == "음성으로 말하기 테스트 (Speaking)":
                            prompt_memo = "지문의 핵심 개요나 첫 문장 힌트를 주고, '아래 마이크 버튼을 눌러 영어로 말해보세요'라는 안내를 텍스트로 깔끔하게 출력해 주세요."
                        else:
                            prompt_memo = "제공된 내용을 바탕으로 암기 확인용 단답형 문제를 깔끔하게 출제해 주세요. 정답은 미리 적지 마세요."

                        if uploaded_img is not None:
                            uploaded_img.seek(0)
                            contents.append(Image.open(uploaded_img))
                        if memo_text.strip():
                            contents.append(memo_text)
                        contents.append(prompt_memo)

                        res_memo = client.models.generate_content(model='gemini-3.5-flash', contents=contents)
                        
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
    # 결과 출력부 렌더링
    # ==========================================
    if st.session_state.get('current_mode') == "일반" and mode == "일반 수행평가 준비" and 'practice_question' in st.session_state:
        st.divider()
        st.subheader("결과 확인 탭")
        tab1, tab2, tab3, tab4 = st.tabs(["📚 요약 학습 자료", "✍️ 실전 문제 풀이 (답안 작성 및 예측)", "💡 평가 팁 및 주의사항", "🎥 추천 미디어"])

        with tab1:
            st.markdown(st.session_state.get('study_material', ''))

        with tab2:
            st.info(st.session_state.get('practice_question', ''))
            user_ans = st.text_area("내 답안 작성 (요청받은 글쓰기 또는 서술형 답변을 작성하세요)", height=220)
            
            if st.button("✨ AI 채점 및 예상 점수 받기"):
                if user_ans.strip():
                    with st.spinner("AI가 답안을 정밀 채점하고 예상 점수를 계산하고 있습니다..."):
                        contents_grade = []
                        if st.session_state.get('ref_img') is not None:
                            contents_grade.append(st.session_state['ref_img'])
                            
                        prompt_grade = f"""
                        [출제 문제]: {st.session_state.get('practice_question', '')}
                        [사용자 답안]: {user_ans}
                        [참고자료 원문]: {st.session_state.get('ref_text_input', '')}
                        [수행평가 안내지 조건]: {st.session_state.get('guide_text', '')}
                        
                        사용자의 답안을 채점해 주세요.
                        1. 안내지 조건 충족 여부 및 상세 피드백
                        2. 예상 수행평가 점수 (안내지 조건을 고려해 100점 만점 기준으로 예측)
                        3. 감점 요인 및 보완해야 할 모범 답안
                        """
                        contents_grade.append(prompt_grade)
                        
                        res_grade = client.models.generate_content(model='gemini-3.5-flash', contents=contents_grade)
                        st.session_state['grading_result'] = res_grade.text
                else:
                    st.warning("답안을 먼저 입력해 주세요.")
                    
            if st.session_state.get('grading_result'):
                st.markdown("### 📊 AI 채점 및 점수 예측 결과")
                st.write(st.session_state['grading_result'])

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

    elif st.session_state.get('current_mode') == "암기" and mode == "암기 시험 연습" and 'memo_test_q' in st.session_state:
        st.divider()
        st.subheader("🧠 실전 암기 테스트")
        st.markdown(st.session_state['memo_test_q'])
        
        is_speaking_mode = (st.session_state.get('memo_subject') == "영어 (지문 암기)" and st.session_state.get('memo_eng_mode') == "음성으로 말하기 테스트 (Speaking)")
        
        user_audio = None
        user_memo_ans = ""
        
        if is_speaking_mode:
            st.write("🎤 **암기한 지문을 아래 마이크 버튼을 눌러 음성으로 말해보세요:**")
            user_audio = st.audio_input("음성 녹음")
        else:
            user_memo_ans = st.text_area("문제에 대한 정답을 작성해 보세요", height=150)
        
        if st.button("📝 암기 답안 제출 및 채점하기"):
            if (is_speaking_mode and user_audio is not None) or (not is_speaking_mode and user_memo_ans.strip()):
                with st.spinner("원본 자료와 비교하여 채점 중입니다..."):
                    try:
                        contents = []
                        if is_speaking_mode:
                            audio_bytes = user_audio.read()
                            audio_part = types.Part.from_bytes(
                                data=audio_bytes,
                                mime_type=user_audio.type or "audio/wav"
                            )
                            contents.append(audio_part)
                            
                            prompt_memo_grade = f"""
                            [출제 문제]: {st.session_state['memo_test_q']}
                            사용자가 영어 지문을 직접 말한 음성 파일입니다. 원본과 대조하여 채점해 주세요.
                            1. 성공 여부 판단
                            2. 음성 인식 텍스트(STT)
                            3. 틀린 부분 및 교정
                            """
                        else:
                            prompt_memo_grade = f"""
                            [출제된 암기 문제]: {st.session_state['memo_test_q']}
                            [사용자가 작성한 답안]: {user_memo_ans}
                            원본 자료를 기준으로 정확히 채점하고 정답을 알려주세요.
                            """

                        if uploaded_img is not None:
                            uploaded_img.seek(0)
                            contents.append(Image.open(uploaded_img))
                        if memo_text.strip():
                            contents.append(memo_text)
                        contents.append(prompt_memo_grade)

                        res_memo_grade = client.models.generate_content(model='gemini-3.5-flash', contents=contents)
                        st.session_state['memo_grading_result'] = res_memo_grade.text
                    except Exception as e:
                        st.error(f"채점 중 오류가 발생했습니다: {e}")
            else:
                if is_speaking_mode:
                    st.warning("마이크 버튼을 눌러 음성을 먼저 녹음해 주세요.")
                else:
                    st.warning("정답을 먼저 입력해 주세요.")
        
        if st.session_state.get('memo_grading_result'):
            st.markdown("### 📊 암기 테스트 채점 결과")
            st.write(st.session_state['memo_grading_result'])

    # ==========================================
    # 화면 하단: ❓ 질문하기 버튼
    # ==========================================
    st.divider()
    col_space1, col_btn, col_space2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button("💬 인공지능에게 질문하기", use_container_width=True):
            st.session_state['qna_mode'] = True
            st.rerun()

else:
    st.info("👈 왼쪽 사이드바에 Gemini API 키를 입력해 주세요.")

