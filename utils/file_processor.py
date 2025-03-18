"""
file_processor.py

ファイルからテキストを抽出するためのモジュール。
対応ファイル形式: Word (.docx) と PDF (.pdf)
"""

from docx import Document
import PyPDF2

def extract_text_from_docx(file_obj):
    """
    docxファイルからテキストを抽出する関数。

    Args:
        file_obj: Wordファイルのバイナリオブジェクト

    Returns:
        抽出されたテキスト (str)
    """
    try:
        doc = Document(file_obj)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        raise ValueError("Wordファイルからのテキスト抽出に失敗しました。") from e

def extract_text_from_pdf(file_obj):
    """
    PDFファイルからテキストを抽出する関数。

    Args:
        file_obj: PDFファイルのバイナリオブジェクト

    Returns:
        抽出されたテキスト (str)
    """
    try:
        pdf_reader = PyPDF2.PdfReader(file_obj)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError("PDFファイルからのテキスト抽出に失敗しました。") from e

def extract_text(file_obj):
    """
    アップロードされたファイルの拡張子を確認し、対応するテキスト抽出関数を呼び出す関数。

    Args:
        file_obj: アップロードされたファイルオブジェクト

    Returns:
        抽出されたテキスト (str)
    """
    filename = file_obj.name.lower()
    if filename.endswith(".docx"):
        return extract_text_from_docx(file_obj)
    elif filename.endswith(".pdf"):
        return extract_text_from_pdf(file_obj)
    else:
        raise ValueError("サポートされていないファイル形式です。 (.docx, .pdf) を使用してください。")
