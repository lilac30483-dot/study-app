import streamlit as st
from google import genai
from google.genai import types
import urllib.parse
from PIL import Image

st.set_page_config(page_title="수행평가 대비 프로그램", layout="centered", page_icon="📝")

# 세션 상태 초기화
if 'qna_mode' not in st.session_state:
    st.session_state['qna_mode'] = False
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
            
    st.stop() # 질문 창에서는 아래쪽 메인 화면이 보이지 않도록 렌더링 중지

# ==========================================
# 📝 메인 화면 시작
# ==========================================
st.title("📝 수행평가 대비 프로그램")

# 오류 방지용 기본 변수
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
        guide_text = st.text_area("2. 수행평가 안내지 입력 (필수)", height=150, placeholder="수행평가 조건, 유의사항, 감점 기준 등을 적어주세요.")

        if st.button("🚀 수행평가 자료 및 실전 문제 생성", use_container_width=True, type="primary"):
            if guide_text.strip() and (ref_text_input.strip() or ref_img is not None):
                with st.spinner("AI가 자료를 분석하고 요약본과 문제를 생성하고 있습니다..."):
                    try:
                        contents_base = []
                        if ref_img is not None:
                            contents_base.append(ref_img)
                        contents_base.append(f"[참고 텍스트]: {ref_text_input}\n[수행평가 안내지]: {guide_text}")

                        # 1) 요약 학습 자료 생성
                        prompt_material = "위 자료를 바탕으로 학생이 보기 편하게 '핵심 요약 학습 자료'를 깔끔하게 정리해서 만들어주세요."
                        res_material = client.models.generate_content(model='gemini-3.5-flash', contents=contents_base + [prompt_material])
                        st.session_state['study_material'] = res_material.text

                        # 2) 평가 팁 생성
                        prompt_tips = "위 자료를 바탕으로 수행평가 고득점 꿀팁과 감점을 피하기 위한 주의사항을 분석해 주세요."
                        res_tips = client.models.generate_content(model='gemini-3.5-flash', contents=contents_base + [prompt_tips])
                        st.session_state['result_tips'] = res_tips.text

                        # 3) 문제 생성 (객관식 + 서술형)
                        prompt_q = """
                        위 자료를 바탕으로 실제 시험에 나올 법한 문제를 출제해 주세요.
                        [출제 조건]
                        1. 객관식 문제(선택지 4~5개) 2개
                        2. 핵심 서술형 문제 2개
                        - 자료에 없는 내용을 가정해서 풀게 만들지 마세요.
                        - 정답이나 해설은 절대 출력하지 말고, 오직 '문제'만 명확하게 출력해 주세요.
                        """
                        res_q = client.models.generate_content(model='gemini-3.5-flash', contents=contents_base + [prompt_q])
                        st.session_state['practice_question'] = res_q.text
                        st.session_state['ref_text_input'] = ref_text_input
                        st.session_state['ref_img'] = ref_img
                        st.session_state['guide_text'] = guide_text

                        # 4) 추천 미디어 키워드 생성
                        prompt_media = """
                        위 자료의 핵심 주제와 관련된 검색 키워드를 추출해 주세요.
                        형식:
                        유튜브 검색어: [키워드]
                        이미지 검색어: [키워드]
                        """
                        res_media = client.models.generate_content(model='gemini-3.5-flash', contents=contents_base + [prompt_media])
                        st.session_state['media_info'] = res_media.text

                        st.session_state['grading_result'] = None
                        st.session_state['current_mode'] = "일반"
                        st.success("✅ 생성 완료! 아래 탭을 눌러 결과를 확인하세요.")
                    except Exception as e:
                        st.error(f"오류가 발생했습니다: {e}")
            else:
                st.warning("수행평가 안내지와 참고자료(텍스트 또는 사진)를 모두 입력해 주세요.")

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
                with st.spinner("암기 테스트를 만드는 중입니다..."):
                    try:
                        contents = []
                        
                        if subject == "과학/수학 (공식 암기)":
                            prompt_memo = "제공된 이미지나 텍스트 내용을 바탕으로 '과학/수학 공식 암기 테스트'를 만들어주세요. 핵심 공식을 묻는 문제를 만들되 정답은 미리 출력하지 마세요."
                        elif subject == "역사 (단어 및 개념 암기)":
                            prompt_memo = "제공된 내용을 바탕으로 '역사 암기 테스트'를 만들어주세요. 단어 테스트와 서술형 테스트를 섞어서 내고, 정답은 출력하지 마세요."
                        elif subject == "영어 (지문 암기)" and eng_mode == "한글을 영어로 옮겨 적기 (영작)":
                            prompt_memo = "한글 해석을 제시하고 올바른 영문장으로 영작하게 유도하는 문제를 만드세요. 영문 정답은 미리 출력하지 마세요."
                        elif subject == "영어 (지문 암기)" and eng_mode == "음성으로 말하기 테스트 (Speaking)":
                            prompt_memo = "지문의 한글 개요 또는 첫 문장의 일부만 힌트로 주고, '아래 마이크 버튼을 누르고 처음부터 끝까지 영어로 말해보세요'라는 안내문구를 출력하세요."
                        else:
                            prompt_memo = "제공된 내용을 바탕으로 '암기 확인용 빈칸 뚫기 또는 단답형 문제'를 만들어주세요. 정답은 미리 출력하지 마세요."

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
                        st.success("✅ 암기 문제가 생성되었습니다. 아래에서 풀어보세요.")
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
        tab1, tab2, tab3, tab4 = st.tabs(["📚 요약 학습 자료", "✍️ 실전 문제 풀이 (채점 및 예측)", "💡 평가 팁 및 주의사항", "🎥 추천 미디어"])

        with tab1:
            st.markdown(st.session_state.get('study_material', ''))

        with tab2:
            st.info(st.session_state.get('practice_question', ''))
            user_ans = st.text_area("내 답안 작성 (객관식 정답과 서술형 답안을 작성하세요)", height=200)
            
            if st.button("✨ AI 채점 및 수행 점수 예측받기"):
                if user_ans.strip():
                    with st.spinner("AI가 답안을 채점하고 예상 점수를 계산하고 있습니다..."):
                        contents_grade = []
                        if st.session_state.get('ref_img') is not None:
                            contents_grade.append(st.session_state['ref_img'])
                            
                        prompt_grade = f"""
                        [출제 문제]: {st.session_state.get('practice_question', '')}
                        [사용자 답안]: {user_ans}
                        [참고자료 원문]: {st.session_state.get('ref_text_input', '')}
                        [수행평가 안내지 조건]: {st.session_state.get('guide_text', '')}
                        
                        사용자의 답안을 채점해 주세요.
                        1. 각 문제별(객관식/서술형) 정답 및 오답 여부
                        2. 예상 수행평가 점수 (안내지 조건을 고려해 100점 만점 기준으로 수치화하여 예측)
                        3. 틀린 이유와 보완해야 할 모범 답안
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
        st.info(st.session_state['memo_test_q'])
        
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
                            사용자가 원본 영어 지문을 직접 입으로 말해서 녹음한 음성 파일입니다. 원본 자료와 음성을 대조해 주세요.
                            1. 성공 여부 판단
                            2. 음성 인식 텍스트(STT)
                            3. 틀린 부분(발음/누락) 및 원본 문장 교정
                            """
                        else:
                            prompt_memo_grade = f"""
                            [출제된 암기 문제]: {st.session_state['memo_test_q']}
                            [사용자가 작성한 답안]: {user_memo_ans}
                            원본 자료를 기준으로 채점해 주세요. 맞은 것과 틀린 것을 구별하고 올바른 정답을 알려주세요.
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

