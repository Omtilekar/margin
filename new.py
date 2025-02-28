import io
import os
from typing import List
import pymupdf
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image, ImageOps
import streamlit as st
import zipfile
import requests
import tempfile

app = FastAPI()

def pdf_to_images(pdf_content: bytes) -> List[Image.Image]:
    """Converts a PDF to a list of PIL Images."""
    images = []
    try:
        pdf_document = pymupdf.open(stream=pdf_content, filetype="pdf")
        for page_number in range(pdf_document.page_count):
            page = pdf_document[page_number]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(300 / 72, 300 / 72))  # High resolution
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            images.append(image)
        pdf_document.close()
        return images
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {e}")

def add_margin_to_image(image: Image.Image, left: int, right: int, top: int, bottom: int) -> Image.Image:
    """Adds margins to a PIL Image."""
    width, height = image.size
    new_width = width + left + right
    new_height = height + top + bottom
    new_image = Image.new(image.mode, (new_width, new_height), "white")
    new_image.paste(image, (left, top))
    return new_image

def images_to_pdf(images: List[Image.Image]) -> bytes:
    """Converts a list of PIL Images to a PDF."""
    pdf_bytes = io.BytesIO()
    images[0].save(pdf_bytes, format="PDF", append_images=images[1:], save_all=True)
    pdf_bytes.seek(0)
    return pdf_bytes.read()

@app.post("/pdf_to_pdf_with_margin/")
async def pdf_to_pdf_with_margin(file: UploadFile = File(...), left: int = 50, right: int = 50, top: int = 50, bottom: int = 50):
    """API endpoint to convert PDF to PDF with margin."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")

    try:
        pdf_content = await file.read()
        images = pdf_to_images(pdf_content)
        margined_images = [add_margin_to_image(img, left, right, top, bottom) for img in images]
        pdf_bytes = images_to_pdf(margined_images)
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=margined_pdf.pdf"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

# Streamlit UI
def streamlit_ui():
    st.title("PDF to PDF with Margin")

    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    left_margin = st.number_input("Left Margin (pixels)", min_value=0, value=50)
    right_margin = st.number_input("Right Margin (pixels)", min_value=0, value=50)
    top_margin = st.number_input("Top Margin (pixels)", min_value=0, value=50)
    bottom_margin = st.number_input("Bottom Margin (pixels)", min_value=0, value=50)

    if uploaded_file is not None:
        if st.button("Convert and Download PDF"):
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            response = requests.post(f"http://127.0.0.1:8000/pdf_to_pdf_with_margin/?left={left_margin}&right={right_margin}&top={top_margin}&bottom={bottom_margin}", files=files)
            if response.status_code == 200:
                st.download_button(
                    label="Download PDF with Margins",
                    data=response.content,
                    file_name="margined_pdf.pdf",
                    mime="application/pdf",
                )
            else:
                st.error(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    import uvicorn
    import requests
    import threading

    def run_fastapi():
        uvicorn.run(app, host="127.0.0.1", port=8000)

    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.start()

    streamlit_ui()