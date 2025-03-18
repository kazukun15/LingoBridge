import streamlit as st
import time
import os
import requests
from docx import Document
from utils.file_processor import extract_text  # utils/file_processor.py に実装済み

# デバッグ用：アプリ開始を明示
st.write("アプリが起動しました。")

st.title("LingoBridge - 方言→標準語変換アプリ")

# 1. ファイルアップロード
uploaded_file = st.file_uploader("WordまたはPDFファイルをアップロードしてください", type=["docx", "pdf"])
if uploaded_file is not None:
    st.write("ファイルをアップロードしました。")
    try:
        # utils/file_processor.py の extract_text を利用してテキスト抽出
        original_text = extract_text(uploaded_file)
        st.write("テキスト抽出完了。")
    except Exception as e:
        st.error(f"ファイルからテキストを抽出できませんでした: {e}")
        original_text = ""
    
    # 2. 2画面表示（左：元のテキスト、右：変換後のテキスト）
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("元のテキスト")
        st.text_area("内容", original_text, height=400)
    
    # 3. プログレスバー（変換処理の進捗をシミュレーション）
    progress_bar = st.progress(0)
    for percent in range(1, 101):
        time.sleep(0.01)  # この処理が重い場合は数値を調整してください
        progress_bar.progress(percent)
    
    # 4. GeminiAPI の呼び出し
    api_key = st.secrets["GEMINI_API_KEY"]
    api_url = "https://api.gemini.example.com/convert"  # ※実際のAPIエンドポイントに置き換えてください
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": "models/gemini-2.0-flash",
        "text": original_text
    }
    
    st.write("GeminiAPI にリクエストを送信中...")
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生させる
        converted_text = response.json().get("converted_text", "")
        st.write("変換完了。")
    except requests.exceptions.ConnectionError as ce:
        st.error("接続エラー：APIエンドポイントに到達できません。")
        st.error(str(ce))
        converted_text = ""
    except requests.exceptions.Timeout as te:
        st.error("リクエストがタイムアウトしました。")
        st.error(str(te))
        converted_text = ""
    except requests.exceptions.HTTPError as he:
        st.error("HTTPエラーが発生しました：" + str(he))
        converted_text = ""
    except Exception as e:
        st.error("予期しないエラーが発生しました：" + str(e))
        converted_text = ""
    
    with col2:
        st.subheader("変換後のテキスト")
        st.text_area("内容", converted_text, height=400)
    
    # 5. 出力形式の選択とファイルダウンロード機能
    output_format = st.radio("出力形式を選択してください", ("Word", "PDF"))
    if st.button("ファイルを出力"):
        if output_format == "Word":
            try:
                doc = Document()
                doc.add_paragraph(converted_text)
                output_filename = "converted.docx"
                doc.save(output_filename)
                with open(output_filename, "rb") as f:
                    st.download_button("ダウンロード Word", f, file_name=output_filename)
                os.remove(output_filename)
            except Exception as e:
                st.error("Wordファイルの生成に失敗しました：" + str(e))
        else:
            try:
                output_filename = "converted.pdf"
                # シンプルなPDF生成（実際は reportlab などを利用すると良いでしょう）
                with open(output_filename, "wb") as f:
                    f.write(converted_text.encode("utf-8"))
                with open(output_filename, "rb") as f:
                    st.download_button("ダウンロード PDF", f, file_name=output_filename)
                os.remove(output_filename)
            except Exception as e:
                st.error("PDFファイルの生成に失敗しました：" + str(e))
else:
    st.write("ファイルをアップロードしてください。")
