from fastapi import FastAPI, File, UploadFile,Form
from fastapi.responses import StreamingResponse
from rembg import remove
from PIL import Image

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PHOTO_SIZES={
    "passport": (413, 531), 
    "visa": (413, 531),
    "square": (500, 500)
}

@app.get("/")
def health():
    return {"status": "running"}

@app.post("/remove-bg")
async def remove_bg(file: UploadFile = File(...)):
    input_bytes = await file.read()

    output_bytes = remove(input_bytes)

    return StreamingResponse(
        io.BytesIO(output_bytes),
        media_type="image/png"
    )

@app.post("/generate-a4")
async def generate_a4(
    file: UploadFile = File(...),
    copies: int = Form(...),
    size: str = Form(...),
    bg_color: str = Form("white"),   
    bw: bool = Form(False)           
):
    input_bytes = await file.read()

    output_bytes = remove(input_bytes)
    target_w, target_h = PHOTO_SIZES[size]

    img = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

    img = fit_image(img, target_w, target_h)


    img = apply_background(img, bg_color)

    if bw:
        img = apply_bw(img)

    if size not in PHOTO_SIZES:
        size = "passport"

    
    img = fit_image(img, target_w, target_h)

    pdf_bytes = io.BytesIO()
    c = canvas.Canvas(pdf_bytes, pagesize=A4)

    
    img_rgb = img.convert("RGB")

    
    img_reader = ImageReader(img_rgb)

    
    photo_w_mm = 35
    photo_h_mm = 45

    margin_mm = 10

    x_mm = margin_mm
    y_mm = 297 - margin_mm - photo_h_mm  

    for _ in range(copies):
        if x_mm + photo_w_mm > 210:  
            x_mm = margin_mm
            y_mm -= (photo_h_mm + margin_mm)

        if y_mm < 0:
            break

        c.drawImage(
            img_reader,   
            x_mm * mm,
            y_mm * mm,
            width=photo_w_mm * mm,
            height=photo_h_mm * mm
        )

        x_mm += photo_w_mm + margin_mm

    c.save()
    pdf_bytes.seek(0)

    return StreamingResponse(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=photos.pdf"}
    )
    
def fit_image(img, target_w, target_h):
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        
        new_height = target_h
        new_width = int(new_height * img_ratio)
    else:
       
        new_width = target_w
        new_height = int(new_width / img_ratio)

    img = img.resize((new_width, new_height))

    
    left = (new_width - target_w) // 2
    top = (new_height - target_h) // 2

    return img.crop((left, top, left + target_w, top + target_h))


def apply_background(img, color="white"):
    if color == "blue":
        bg = Image.new("RGBA", img.size, (67, 142, 219, 255))  
    else:
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255)) 

    bg.paste(img, (0, 0), img)
    return bg.convert("RGB")

def apply_bw(img):
    return img.convert("L").convert("RGB")
