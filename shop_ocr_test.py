import pytesseract
import mss
from PIL import Image, ImageEnhance

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Crop only the shop UI area
SHOP_REGION = {
    "left": 600,
    "top": 160,
    "width": 950,
    "height": 700
}

with mss.mss() as sct:
    screenshot = sct.grab(SHOP_REGION)
    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

# Make text easier to read
# img = img.convert("L")  # grayscale
# img = ImageEnhance.Contrast(img).enhance(2.0)

# Save debug image so you can see exactly what OCR is reading
img.save("shop_crop_debug.png")

text = pytesseract.image_to_string(img, config="--psm 6")

print("OCR found in shop crop:")
print(text)
print("\nSaved crop as shop_crop_debug.png")