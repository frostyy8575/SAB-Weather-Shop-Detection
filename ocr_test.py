import pytesseract
import mss
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

with mss.mss() as sct:
    monitor = sct.monitors[1]
    screenshot = sct.grab(monitor)
    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

text = pytesseract.image_to_string(img)

print("OCR found:")
print(text)