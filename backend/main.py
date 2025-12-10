from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pypdf import PdfReader, PdfWriter
import os
import uuid
import shutil
import zipfile
from pathlib import Path

app = FastAPI(title="PDF Splitter API")

# フロントエンドのパス
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 一時ファイル保存ディレクトリ
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.post("/api/split")
async def split_pdf(file: UploadFile = File(...)):
    """PDFを1ページずつに分割してZIPで返す"""

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDFファイルのみ対応しています")

    # ユニークなセッションIDを生成
    session_id = str(uuid.uuid4())
    session_upload_dir = UPLOAD_DIR / session_id
    session_output_dir = OUTPUT_DIR / session_id
    session_upload_dir.mkdir(exist_ok=True)
    session_output_dir.mkdir(exist_ok=True)

    try:
        # アップロードされたファイルを保存
        input_path = session_upload_dir / file.filename
        with open(input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # PDFを読み込んで分割
        reader = PdfReader(input_path)
        total_pages = len(reader.pages)

        if total_pages == 0:
            raise HTTPException(status_code=400, detail="PDFにページがありません")

        base_name = Path(file.filename).stem
        split_files = []

        # 1ページずつ分割
        for i, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)

            output_filename = f"{base_name}_page{i:03d}.pdf"
            output_path = session_output_dir / output_filename

            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            split_files.append(output_filename)

        # ZIPファイルを作成
        zip_filename = f"{base_name}_split.zip"
        zip_path = session_output_dir / zip_filename

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for split_file in split_files:
                file_path = session_output_dir / split_file
                zipf.write(file_path, split_file)

        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "total_pages": total_pages,
            "files": split_files,
            "zip_filename": zip_filename
        })

    except Exception as e:
        # エラー時はクリーンアップ
        shutil.rmtree(session_upload_dir, ignore_errors=True)
        shutil.rmtree(session_output_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str):
    """分割されたファイルまたはZIPをダウンロード"""

    file_path = OUTPUT_DIR / session_id / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.delete("/api/cleanup/{session_id}")
async def cleanup(session_id: str):
    """セッションの一時ファイルを削除"""

    session_upload_dir = UPLOAD_DIR / session_id
    session_output_dir = OUTPUT_DIR / session_id

    shutil.rmtree(session_upload_dir, ignore_errors=True)
    shutil.rmtree(session_output_dir, ignore_errors=True)

    return {"success": True, "message": "クリーンアップ完了"}


@app.get("/api/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """フロントエンドを配信"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
