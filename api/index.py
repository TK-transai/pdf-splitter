from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pypdf import PdfReader, PdfWriter
import io
import zipfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/split")
async def split_pdf(file: UploadFile = File(...)):
    """PDFを1ページずつに分割してZIPで返す"""

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDFファイルのみ対応しています")

    try:
        content = await file.read()
        pdf_stream = io.BytesIO(content)
        reader = PdfReader(pdf_stream)
        total_pages = len(reader.pages)

        if total_pages == 0:
            raise HTTPException(status_code=400, detail="PDFにページがありません")

        base_name = file.filename.rsplit('.', 1)[0]

        # ZIPをメモリ内で作成
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, page in enumerate(reader.pages, start=1):
                writer = PdfWriter()
                writer.add_page(page)

                pdf_output = io.BytesIO()
                writer.write(pdf_output)
                pdf_output.seek(0)

                filename = f"{base_name}_page{i:03d}.pdf"
                zipf.writestr(filename, pdf_output.getvalue())

        zip_buffer.seek(0)
        zip_filename = f"{base_name}_split.zip"

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"',
                "X-Total-Pages": str(total_pages)
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
