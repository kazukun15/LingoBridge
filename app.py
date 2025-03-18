import streamlit as st
import time
import os
import requests
from docx import Document
from utils.file_processor import extract_text  # utils/file_processor.py に実装済み

# ---------------------------------------------
# デバッグ用：シークレットの読み込み確認
# ---------------------------------------------
# もし "GEMINI_API_KEY" が st.secrets に存在すれば値を表示する
# 本番環境では機密情報を画面に表示しないよう注意してください。
if "GEMINI_API_KEY" in st.secrets:
    st.write("【デバッグ表示】GEMINI_API_KEY:", st.secrets["GEMINI_API_KEY"])
else:
    st.error("【デバッグ表示】'GEMINI_API_KEY' が secrets に存在しません。")

st.title("LingoBridge - 方言→標準語変換アプリ")

# 1. ファイルアップロード
uploaded_file = st.file_uploader("WordまたはPDFファイルをアップロードしてください", type=["docx", "pdf"])

if uploaded_file is not None:
    st.write("ファイルをアップロードしました。")

    # 2. ファイルからテキスト抽出
    try:
        original_text = extract_text(uploaded_file)
        st.write("テキスト抽出完了。")
    except Exception as e:
        st.error(f"ファイルからテキストを抽出できませんでした: {e}")
        original_text = ""

    # 3. 2画面表示（左：元のテキスト、右：変換後のテキスト）
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("元のテキスト")
        st.text_area("内容", original_text, height=400)

    # 4. プログレスバー（変換処理の進捗をシミュレーション）
    progress_bar = st.progress(0)
    for percent in range(1, 101):
        time.sleep(0.01)
        progress_bar.progress(percent)

    # 5. GeminiAPI の呼び出し
    # secrets からキーを読み込み
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    # 実際のAPIエンドポイントに置き換えてください
    api_url = "https://api.gemini.example.com/convert"

    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": "models/gemini-2.0-flash",
        "text": original_text
    }

    st.write("GeminiAPI にリクエストを送信中...")

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生
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

    # 6. 出力形式の選択とファイルダウンロード機能
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
                # シンプルなPDF生成（実際は reportlab 等のライブラリを用いると良い）
                with open(output_filename, "wb") as f:
                    f.write(converted_text.encode("utf-8"))
                with open(output_filename, "rb") as f:
                    st.download_button("ダウンロード PDF", f, file_name=output_filename)
                os.remove(output_filename)
            except Exception as e:
                st.error("PDFファイルの生成に失敗しました：" + str(e))
else:
    st.write("ファイルをアップロードしてください。")
