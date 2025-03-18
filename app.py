import streamlit as st
import streamlit.components.v1 as components
import time
import os
import asyncio
import httpx
import requests
import json
from docx import Document
from utils.file_processor import extract_text
from google.cloud import storage
from google.oauth2 import service_account
from PyPDF2 import PdfReader
import io
import difflib

# ワイドモードで起動
st.set_page_config(layout="wide")

# グローバルCSS（Robotoフォント採用、背景は白、モノクロ、テキストは自動改行）
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

# サイドバーにファイルアップロード、要約生成、ファイル出力、出力形式選択、GCS接続、PDF検索クエリ
sidebar_file = st.sidebar.file_uploader("WordまたはPDFファイルをアップロードしてください", type=["docx", "pdf"])
if sidebar_file:
    st.sidebar.write("ファイルがアップロードされました。")
generate_summary_btn = st.sidebar.button("要約を生成")
output_btn = st.sidebar.button("ファイルを出力")
output_format = st.sidebar.radio("出力形式を選択してください", ("Word", "PDF"))
connect_gcs_btn = st.sidebar.button("GCSに接続")
search_query = st.sidebar.text_input("議事録検索クエリ (PDF)", value="")

st.title("LingoBridge - 方言→標準語変換＆要約アプリ")

# --- GCS 接続（サービスアカウントの JSON キーを利用） ---
if connect_gcs_btn:
    st.sidebar.write("GCSに接続しています...")
    try:
        # JSONキーは secrets から読み込み
        json_key_str = st.secrets["google_cloud"]["json_key"]
        json_key = json.loads(json_key_str)
        credentials = service_account.Credentials.from_service_account_info(json_key)
        client = storage.Client(credentials=credentials, project=json_key["project_id"])
        buckets = list(client.list_buckets())
        if buckets:
            st.sidebar.write("取得したバケット一覧:")
            for b in buckets:
                st.sidebar.write(" - ", b.name)
        else:
            st.sidebar.write("バケットがありません。")
    except Exception as e:
        st.sidebar.error(f"GCS接続に失敗しました: {e}")

# --- RAG：GCS から議事録PDFを読み込み、検索機能 ---
def load_all_meeting_minutes_gcs(bucket_name, prefix=""):
    """指定バケット内のPDFを読み込み、ファイル名→テキストの辞書を返す"""
    meeting_data = {}
    try:
        # 認証情報は同じく secrets を利用
        json_key_str = st.secrets["google_cloud"]["json_key"]
        json_key = json.loads(json_key_str)
        credentials = service_account.Credentials.from_service_account_info(json_key)
        client = storage.Client(credentials=credentials, project=json_key["project_id"])
        blobs = client.list_blobs(bucket_name, prefix=prefix)
        for blob in blobs:
            if blob.name.lower().endswith(".pdf"):
                pdf_bytes = blob.download_as_bytes()
                pdf_stream = io.BytesIO(pdf_bytes)
                try:
                    reader = PdfReader(pdf_stream)
                    text = ""
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    meeting_data[blob.name] = text
                except Exception as e:
                    st.write(f"PDF読み込み失敗: {blob.name}, {e}")
    except Exception as e:
        st.error(f"GCSからのPDF読み込みに失敗しました: {e}")
    return meeting_data

def search_meeting_minutes(meeting_data, query):
    """議事録データから検索クエリに一致する行を抽出"""
    results = []
    if not query:
        return results
    for filename, text in meeting_data.items():
        lines = text.splitlines()
        matched_lines = [line.strip() for line in lines if query.lower() in line.lower()]
        if matched_lines:
            results.append((filename, matched_lines))
    return results

if search_query:
    st.sidebar.markdown("### 議事録検索結果")
    # 例: バケット名とプレフィックスを指定（適宜変更してください）
    bucket_name = st.sidebar.text_input("検索するバケット名", value="storage1155")
    gcs_prefix = st.sidebar.text_input("検索するフォルダ (prefix)", value="meeting_minutes/")
    meeting_minutes_data = load_all_meeting_minutes_gcs(bucket_name, gcs_prefix)
    if meeting_minutes_data:
        res = search_meeting_minutes(meeting_minutes_data, search_query)
        if res:
            for fname, lines in res:
                st.sidebar.write(f"**{fname}**")
                for ln in lines:
                    st.sidebar.write(f"- {ln}")
        else:
            st.sidebar.write("該当する内容が見つかりませんでした。")
    else:
        st.sidebar.write("議事録PDFがロードされていません。")

# --- 既存の変換処理部分 ---
if sidebar_file is not None:
    try:
        original_text = extract_text(sidebar_file)
        st.write("テキスト抽出完了。")
    except Exception as e:
        st.error(f"ファイルからテキストを抽出できませんでした: {e}")
        original_text = ""
    
    progress_bar = st.progress(0)
    progress_text = st.empty()
    for percent in range(1, 101):
        time.sleep(0.01)
        progress_bar.progress(percent)
        progress_text.text(f"{percent}%")
    
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    max_attempts = 3
    timeout_seconds = 30

    async def fetch_api(payload: dict) -> dict:
        attempt = 1
        while attempt <= max_attempts:
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    response = await client.post(api_url, headers=headers, json=payload)
                    response.raise_for_status()
                    return response.json()
            except httpx.TimeoutException:
                st.warning(f"非同期タイムアウト：{attempt}回目のリトライ中...")
                if attempt == max_attempts:
                    st.error("リクエストがタイムアウトしました。")
                    return {}
                else:
                    await asyncio.sleep(5)
                    attempt += 1
            except httpx.RequestError as re:
                st.error("非同期接続エラーが発生しました。")
                st.error(str(re))
                return {}
            except Exception as e:
                st.error("非同期処理で予期しないエラー：" + str(e))
                return {}
        return {}

    convert_prompt = (
        "以下の文章は方言が含まれています。文章全体の意味を十分に考慮し、すべての方言表現を標準語に変換してください。変換後の文章のみを出力してください。\n\n"
        "テキスト:\n" + original_text
    )
    convert_payload = {"contents": [{"parts": [{"text": convert_prompt}]}]}
    st.write("GeminiAPI に変換処理のリクエストを送信中...")
    with st.spinner("GeminiAPIで変換中..."):
        response_json = asyncio.run(fetch_api(convert_payload))
        st.expander("変換処理 APIレスポンス (JSON)", expanded=False).write(response_json)
    
    if "candidates" in response_json and len(response_json["candidates"]) > 0:
        try:
            converted_text = response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            st.error("レスポンス構造が想定と異なります。")
            st.write("レスポンス内容:", response_json)
            converted_text = ""
    elif "text" in response_json:
        converted_text = response_json["text"].strip()
    else:
        st.error("変換処理 APIレスポンスに想定するキーが存在しません。")
        st.write("レスポンス内容:", response_json)
        converted_text = ""
    st.write("変換完了。")
    
    if converted_text:
        tabs = st.tabs(["元のテキスト", "変換後のテキスト"])
        with tabs[0]:
            html_original = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <style>
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
                  width: 90%;
                  height: 450px;
                  white-space: pre-wrap;
                }}
                .header {{
                  margin-top: 0;
                  border-bottom: 2px solid #000000;
                  padding-bottom: 5px;
                }}
              </style>
            </head>
            <body>
              <div class="text-window">
                <h2 class="header">元のテキスト</h2>
                <p>{original_text}</p>
              </div>
            </body>
            </html>
            """
            components.html(html_original, height=470, scrolling=True)
        
        with tabs[1]:
            html_converted = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <style>
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
                  width: 90%;
                  height: 450px;
                  white-space: pre-wrap;
                }}
                .header {{
                  margin-top: 0;
                  border-bottom: 2px solid #000000;
                  padding-bottom: 5px;
                }}
              </style>
            </head>
            <body>
              <div class="text-window">
                <h2 class="header">変換後のテキスト</h2>
                <p>{converted_text}</p>
              </div>
            </body>
            </html>
            """
            components.html(html_converted, height=470, scrolling=True)
    
    if output_btn:
        if output_format == "Word":
            try:
                doc = Document()
                doc.add_paragraph(converted_text)
                output_filename = "converted.docx"
                doc.save(output_filename)
                with open(output_filename, "rb") as f:
                    st.sidebar.download_button("ダウンロード Word", f, file_name=output_filename)
                os.remove(output_filename)
            except Exception as e:
                st.error("Wordファイルの生成に失敗しました：" + str(e))
        else:
            try:
                output_filename = "converted.pdf"
                with open(output_filename, "wb") as f:
                    f.write(converted_text.encode("utf-8"))
                with open(output_filename, "rb") as f:
                    st.sidebar.download_button("ダウンロード PDF", f, file_name=output_filename)
                os.remove(output_filename)
            except Exception as e:
                st.error("PDFファイルの生成に失敗しました：" + str(e))
    
    summary_text = ""
    if generate_summary_btn:
        summarize_prompt = (
            "以下は町議会の議事録です。議事録を要約する際、まず議題ごとにセクションに分割し、"
            "各セクション内で発言者ごとの情報を整理してください。具体的には、主要な議題、決定事項、"
            "重要な発言、及び今後のアクションアイテムを抽出し、誰がどのような意見を述べたのかを明確にしてください。"
            "\n\n議事録全文:\n" + original_text
        )
        summary_payload = {"contents": [{"parts": [{"text": summarize_prompt}]}]}
        with st.spinner("GeminiAPIで要約生成中..."):
            summary_progress_bar = st.progress(0)
            summary_progress_text = st.empty()
            for percent in range(1, 101):
                time.sleep(0.005)
                summary_progress_bar.progress(percent)
                summary_progress_text.text(f"{percent}%")
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
        
        if summary_text:
            st.markdown("## 要約結果")
            st.markdown(summary_text)
else:
    st.write("ファイルをアップロードしてください。")
