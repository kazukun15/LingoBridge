import streamlit as st
from docx import Document
import PyPDF2
import requests

st.title("方言→標準語変換アプリ")

# 2画面表示（左：オリジナル、右：変換結果）
col1, col2 = st.columns(2)

# ファイルアップロード
uploaded_file = st.file_uploader("WordまたはPDFファイルをアップロードしてください", type=["docx", "pdf"])
if uploaded_file is not None:
    # ファイル形式に応じたテキスト抽出
    if uploaded_file.name.endswith(".docx"):
        doc = Document(uploaded_file)
        original_text = "\n".join([para.text for para in doc.paragraphs])
    elif uploaded_file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        original_text = ""
        for page in pdf_reader.pages:
            original_text += page.extract_text()
    
    # 左側に元のテキストを表示
    with col1:
        st.subheader("元のテキスト")
        st.text_area("内容", original_text, height=400)
    
    # プログレスバーの表示（例示）
    progress_bar = st.progress(0)
    for percent in range(1, 101):
        progress_bar.progress(percent)
        # 実際の実装ではGeminiAPIの呼び出し進捗に合わせる
    
    # StreamlitのsecretsからGeminiAPIキーを取得
    api_key = st.secrets["GEMINI_API_KEY"]
    
    # GeminiAPI へのリクエスト例
    api_url = "https://api.gemini.example.com/convert"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": "models/gemini-2.0-flash",
        "text": original_text
    }
    response = requests.post(api_url, headers=headers, json=data)
    if response.status_code == 200:
        converted_text = response.json().get("converted_text")
    else:
        st.error("変換に失敗しました。")
        converted_text = ""
    
    # 右側に変換後のテキストを表示
    with col2:
        st.subheader("変換後のテキスト")
        st.text_area("内容", converted_text, height=400)
    
    # 出力形式選択とダウンロードボタン
    output_format = st.radio("出力形式を選択してください", ("Word", "PDF"))
    if st.button("ファイルを出力"):
        if output_format == "Word":
            # Word形式で出力（python-docx利用例）
            doc_out = Document()
            doc_out.add_paragraph(converted_text)
            doc_out.save("converted.docx")
            with open("converted.docx", "rb") as f:
                st.download_button("ダウンロード Word", f, file_name="converted.docx")
        else:
            # PDF形式で出力（簡易例）
            with open("converted.pdf", "wb") as f:
                f.write(converted_text.encode("utf-8"))
            with open("converted.pdf", "rb") as f:
                st.download_button("ダウンロード PDF", f, file_name="converted.pdf")
