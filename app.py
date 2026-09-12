import streamlit as st
from google import genai
from google.genai import types
import urllib.parse
from PIL import Image
import time

st.set_page_config(page_title="수행평가 대비 프로그램", layout="centered", page_icon="📝")

# ==========================================
# 🎨 연파랑 및 무채색 UI 커스텀 디자인 적용
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #F7F9FC; color: #2C3E50; }
    [data-testid="stSidebar"] { background-color: #EDF2F7; }
    .stButton > button {
        background-color: #E2E8F0; color: #2D3748;
        border: 1px solid #CBD5E0; border-radius: 6px; font-weight: 600;
    }
    .stButton > button:hover { background-color: #CBD5E0; color: #1A202C; }
    .stButton > button[kind="primary"] { background-color: #3182CE; color: white; border: none; }
    .stButton > button[kind="primary"]:hover { background-color: #2B6CB0; }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'qna_mode' not in st.session_state: st.session_state['qna_mode'] = False
if 'material_mode' not in st.session_state: st.session_state['material_mode'] = False
if 'saved_api_key' not in st.session_state: st.session_state['saved_api_key'] = ""

# ==========================================
# 🛠️ 429 무료 API 과부하 방지용 자동 재시도 함수 (절대 삭제 금지)
# ==========================================
def generate_content_with_retry(client, model_name, contents, config=None, max_retries=4):
    for attempt in range(max_retries):
        try:
            if config:
                return client.models.generate_content(model=model_name, contents=contents, config=config)
            else:
                return client.models.generate_content(model=model_name, contents=contents)
        except Exception as e:
            error_msg = str(e)
            # 429 과부하 에러가 발생한 경우
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # 5초, 10초, 15초 대기 시간 증가
                    st.warning(f"⏳ 무료 API 일시적 과부하(429) 발생. {wait_time}초 대기 후 자동으로 재시도합니다... (시도 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise e # 최대 재시도 횟수를 넘으면 에러 발생
            else:
                raise e # 429가 아닌 다른 에러는 즉시 발생

# ==========================================
# ❓ 질문하기 전용 화면 (Q&A 모드)
# ==========================================
if st.session_state['qna_mode']:
    st.title("❓ 무엇이든 질문하세요")
    if st.button("⬅️ 메인 화면으로 돌아가기"):
        st.session_state['qna_mode'] = False
        st.rerun()
    
    st.info("수행평가 내용, 암기 안 되는 부분, 기타 궁금한 점을 인공지능에게 자유롭게 질문해 보세요. (🌐 인터넷 실시간 검색이 지원됩니다)")
    user_question = st.text_area("질문 입력", height=150, placeholder="여기에 질문을 적어주세요.")
    
    if st.button("답변 받기", type="primary"):
        api_key = st.session_state.get('saved_api_key', '')
        if api_key and user_question.strip():
            client = genai.Client(api_key=api_key)
            with st.spinner("인터넷을 검색하며 답변을 작성하고 있습니다..."):
                try:
                    config_qna = types.GenerateContentConfig(tools=[{"google_search": {}}])
                    # 429 방지 함수 적용 (버전은 3.5 유지)
                    res_qna = generate_content_with_retry(
                        client, 'gemini-3.5-flash', user_question, config=config_qna
                    )
                    st.success("답변이 도착했습니다!")
                    st.markdown("### 💡 AI 답변")
                    st.write(res_qna.text)
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("질문을 입력하지 않았거나 API 키가 없습니다.")
    st.stop()

# ==========================================
# 📄 복합 양식 학습 자료 제작 전용 화면 (인터넷 사진 연동 및 과부하 방지)
# ==========================================
if st.session_state['material_mode']:
    st.title("📑 고퀄리티 복합 양식 교재 제작실")
    if st.button("⬅️ 메인 화면으로 돌아가기"):
        st.session_state['material_mode'] = False
        st.rerun()
        
    st.info("글자와 인터넷 실제 사진/도표가 어우러진 진정한 복합 양식 학습 노트를 제작합니다.")
    
    mat_img_file = st.file_uploader("🖼️ 참고 사진/자료 업로드 (선택 사항)", type=["jpg", "jpeg", "png"], key="mat_img")
    mat_img = None
    if mat_img_file is not None:
        mat_img = Image.open(mat_img_file)
        st.image(mat_img, caption="업로드된 사진", use_container_width=True)
    
    mat_topic = st.text_area("1. 교재로 만들 핵심 주제나 원본 텍스트", height=120, placeholder="예: 중세 유럽의 백년전쟁과 잔 다르크의 활약상")
    mat_request = st.text_area("2. 추가 요청사항 (선택 사항)", height=120, placeholder="예: 전쟁의 원인과 전개 과정을 표로 정리하고, 관련 실제 역사 유물이나 초상화 사진을 본문에 넣어줘.")
    
    if st.button("✨ 복합 양식 학습 자료 생성하기 (인터넷 사진+텍스트)", type="primary", use_container_width=True):
        api_key = st.session_state.get('saved_api_key', '')
        if api_key and (mat_topic.strip() or mat_img is not None):
            client = genai.Client(api_key=api_key)
            st.session_state.pop('generated_complex_material', None)
            
            with st.spinner("인터넷에서 관련 사진을 찾고 완벽한 교재를 작성 중입니다... (약 10~15초 소요)"):
                try:
                    contents_mat = []
                    if mat_img is not None:
                        contents_mat.append(mat_img)
                    
                    prompt_complex = """
                    당신은 최고의 일타 강사이자 교재 제작 전문가입니다.
                    다음 제공된 자료(사진 및 텍스트)를 바탕으로, 학생들이 직관적으로 이해하고 암기할 수 있는 '고품질 복합 양식 학습 자료'를 만들어주세요.

                    [🚨 복합 양식 핵심 규칙]
                    1. 구글 검색 기능을 활용하여, 주제와 밀접하게 연관된 **실제 인터넷 사진, 도표, 유물 등의 이미지 URL(위키미디어 공용 등 신뢰할 수 있는 소스)**을 2개 이상 찾으세요.
                    2. 찾은 실제 이미지 URL을 반드시 마크다운 문법인 `![이미지 설명](실제_이미지_URL)` 형태로 글 내용 중간중간 알맞은 위치에 삽입하세요. (임의로 가짜 주소를 만들지 마세요).
                    3. ┌, ─, ┐ 같은 '특수문자 선 긋기(ASCII Art)'는 절대 사용하지 마세요. (폰트 깨짐 방지)
                    4. 시각화가 필요할 때는 오직 **표(Markdown Table)**, **글머리 기호(-)**, **인용구(>)**, 그리고 위에서 요구한 **실제 마크다운 이미지**만 사용하세요.
                    """
                    
                    if mat_topic.strip():
                        prompt_complex += f"\n\n[주제 및 내용]\n{mat_topic}\n"
                    if mat_request.strip():
                        prompt_complex += f"\n[추가 요청사항]\n{mat_request}\n"
                        
                    contents_mat.append(prompt_complex)

                    config_mat = types.GenerateContentConfig(tools=[{"google_search": {}}])
                    
                    # 429 방지 함수 적용 (버전은 3.5 유지)
                    res_mat = generate_content_with_retry(
                        client, 'gemini-3.5-flash', contents_mat, config=config_mat
                    )
                    
                    st.session_state['generated_complex_material'] = res_mat.text
                    st.success("고퀄리티 복합 양식 학습 자료가 성공적으로 생성되었습니다!")
                    
                except Exception as e:
                    st.error(f"과부하 대기 시간 초과 또는 오류가 발생했습니다: {e}")
        else:
            st.warning("주제(내용)를 입력하거나 참고 사진을 첨부해 주세요 (API 키 확인 필수).")
            
    if 'generated_complex_material' in st.session_state:
        st.divider()
        st.markdown("### 📄 완성된 복합 양식 학습 노트")
        st.markdown(st.session_state['generated_complex_material'])
        
        st.download_button(
            label="💾 자료 파일 다운로드 (.txt)",
            data=st.session_state['generated_complex_material'].encode('utf-8-sig'),
            file_name="complex_study_material.txt",
            mime="text/plain",
            use_container_width=True
        )
    st.stop()

# ==========================================
# 📝 메인 화면 시작 (일반 수행/암기 모드)
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
    # 1. 일반 수행평가 준비 모드 (429 에러 방지 통합 호출)
    # ------------------------------------------
    if mode == "일반 수행평가 준비":
        st.subheader("📄 참고 자료 및 안내지 입력")
        uploaded_file = st.file_uploader("참고자료 업로드 (.txt, .jpg, .png)", type=["txt", "jpg", "jpeg", "png"])
        
        ref_text, ref_img = "", None
        if uploaded_file is not None:
            if uploaded_file.name.lower().endswith('.txt'):
                ref_text = uploaded_file.read().decode("utf-8")
                st.success("텍스트 파일을 성공적으로 불러왔습니다.")
            else:
                ref_img = Image.open(uploaded_file)
                st.success("사진 자료를 성공적으로 불러왔습니다.")
                st.image(ref_img, caption="업로드된 사진", use_container_width=True)

        ref_text_input = st.text_area("1. 참고 텍스트", value=ref_text, height=150, placeholder="참고할 텍스트 내용을 붙여넣으세요.")
        guide_text = st.text_area("2. 수행평가 안내지 입력 (필수)", height=150, placeholder="수행평가 유형(글쓰기, 발표, 실험 등), 조건, 글자 수 등을 적어주세요.")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if st.button("📝 맞춤형 실전 문제 생성", use_container_width=True, type="primary"):
                if guide_text.strip() and (ref_text_input.strip() or ref_img is not None):
                    with st.spinner("과부하 방지를 위해 한 번에 모든 자료를 분석하고 있습니다..."):
                        try:
                            contents_base = []
                            if ref_img is not None: contents_base.append(ref_img)
                            contents_base.append(f"[참고 텍스트]: {ref_text_input}\n[수행평가 안내지]: {guide_text}")

                            prompt_combined = """
                            위 수행평가 안내지와 참고자료를 분석하여 다음 4가지 항목을 작성해 주세요.
                            [🚨매우 중요🚨] 각 항목의 사이에는 반드시 `===구분선===` 이라는 텍스트를 정확히 입력하여 내용을 나누어 주세요.

                            1. 핵심 요약 학습 자료: 학생이 보기 편하게 깔끔하게 정리.
                            ===구분선===
                            2. 고득점 꿀팁 및 감점 예방 주의사항 분석.
                            ===구분선===
                            3. 실전 문제: 안내지에 부합하는 서술형/작문형 문제 (정답이나 해설 없이 오직 문제만 출력).
                            ===구분선===
                            4. 추천 미디어 검색어: 핵심 주제와 관련된 키워드를 '유튜브 검색어: [키워드]\n이미지 검색어: [키워드]' 형식으로 추출.
                            """
                            
                            # 429 방지 함수 적용 (버전은 3.5 유지)
                            res_combined = generate_content_with_retry(
                                client, 'gemini-3.5-flash', contents_base + [prompt_combined]
                            )
                            
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
                            st.error(f"과부하 대기 시간 초과 또는 오류가 발생했습니다: {e}")
                else:
                    st.warning("안내지와 참고자료를 모두 입력해 주세요.")
                    
        with col_m2:
            if st.button("📑 고퀄리티 복합 양식 교재 제작실 가기", use_container_width=True):
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
        
        if st.button("📝 암기 테스트 문제 출제", use_container_width=True, type="primary"):
            if uploaded_img is not None or memo_text.strip():
                with st.spinner("오류 없는 깔끔한 암기 테스트를 만드는 중입니다..."):
                    try:
                        contents = []
                        if subject == "과학/수학 (공식 암기)": prompt_memo = "제공된 내용을 바탕으로 '과학/수학 공식 암기 테스트'용 주관식 빈칸 문제를 3문제 출제. 정답은 미리 적지 말 것."
                        elif subject == "역사 (단어 및 개념 암기)": prompt_memo = "제공된 내용을 바탕으로 '역사 단어 및 개념 테스트'용 문제를 3문제 출제. 정답 제외."
                        elif subject == "영어 (지문 암기)" and eng_mode == "한글을 영어로 옮겨 적기 (영작)": prompt_memo = "제공된 영어 지문을 바탕으로 한글 해석을 제시하고 영작하는 테스트 문제 출제. 정답 제외."
                        elif subject == "영어 (지문 암기)" and eng_mode == "음성으로 말하기 테스트 (Speaking)": prompt_memo = "지문의 핵심 개요나 첫 문장 힌트를 주고, '아래 마이크 버튼을 눌러 영어로 말해보세요'라는 안내를 텍스트로 출력."
                        else: prompt_memo = "제공된 내용을 바탕으로 암기 확인용 단답형 문제를 출제해 주세요. 정답은 미리 적지 마세요."

                        if uploaded_img is not None:
                            uploaded_img.seek(0)
                            contents.append(Image.open(uploaded_img))
                        if memo_text.strip(): contents.append(memo_text)
                        contents.append(prompt_memo)

                        # 429 방지 함수 적용 (버전은 3.5 유지)
                        res_memo = generate_content_with_retry(client, 'gemini-3.5-flash', contents)
                        
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
        tab1, tab2, tab3, tab4 = st.tabs(["📚 요약 학습 자료", "✍️ 실전 문제 풀이", "💡 평가 팁 및 주의사항", "🎥 추천 미디어"])

        with tab1: st.markdown(st.session_state.get('study_material', ''))
        with tab3: st.markdown(st.session_state.get('result_tips', ''))
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
            user_ans = st.text_area("내 답안 작성", height=220)
            
            if st.button("✨ AI 채점 및 예상 점수 받기"):
                if user_ans.strip():
                    with st.spinner("AI가 답안을 정밀 채점하고 예상 점수를 계산하고 있습니다..."):
                        contents_grade = []
                        if st.session_state.get('ref_img') is not None: contents_grade.append(st.session_state['ref_img'])
                        prompt_grade = f"""
                        [출제 문제]: {st.session_state.get('practice_question', '')}
                        [사용자 답안]: {user_ans}
                        [참고자료 원문]: {st.session_state.get('ref_text_input', '')}
                        [수행평가 안내지 조건]: {st.session_state.get('guide_text', '')}
                        사용자의 답안을 채점해 주세요. 1. 조건 충족 여부 2. 예상 점수 3. 감점 요인 및 보완 모델
                        """
                        contents_grade.append(prompt_grade)
                        
                        # 429 방지 함수 적용 (버전은 3.5 유지)
                        res_grade = generate_content_with_retry(client, 'gemini-3.5-flash', contents_grade)
                        st.session_state['grading_result'] = res_grade.text
                else:
                    st.warning("답안을 먼저 입력해 주세요.")
                    
            if st.session_state.get('grading_result'):
                st.markdown("### 📊 AI 채점 및 점수 예측 결과")
                st.write(st.session_state['grading_result'])

    elif st.session_state.get('current_mode') == "암기" and mode == "암기 시험 연습" and 'memo_test_q' in st.session_state:
        st.divider()
        st.subheader("🧠 실전 암기 테스트")
        st.markdown(st.session_state['memo_test_q'])
        
        is_speaking_mode = (st.session_state.get('memo_subject') == "영어 (지문 암기)" and st.session_state.get('memo_eng_mode') == "음성으로 말하기 테스트 (Speaking)")
        user_audio, user_memo_ans = None, ""
        
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
                            contents.append(types.Part.from_bytes(data=audio_bytes, mime_type=user_audio.type or "audio/wav"))
                            prompt_memo_grade = f"[출제 문제]: {st.session_state['memo_test_q']}\n사용자가 직접 말한 음성입니다. 원본과 대조하여 채점해 주세요."
                        else:
                            prompt_memo_grade = f"[출제된 문제]: {st.session_state['memo_test_q']}\n[사용자 답안]: {user_memo_ans}\n원본 자료 기준으로 정확히 채점해 주세요."

                        if uploaded_img is not None:
                            uploaded_img.seek(0)
                            contents.append(Image.open(uploaded_img))
                        if memo_text.strip(): contents.append(memo_text)
                        contents.append(prompt_memo_grade)

                        # 429 방지 함수 적용 (버전은 3.5 유지)
                        res_memo_grade = generate_content_with_retry(client, 'gemini-3.5-flash', contents)
                        st.session_state['memo_grading_result'] = res_memo_grade.text
                    except Exception as e:
                        st.error(f"채점 중 오류가 발생했습니다: {e}")
            else:
                st.warning("답안을 먼저 입력하거나 녹음해 주세요.")
        
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

