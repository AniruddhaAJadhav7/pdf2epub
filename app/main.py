from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from .converter import pdf_to_epub, docx_to_epub
import io
import pdfplumber
# Rest of your code

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    content = await file.read()
    if file.content_type == "application/pdf":
        epub_file = pdf_to_epub(content, file.filename)
    elif file.content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        epub_file = docx_to_epub(content, file.filename)
    else:
        raise HTTPException(400, detail="Invalid file type. Please upload a PDF or Word file.")
    
    return StreamingResponse(
        io.BytesIO(epub_file.getvalue()),
        media_type="application/epub+zip",
        headers={"Content-Disposition": f"attachment; filename={file.filename.rsplit('.', 1)[0]}.epub"}
    )
