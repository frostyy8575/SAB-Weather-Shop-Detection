# SAB Detector

A small Python OCR-based detector for the Roblox **Spin a Baddie** shop and weather.

It takes screenshots of the visible UI, reads text with Tesseract OCR, scrolls the shop with `pyautogui`, and sends updates to a Discord webhook when it finds target weather or target dice in stock.

This project does **not** use Roblox executors (Not bannable), memory editing, or game exploits. It only works from what is visible on screen.

## What It Does

- Scans the visible shop for specific target dice
- Checks the visible weather area for target weather
- Scrolls through the shop automatically
- Sends a Discord message with the detected weather and in-stock target dice
- Saves debug screenshots to help troubleshoot OCR problems

## Features

- OCR-based detection using Tesseract
- Strict dice detection designed to prefer false negatives over false positives
- Broad `NO STOCK` filtering
- Weather checks during the scan
- Optional debug images for card crops and weather crops
- Discord webhook notifications
- Color detection system as a backup to detect when an item is in stock or not.

## Requirements

- Windows
- Python 3.9+ recommended
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- Roblox open on screen with the shop/weather UI visible

Python packages used by the project:

- `requests`
- `pytesseract`
- `pyautogui`
- `mss`
- `Pillow`
- `python-dotenv`

## Install Dependencies

Create and activate a virtual environment if you want to keep the install isolated, then install the packages:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install requests pytesseract pyautogui mss pillow python-dotenv
```

## Install and Configure Tesseract OCR

1. Install Tesseract OCR for Windows.
2. The script currently expects Tesseract here:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

3. If your install path is different, update this line in `sab_detector.py`:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Configure `.env`

Create a `.env` file in the repo root:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_here
```

The detector loads this value at startup and uses it for Discord notifications. This allows the user to not leak their discord webhook url to others.

## Run the Detector

From the repo root:

```powershell
python sab_detector.py
```

Before running:

- Open Roblox
- Open the Spin a Baddie shop
- Make sure the weather area is visible
- Keep the game window in a stable position while the detector runs

## Notes

- OCR is imperfect. Always double-check detections before acting on them.
- Screen position, UI scale, lighting, overlap, and motion can all affect OCR results.
- This script is intentionally strict, so it may miss some real items instead of risking false reports.
- Debug PNGs can help tune regions and OCR behavior if detections are missed.
- Crops are tuned so the detector starts at Kraken Dice and ends at Baddie Dice. Tune CARD_STEP_SCANS & RETURN_SCROLL_AMOUNT to start at a higher position or lower position item.

## Security Warning

- Do **not** commit `.env`.
- Do **not** commit real Discord webhook URLs.
- If a webhook URL is exposed, rotate it in Discord and replace it.

