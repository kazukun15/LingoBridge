import streamlit as st
import time
import os
import requests
from docx import Document
from utils.file_processor import extract_text  # utils/file_processor.py に実装済み

# -------------------------------
# デバッグ用：secretsの読み込み確認（本番環境では表示しないこと）
if "GEMINI_API_KEY" in st.secrets:
    st.write("【デバッグ表示】GEMINI_API_KEY:", st.secrets["GEMINI_API_KEY"])
else:
    st.error("【デバッグ表示】'GEMINI_API_KEY' が secrets に存在しません。")

st.title("LingoBridge - 方言→標準語変換＆要約アプリ")

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
    
    # 4. プログレスバー（処理進捗のシミュレーション）
    progress_bar = st.progress(0)
    for percent in range(1, 101):
        time.sleep(0.01)
        progress_bar.progress(percent)
    
    # 共通のAPI設定
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    max_attempts = 3
    timeout_seconds = 30

    # 5. 方言→標準語変換処理
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

    with col2:
        st.subheader("変換後のテキスト")
        st.text_area("内容", converted_text, height=400)
    
    # 6. 要約機能
    if st.button("要約を生成"):
        summarize_prompt = (
            "町議会の議事録を要約してください。主要な議題、決定事項、重要な発言、"
            "今後のアクションアイテムを含む、読みやすく簡潔な要約を生成してください。\n\n"
            "議事録全文:\n" + original_text
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
        summary_text = ""
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
        
        st.subheader("要約結果")
        st.text_area("内容", summary_text, height=400)
    
    # 7. 出力機能（変換後テキストのダウンロード）
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
else:
    st.write("ファイルをアップロードしてください。")
