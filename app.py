import streamlit as st
from google import genai
from google.genai import types
import urllib.parse
from PIL import Image

st.set_page_config(page_title="수행평가 대비 프로그램", layout="centered")

st.title("📝 수행평가 대비 프로그램")

uploaded_img = None
memo_text = ""

api_key = st.sidebar.text_input("Gemini API 키를 입력하세요", type="password")

if api_key:
    client = genai.Client(api_key=api_key)

    mode = st.radio("📌 수행평가 유형을 선택하세요", ["일반 수행평가", "암기 시험"])
    st.divider()

    if mode == "일반 수행평가":
        st.subheader("📄 자료 입력 및 파일 첨부")
        uploaded_file = st.file_uploader("참고자료 파일 업로드 (.txt)", type=["txt"])
        uploaded_text = ""
        if uploaded_file is not None:
            uploaded_text = uploaded_file.read().decode("utf-8")
            st.success("파일을 성공적으로 불러왔습니다.")

        ref_text = st.text_area("1. 참고자료 입력", value=uploaded_text, height=150, placeholder="내용을 붙여넣거나 파일을 업로드하세요.")
        guide_text = st.text_area("2. 수행평가 안내지 입력", height=150, placeholder="수행평가 안내지/유의사항을 붙여넣으세요.")

        if st.button("수행평가 분석 및 문제 생성"):
            if ref_text.strip() and guide_text.strip():
                with st.spinner("자료를 분석하여 문제 및 참고 자료를 생성 중입니다..."):
                    try:
                        prompt_tips = f"""
                        아래 자료를 바탕으로 수행평가 대비 필수 핵심 개념과 고득점 꿀팁, 감점 예방 주의사항을 작성해 주세요.
                        [참고자료]
                        {ref_text}
                        [수행평가 안내지]
                        {guide_text}
                        """
                        res_tips = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_tips)
                        st.session_state['result_tips'] = res_tips.text

                        prompt_q = f"""
                        아래 참고자료를 바탕으로 수행평가에 출제될 수 있는 핵심 서술형 문제 3개를 출제해 주세요.
                        [절대 지켜야 할 출제 조건]
                        - "[제시된 상황]", "[가상의 조건]" 같이 참고자료에 없는 내용을 가정해서 풀 수 없게 만들지 마세요.
                        - 반드시 입력된 '참고자료' 안에서만 정답을 찾고 서술할 수 있는 명확한 문제여야 합니다.
                        - 다른 부가 설명 없이 오직 '문제 질문 내용'만 출력하세요.
                        [참고자료]
                        {ref_text}
                        [수행평가 안내지]
                        {guide_text}
                        """
                        res_q = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_q)
                        st.session_state['practice_question'] = res_q.text

                        prompt_media = f"""
                        아래 자료의 핵심 주제와 관련된 검색 키워드를 추출해 주세요.
                        형식:
                        유튜브 검색어: [주제 키워드]
                        이미지 검색어: [주제 키워드]
                        [참고자료]
                        {ref_text}
                        """
                        res_media = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_media)
                        st.session_state['media_info'] = res_media.text
                        st.session_state['grading_result'] = None
                        st.session_state['current_mode'] = "일반"

                        st.success("분석 및 문제 생성이 완료되었습니다.")
                    except Exception as e:
                        st.error(f"오류가 발생했습니다: {e}")
            else:
                st.warning("참고자료와 수행평가 안내지를 모두 입력해 주세요.")

    elif mode == "암기 시험":
        st.subheader("🧠 암기할 자료 첨부 및 과목 선택")
        
        subject = st.selectbox("📌 과목을 선택하세요", ["과학/수학 (공식 암기)", "영어 (지문 암기)", "역사 (단어 및 개념 암기)", "기타 일반 암기"])
        
        eng_mode = None
        if subject == "영어 (지문 암기)":
            eng_mode = st.radio("테스트 방식을 선택하세요", ["한글을 영어로 옮겨 적기 (영작)", "음성으로 말하기 테스트 (Speaking)"])

        uploaded_img = st.file_uploader("암기할 내용이 담긴 사진 업로드 (.jpg, .jpeg, .png)", type=["jpg", "jpeg", "png"])
        memo_text = st.text_area("또는 암기할 텍스트를 직접 입력하세요", height=150, placeholder="사진을 올리지 않고 텍스트로 바로 입력할 수도 있습니다.")
        
        if st.button("암기 테스트 문제 생성"):
            if uploaded_img is not None or memo_text.strip():
                with st.spinner("암기 테스트를 만드는 중입니다..."):
                    try:
                        contents = []
                        
                        if subject == "과학/수학 (공식 암기)":
                            prompt_memo = """
                            제공된 이미지나 텍스트 내용을 바탕으로 '과학/수학 공식 암기 테스트'를 만들어주세요.
                            [조건]
                            1. 핵심 공식, 수식, 기호, 조건 등을 정확히 알고 있는지 검증하는 문제(빈칸 채우기, 공식 완성하기 등)를 작성하세요.
                            2. 화면에 정답은 절대 미리 출력하지 마세요.
                            """
                        elif subject == "역사 (단어 및 개념 암기)":
                            prompt_memo = """
                            제공된 이미지나 텍스트 내용을 바탕으로 '역사 암기 테스트'를 만들어주세요.
                            [조건]
                            1. 주요 인물, 사건, 연도, 기구 이름 등을 묻는 '단어 테스트'와 사건의 배경, 원인, 영향, 과정 등을 묻는 '개념/서술형 테스트'를 섞어서 출제하세요.
                            2. 화면에 정답은 절대 미리 출력하지 마세요.
                            """
                        elif subject == "영어 (지문 암기)" and eng_mode == "한글을 영어로 옮겨 적기 (영작)":
                            prompt_memo = """
                            제공된 영어 지문을 바탕으로 '영작 암기 테스트'를 만들어주세요.
                            [조건]
                            1. 원본 지문의 각 문장에 대한 한글 해석을 제시하고, 이를 올바른 영문장으로 작성하도록 유도하는 문제를 만드세요.
                            2. 화면에 정답(영문)은 절대 미리 출력하지 마세요.
                            """
                        elif subject == "영어 (지문 암기)" and eng_mode == "음성으로 말하기 테스트 (Speaking)":
                            prompt_memo = """
                            제공된 영어 지문을 바탕으로 '말하기(Speaking) 암기 테스트' 안내문을 생성해주세요.
                            [조건]
                            1. 지문의 전체적인 한글 개요 또는 첫 문장의 일부만 힌트로 제시하세요.
                            2. "아래 마이크 버튼을 누르고 지문을 처음부터 끝까지 영어로 암기하여 말해보세요."라는 안내문구를 출력하세요.
                            3. 화면에 원본 영어 지문 전체는 절대 미리 출력하지 마세요.
                            """
                        else:
                            prompt_memo = """
                            제공된 이미지나 텍스트 내용을 바탕으로 '암기 확인용 테스트'를 만들어주세요.
                            [조건]
                            1. 사용자가 직접 답을 입력하고 맞출 수 있도록 '문제(빈칸 뚫기 또는 단답형)'만 출력하세요.
                            2. 화면에 정답은 절대 미리 출력하지 마세요.
                            """

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
                        st.success("암기 테스트 문제가 생성되었습니다.")
                    except Exception as e:
                        st.error(f"오류가 발생했습니다: {e}")
            else:
                st.warning("암기할 사진을 업로드하거나 텍스트를 입력해 주세요.")

    # --- 하단 결과 출력부 ---
    if st.session_state.get('current_mode') == "일반" and 'result_tips' in st.session_state:
        st.divider()
        tab1, tab2, tab3 = st.tabs(["💡 평가 팁 및 개념", "✍️ 서술형 실전 연습", "🎥 참고 영상 및 사진"])

        with tab1:
            st.markdown(st.session_state['result_tips'])

        with tab2:
            st.subheader("📝 서술형 연습 문제")
            st.info(st.session_state.get('practice_question', ''))
            user_ans = st.text_area("답안 작성", height=150)
            
            if st.button("AI 채점 및 피드백 받기"):
                if user_ans.strip():
                    with st.spinner("채점 중입니다..."):
                        prompt_grade = f"""
                        [출제 문제] {st.session_state.get('practice_question', '')}
                        [사용자 답안] {user_ans}
                        사용자의 답안을 평가해 주세요:
                        1. 채점 점수 (100점 만점)
                        2. 잘된 점 및 보완점 (감점 요인)
                        3. 추가 암기 개념
                        """
                        res_grade = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_grade)
                        st.session_state['grading_result'] = res_grade.text
                else:
                    st.warning("답안을 입력해 주세요.")
                    
            if st.session_state.get('grading_result'):
                st.subheader("📊 AI 채점 결과")
                st.markdown(st.session_state['grading_result'])

        with tab3:
            st.subheader("🔍 추천 학습 자료")
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

    elif st.session_state.get('current_mode') == "암기" and 'memo_test_q' in st.session_state:
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
            user_memo_ans = st.text_area("위 문제에 대한 정답을 작성해 보세요", height=150)
        
        if st.button("암기 답안 제출 및 채점하기"):
            if (is_speaking_mode and user_audio is not None) or (not is_speaking_mode and user_memo_ans.strip()):
                with st.spinner("작성/녹음한 답안을 원본 자료와 비교하여 채점 중입니다..."):
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
                            [출제 문제]
                            {st.session_state['memo_test_q']}
                            
                            사용자가 원본 영어 지문을 직접 입으로 말해서 녹음한 음성 파일입니다.
                            원본 자료(이미지/텍스트)의 내용과 사용자가 직접 말한 음성을 대조하여 채점해 주세요.
                            
                            [채점 기준]
                            1. **성공 여부 판단**: 원본 지문과 사용자가 말한 내용이 일치하면 '성공'이라고 명확히 알려주세요.
                            2. **음성 인식 텍스트(STT)**: 사용자가 음성으로 말한 내용을 텍스트로 적어 보여주세요.
                            3. **틀린 부분 및 교정**: 원본 지문과 비교했을 때 누락된 단어, 틀린 단어, 문법/발음 오류가 있다면 명확히 짚어주고 원본 지문을 제시해 주세요.
                            """
                        else:
                            prompt_memo_grade = f"""
                            [출제된 암기 문제]
                            {st.session_state['memo_test_q']}
                            
                            [사용자가 작성한 답안]
                            {user_memo_ans}
                            
                            제공된 원본 자료(이미지/텍스트)를 기준으로 사용자의 답안을 채점해 주세요.
                            [조건]
                            1. 맞은 문제와 틀린 문제를 구별하여 알려주세요.
                            2. 틀린 문제가 있다면 어느 부분이 틀렸는지 명확히 짚어주고, 올바른 정답을 알려주세요.
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
            st.subheader("📊 암기 테스트 채점 결과")
            st.markdown(st.session_state['memo_grading_result'])

else:
    st.info("왼쪽 사이드바에 Gemini API 키를 입력한 후 사용해 주세요.")
