import streamlit as st
import time
import os
import requests
from docx import Document
from utils.file_processor import extract_text  # utils/file_processor.py に実装済み

# -------------------------------
# デバッグ用：secretsの読み込み確認
# 本番環境ではAPIキーを画面表示しないでください。
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
        time.sleep(0.01)  # UI更新用（処理時間に応じて調整してください）
        progress_bar.progress(percent)
    
    # 5. Google Generative Language API (Gemini) への呼び出し
    # 適切なプロンプトに書き換えています。
    prompt = (
        "以下の文章は方言が含まれています。文章全体の意味を十分に考慮し、"
        "すべての方言表現を標準語に変換してください。変換後の文章のみを出力してください。\n\n"
        "テキスト:\n" + original_text
    )
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    # secretsからAPIキーを取得し、URLに付与
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    st.write("GeminiAPI にリクエストを送信中...")
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生
        response_json = response.json()
        
        # JSONレスポンスを折り畳みで表示
        with st.expander("APIレスポンス (JSON)"):
            st.json(response_json, expanded=False)
        
        # レスポンス例: {"contents": [{"parts": [{"text": "変換されたテキスト"}]}]}
        try:
            converted_text = response_json["contents"][0]["parts"][0]["text"]
        except (KeyError, IndexError):
            st.warning("レスポンス構造が想定と異なります。")
            converted_text = ""
            st.write("レスポンス内容:", response_json)
        
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
                # シンプルなPDF生成（必要に応じてreportlab等を使用してください）
                with open(output_filename, "wb") as f:
                    f.write(converted_text.encode("utf-8"))
                with open(output_filename, "rb") as f:
                    st.download_button("ダウンロード PDF", f, file_name=output_filename)
                os.remove(output_filename)
            except Exception as e:
                st.error("PDFファイルの生成に失敗しました：" + str(e))
else:
    st.write("ファイルをアップロードしてください。")
