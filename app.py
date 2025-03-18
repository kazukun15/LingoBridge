import streamlit as st
import streamlit.components.v1 as components
import time
import os
import requests
from docx import Document
from utils.file_processor import extract_text

# グローバルCSS（Robotoフォント採用、背景は白、モノクロで統一）
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
<style>
body {
    background-color: #FFFFFF;
    font-family: 'Roboto', sans-serif;
    color: #000000;
}
h1, h2, h3 {
    color: #000000;
}
div.stButton > button, div.stDownloadButton > button {
    background-color: #000000 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600;
    padding: 10px 20px !important;
}
.stTextArea label, .stTextArea textarea {
    color: #000000;
    background-color: #FFFFFF;
    border: 1px solid #000000;
}
.stMarkdown {
    color: #000000;
}
</style>
""", unsafe_allow_html=True)

# サイドバーにファイルアップロード
sidebar_file = st.sidebar.file_uploader("WordまたはPDFファイルをアップロードしてください", type=["docx", "pdf"])
if sidebar_file:
    st.sidebar.write("ファイルがアップロードされました。")

# デバッグ用：secretsの読み込み確認（本番環境では非表示推奨）
if "GEMINI_API_KEY" in st.secrets:
    st.write("【デバッグ表示】GEMINI_API_KEY:", st.secrets["GEMINI_API_KEY"])
else:
    st.error("【デバッグ表示】'GEMINI_API_KEY' が secrets に存在しません。")

st.title("LingoBridge - 方言→標準語変換＆要約アプリ")

if sidebar_file is not None:
    try:
        original_text = extract_text(sidebar_file)
        st.write("テキスト抽出完了。")
    except Exception as e:
        st.error(f"ファイルからテキストを抽出できませんでした: {e}")
        original_text = ""
    
    # プログレスバー（％表示付き）
    progress_bar = st.progress(0)
    progress_text = st.empty()
    for percent in range(1, 101):
        time.sleep(0.01)
        progress_bar.progress(percent)
        progress_text.text(f"{percent}%")
    
    # 共通のAPI設定
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    max_attempts = 3
    timeout_seconds = 30

    # 方言→標準語変換処理
    convert_prompt = (
        "以下の文章は方言が含まれています。文章全体の意味を十分に考慮し、"
        "すべての方言表現を標準語に変換してください。変換後の文章のみを出力してください。\n\n"
        "テキスト:\n" + original_text
    )
    convert_payload = {
        "contents": [
            {
                "parts": [
                    {"text": convert_prompt}
                ]
            }
        ]
    }
    st.write("GeminiAPI に変換処理のリクエストを送信中...")
    converted_text = ""
    with st.spinner("GeminiAPIで変換中..."):
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(api_url, headers=headers, json=convert_payload, timeout=timeout_seconds)
                response.raise_for_status()
                response_json = response.json()
                
                with st.expander("変換処理 APIレスポンス (JSON)"):
                    st.json(response_json, expanded=False)
                
                if "candidates" in response_json and len(response_json["candidates"]) > 0:
                    try:
                        converted_text = response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    except (KeyError, IndexError):
                        st.error("変換処理レスポンス構造が想定と異なります。")
                        st.write("レスポンス内容:", response_json)
                        converted_text = ""
                elif "text" in response_json:
                    converted_text = response_json["text"].strip()
                else:
                    st.error("変換処理 APIレスポンスに想定するキーが存在しません。")
                    st.write("レスポンス内容:", response_json)
                    converted_text = ""
                st.write("変換完了。")
                break
            except requests.exceptions.Timeout as te:
                st.warning(f"変換処理でタイムアウトが発生しました。{attempt}回目のリトライ中です...")
                if attempt == max_attempts:
                    st.error("変換処理のリクエストがタイムアウトしました。")
                    converted_text = ""
                else:
                    time.sleep(5)
            except requests.exceptions.ConnectionError as ce:
                st.error("変換処理接続エラー：APIエンドポイントに到達できません。")
                st.error(str(ce))
                converted_text = ""
                break
            except requests.exceptions.HTTPError as he:
                st.error("変換処理HTTPエラー：" + str(he))
                converted_text = ""
                break
            except Exception as e:
                st.error("変換処理で予期しないエラーが発生しました：" + str(e))
                converted_text = ""
                break

    # 元のテキストと変換後テキストを横並びに表示（カスタムウィンドウ内、改行反映）
    if converted_text:
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            .container {{
              display: flex;
              flex-direction: row;
              align-items: flex-start;
              gap: 20px;
            }}
            .text-window {{
              background: #FFFFFF;
              border: 2px solid #000000;
              border-radius: 10px;
              padding: 20px;
              color: #000000;
              font-size: 16px;
              line-height: 1.6;
              box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
              overflow: auto;
              width: 48%;
              white-space: pre-wrap;
            }}
            .arrow {{
              font-size: 64px;
              font-weight: bold;
              color: #000000;
              align-self: center;
            }}
            .header {{
              margin-top: 0;
              border-bottom: 2px solid #000000;
              padding-bottom: 5px;
            }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="text-window">
              <h2 class="header">元のテキスト</h2>
              <p>{original_text}</p>
            </div>
            <div class="arrow">⇒</div>
            <div class="text-window">
              <h2 class="header">変換後のテキスト</h2>
              <p>{converted_text}</p>
            </div>
          </div>
        </body>
        </html>
        """
        components.html(html_code, height=600, scrolling=True)
    
    # 出力機能（変換後テキストのダウンロード）
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
                with open(output_filename, "wb") as f:
                    f.write(converted_text.encode("utf-8"))
                with open(output_filename, "rb") as f:
                    st.download_button("ダウンロード PDF", f, file_name=output_filename)
                os.remove(output_filename)
            except Exception as e:
                st.error("PDFファイルの生成に失敗しました：" + str(e))
    
    # 要約機能の実装（発言者整理・セクショニング指示付き）
    summary_text = ""
    if st.button("要約を生成"):
        summarize_prompt = (
            "以下は町議会の議事録です。議事録を要約する際、まず議題ごとにセクションに分割し、"
            "各セクション内で発言者ごとの情報を整理してください。具体的には、主要な議題、決定事項、"
            "重要な発言、及び今後のアクションアイテムを抽出し、誰がどのような意見を述べたのかを明確にしてください。"
            "\n\n議事録全文:\n" + original_text
        )
        summary_payload = {
            "contents": [
                {
                    "parts": [
                        {"text": summarize_prompt}
                    ]
                }
            ]
        }
        with st.spinner("GeminiAPIで要約生成中..."):
            for attempt in range(1, max_attempts + 1):
                try:
                    summary_response = requests.post(api_url, headers=headers, json=summary_payload, timeout=timeout_seconds)
                    summary_response.raise_for_status()
                    summary_json = summary_response.json()
                    
                    with st.expander("要約処理 APIレスポンス (JSON)"):
                        st.json(summary_json, expanded=False)
                    
                    if "candidates" in summary_json and len(summary_json["candidates"]) > 0:
                        try:
                            summary_text = summary_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                        except (KeyError, IndexError):
                            st.error("要約処理レスポンス構造が想定と異なります。")
                            st.write("レスポンス内容:", summary_json)
                            summary_text = ""
                    elif "text" in summary_json:
                        summary_text = summary_json["text"].strip()
                    else:
                        st.error("要約処理 APIレスポンスに想定するキーが存在しません。")
                        st.write("レスポンス内容:", summary_json)
                        summary_text = ""
                    
                    st.success("要約生成完了。")
                    break
                except requests.exceptions.Timeout as te:
                    st.warning(f"要約処理でタイムアウトが発生しました。{attempt}回目のリトライ中です...")
                    if attempt == max_attempts:
                        st.error("要約処理のリクエストがタイムアウトしました。")
                        summary_text = ""
                    else:
                        time.sleep(5)
                except requests.exceptions.ConnectionError as ce:
                    st.error("要約処理接続エラー：APIエンドポイントに到達できません。")
                    st.error(str(ce))
                    summary_text = ""
                    break
                except requests.exceptions.HTTPError as he:
                    st.error("要約処理HTTPエラー：" + str(he))
                    summary_text = ""
                    break
                except Exception as e:
                    st.error("要約処理で予期しないエラーが発生しました：" + str(e))
                    summary_text = ""
                    break
        
        # 要約結果をマークダウン形式で表示
        if summary_text:
            st.markdown("## 要約結果")
            st.markdown(summary_text)
else:
    st.write("ファイルをアップロードしてください。")
