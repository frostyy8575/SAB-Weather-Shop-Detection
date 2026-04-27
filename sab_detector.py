import time
import re
from pathlib import Path
import requests
import pytesseract
import pyautogui
import mss
import os
from dotenv import load_dotenv
from PIL import Image, ImageOps

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

SHOP_REGION = {
    "left": 600,
    "top": 120,
    "width": 1050,
    "height": 760
}

WEATHER_REGION = {
    "left": 780,
    "top": 85,
    "width": 760,
    "height": 240
}

SCROLL_STEPS = 65
SCROLL_AMOUNT = -120
RETURN_SCROLL_AMOUNT = 8500
WAIT_AFTER_SCROLL = 0.25
SCAN_EVERY_SECONDS = 30

# Turn this on for one test if a dice gets missed.
# It will create debug_card_step_... PNG files.
SAVE_CARD_DEBUG_IMAGES = True
SAVE_WEATHER_DEBUG_IMAGES = False
CLEAN_DEBUG_IMAGES_ON_START = True
VERBOSE_DETECTION_LOG = True

TARGET_DICE = [
    "Kraken Dice",
    "Seraphic Dice",
    "Galactic Dice",
    "Eldritch Dice",
    "Emperor Dice",
    "Annihilation Dice",
    "Disaster Dice",
    "Impossible Dice",
    "Limbo Dice",
    "Chronos Dice",
    "Yinyang Dice",
    "Yin Yang Dice",
    "Matrix Dice",
    "Uriel Dice",
    "Overlord Dice",
    "Baddies Dice",

    # Testing item
    "Crystallum Dice"
]

DISPLAY_NAME_FIXES = {
    "Yin Yang Dice": "Yinyang Dice"
}

TARGET_WEATHERS = [
    "Solar",
    "Celestial",
    "Void",
    "Charged",
    "Rainy",
    "Cold",
    "Golden",
    "Emerald",
    "Diamond"
]

WEATHER_ALIASES = {
    "Solar": ["solar"],
    "Celestial": ["celestial"],
    "Void": ["void"],
    "Charged": ["charged"],
    "Rainy": ["rainy"],
    "Cold": ["cold"],
    "Golden": ["golden"],
    "Emerald": ["emerald"],
    "Diamond": ["diamond"]
}

OUT_OF_STOCK_PATTERNS = [
    "nostock",
    "noistock",
    "noslock",
    "nosrock",
    "nost0ck",
    "no5tock",
    "n0stock",
    "notstock"
]

STRICT_QUANTITY_RE = re.compile(r"(?<![a-z0-9])x\s*\d+\b", re.IGNORECASE)
WEATHER_MAX_LINES = 3
WEATHER_LINE_SUFFIX_TOLERANCE = 2
last_sent_message = ""
DEBUG_IMAGE_PATTERNS = [
    "debug_weather.png",
    "debug_weather_step_*.png",
    "debug_card_step_*.png",
    "debug_shop_step_*.png",
    "debug_scan_step_*.png",
    "shop_crop_debug.png"
]
CARD_REGION_LAYOUTS = {
    1: {
        "name_box": (0.45, 0.40, 0.98, 0.80),
        "quantity_boxes": [
            (0.38, 0.48, 0.76, 1.28),
            (0.43, 0.44, 0.72, 1.08)
        ]
    },
    2: {
        "name_box": (0.45, 0.00, 0.98, 0.38),
        "quantity_boxes": [
            (0.45, 0.28, 0.62, 0.68),
            (0.40, 0.18, 0.70, 0.68)
        ]
    }
}


def send_discord_message(message):
    try:
        response = requests.post(WEBHOOK_URL, json={"content": message})
        if response.status_code not in [200, 204]:
            print(f"Discord webhook error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Failed to send webhook: {e}")


def cleanup_debug_images():
    if not CLEAN_DEBUG_IMAGES_ON_START:
        return

    deleted = 0
    for pattern in DEBUG_IMAGE_PATTERNS:
        for path in Path(".").glob(pattern):
            if path.is_file():
                path.unlink()
                deleted += 1

    print(f"Deleted {deleted} old debug image(s).")


def take_screenshot(region):
    with mss.MSS() as sct:
        screenshot = sct.grab(region)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return img


def read_text_from_image(img):
    return pytesseract.image_to_string(img, config="--psm 6")


def read_ocr_data(img, config="--psm 6"):
    return pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT)


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def verbose_log(message):
    if not VERBOSE_DETECTION_LOG:
        return

    print(message)


def preprocess_for_ocr(img, threshold=150, scale=3):
    processed = ImageOps.grayscale(img)
    processed = processed.resize((processed.width * scale, processed.height * scale))
    return processed.point(lambda p: 255 if p > threshold else 0)


def crop_with_relative_box(img, relative_box):
    width, height = img.size
    left = int(width * relative_box[0])
    top = int(height * relative_box[1])
    right = int(width * relative_box[2])
    bottom = int(height * relative_box[3])
    return img.crop((left, top, right, bottom))


def split_nonempty_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def get_normalized_lines(text):
    return [normalize_text(line) for line in split_nonempty_lines(text)]


def read_text_variants(img, configs, thresholds):
    results = []

    for config in configs:
        text = read_text_from_image(img) if config == "--psm 6" else pytesseract.image_to_string(img, config=config)
        results.append(text)

    for threshold in thresholds:
        processed = preprocess_for_ocr(img, threshold=threshold)
        for config in configs:
            results.append(pytesseract.image_to_string(processed, config=config))

    return results


def extract_ocr_lines(img, config="--psm 6"):
    data = read_ocr_data(img, config=config)
    lines = {}

    for i, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
        if not text:
            continue

        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        line = lines.setdefault(key, {"top": data["top"][i], "parts": []})
        line["top"] = min(line["top"], data["top"][i])
        line["parts"].append(text)

    result = []
    for line in lines.values():
        joined = " ".join(line["parts"]).strip()
        result.append({
            "text": joined,
            "normalized": normalize_text(joined),
            "top": line["top"]
        })

    result.sort(key=lambda line: line["top"])
    return result


def card_contains_loose_dice_text(card_text, dice):
    return normalize_text(dice) in normalize_text(card_text)


def is_out_of_stock(text):
    text_norm = normalize_text(text)

    for pattern in OUT_OF_STOCK_PATTERNS:
        if pattern in text_norm:
            return True

    return False


def has_quantity(text):
    text = text.replace("×", "x").replace("X", "x")
    return bool(STRICT_QUANTITY_RE.search(text))


def detect_weather_name_from_lines(lines):
    candidates = []

    for line in lines:
        line_norm = line["normalized"]
        for weather, aliases in WEATHER_ALIASES.items():
            for alias in aliases:
                alias_norm = normalize_text(alias)
                if line_norm == alias_norm:
                    candidates.append((4, -line["top"], weather, line["text"]))
                    break
                if line_norm.startswith(alias_norm):
                    suffix = line_norm[len(alias_norm):]
                    if len(suffix) <= WEATHER_LINE_SUFFIX_TOLERANCE:
                        candidates.append((3, -line["top"], weather, line["text"]))
                        break
            else:
                continue
            break

    if not candidates:
        return None, None

    _, _, best_weather, matched_line = max(candidates)
    return best_weather, matched_line


def find_loose_target_dice_name(card_text):
    for dice in TARGET_DICE:
        if card_contains_loose_dice_text(card_text, dice):
            return display_dice_name(dice)
    return None


def detect_exact_dice_name_from_card(card_img, card_text, card_index):
    raw_normalized_lines = get_normalized_lines(card_text)

    for dice in TARGET_DICE:
        dice_norm = normalize_text(dice)
        if dice_norm in raw_normalized_lines:
            return display_dice_name(dice)

    loose_name = find_loose_target_dice_name(card_text)
    if loose_name is None:
        return None

    layout = CARD_REGION_LAYOUTS[card_index]
    name_crop = crop_with_relative_box(card_img, layout["name_box"])
    name_texts = read_text_variants(name_crop, ["--psm 6", "--psm 7"], [150])
    normalized_lines = []

    for text in name_texts:
        normalized_lines.extend(normalize_text(line) for line in split_nonempty_lines(text))

    for dice in TARGET_DICE:
        dice_norm = normalize_text(dice)
        if dice_norm in normalized_lines:
            return display_dice_name(dice)

    return None


def detect_quantity_from_card(card_img, card_text, card_index, require_fallback):
    quantity_texts = [card_text]
    layout = CARD_REGION_LAYOUTS[card_index]

    if has_quantity(card_text):
        return True, card_text.strip()

    if not require_fallback:
        return False, card_text.strip()

    for relative_box in layout["quantity_boxes"]:
        crop = crop_with_relative_box(card_img, relative_box)
        for threshold in (110, 130, 150):
            processed = preprocess_for_ocr(crop, threshold=threshold, scale=4)
            quantity_texts.append(
                pytesseract.image_to_string(
                    processed,
                    config="--psm 6 -c tessedit_char_whitelist=xX×0123456789"
                )
            )
            quantity_texts.append(
                pytesseract.image_to_string(
                    processed,
                    config="--psm 7 -c tessedit_char_whitelist=xX×0123456789"
                )
            )

    for text in quantity_texts:
        if has_quantity(text):
            return True, text.strip()

    return False, quantity_texts[-1].strip() if quantity_texts else ""


def log_weather_detection(step_number, raw_text, detected_weather):
    verbose_log(
        "\n".join([
            f"WEATHER step={step_number}",
            f"raw_ocr={raw_text or '<empty>'}",
            f"detected_weather={detected_weather or 'None'}",
            "-" * 20
        ])
    )


def log_card_detection(step_number, card_index, raw_text, detected_dice_name, no_stock_detected, quantity_detected, decision):
    verbose_log(
        "\n".join([
            f"CARD step={step_number} card={card_index}",
            f"raw_ocr={raw_text or '<empty>'}",
            f"detected_dice_name={detected_dice_name or 'None'}",
            f"no_stock_detected={no_stock_detected}",
            f"quantity_detected={quantity_detected}",
            f"decision={decision}",
            "-" * 20
        ])
    )


def detect_weather(step_number):
    img = take_screenshot(WEATHER_REGION)
    img.save("debug_weather.png")
    if SAVE_WEATHER_DEBUG_IMAGES:
        img.save(f"debug_weather_step_{step_number}.png")
    raw_text = read_text_from_image(img)
    lines = []
    weather_texts = [raw_text]

    processed = preprocess_for_ocr(img, threshold=130, scale=3)
    weather_texts.append(pytesseract.image_to_string(processed, config="--psm 6"))

    for text in weather_texts:
        for index, line in enumerate(split_nonempty_lines(text)[:WEATHER_MAX_LINES]):
            lines.append({
                "text": line,
                "normalized": normalize_text(line),
                "top": index
            })

    detected_weather, matched_line = detect_weather_name_from_lines(lines)

    print("Weather OCR:")
    print(raw_text)
    print("-" * 40)

    log_weather_detection(step_number, raw_text, detected_weather)

    if detected_weather:
        verbose_log(f"WEATHER matched_line={matched_line}")
        return [detected_weather]

    return []


def split_shop_into_card_regions(shop_img):
    width, height = shop_img.size

    cards = []

    # Upper card area
    cards.append(shop_img.crop((0, 250, width, 500)))

    # Lower card area - start at 501 to avoid 45-pixel overlap with upper region
    cards.append(shop_img.crop((0, 501, width, 735)))

    return cards


def display_dice_name(dice):
    return DISPLAY_NAME_FIXES.get(dice, dice)


def detect_in_stock_dice_from_card(card_img, card_text, step_number, card_index):
    found = []
    card_out = is_out_of_stock(card_text)
    detected_dice_name = detect_exact_dice_name_from_card(card_img, card_text, card_index)
    quantity_detected = False
    quantity_source_text = card_text.strip()

    if detected_dice_name is None:
        loose_name = find_loose_target_dice_name(card_text)
        log_card_detection(
            step_number,
            card_index,
            card_text,
            loose_name,
            card_out,
            quantity_detected,
            "SKIPPED: no exact normalized target dice name match."
        )
        return found

    if card_out:
        quantity_detected, quantity_source_text = detect_quantity_from_card(
            card_img,
            card_text,
            card_index,
            require_fallback=False
        )
        log_card_detection(
            step_number,
            card_index,
            card_text,
            detected_dice_name,
            card_out,
            quantity_detected,
            "SKIPPED: NO STOCK detected in the same card OCR."
        )
        return found

    quantity_detected, quantity_source_text = detect_quantity_from_card(
        card_img,
        card_text,
        card_index,
        require_fallback=True
    )

    if not quantity_detected:
        log_card_detection(
            step_number,
            card_index,
            card_text,
            detected_dice_name,
            card_out,
            quantity_detected,
            "SKIPPED: no strict x<number> quantity found in this card."
        )
        return found

    found.append(detected_dice_name)
    log_card_detection(
        step_number,
        card_index,
        f"{card_text}\n[quantity_source]\n{quantity_source_text}",
        detected_dice_name,
        card_out,
        quantity_detected,
        "ACCEPTED: exact dice name + strict quantity + no NO STOCK."
    )

    return found


def scan_shop_dice():
    all_in_stock_dice = []
    all_raw_text = []
    all_weather = []

    print("Starting shop scan from current position...")
    time.sleep(1)

    for step in range(SCROLL_STEPS):
        step_number = step + 1
        print(f"Shop scan step {step_number}/{SCROLL_STEPS}")

        # Check weather every scroll step in case it changes mid-scan.
        weather_now = detect_weather(step_number)
        all_weather.extend(weather_now)

        shop_img = take_screenshot(SHOP_REGION)

        full_shop_text = read_text_from_image(shop_img)
        all_raw_text.append(full_shop_text)

        card_imgs = split_shop_into_card_regions(shop_img)

        for index, card_img in enumerate(card_imgs):
            if SAVE_CARD_DEBUG_IMAGES:
                card_img.save(f"debug_card_step_{step_number}_{index + 1}.png")

            card_text = read_text_from_image(card_img)

            print(f"Card {index + 1} OCR:")
            print(card_text)
            print("-" * 20)

            dice_found = detect_in_stock_dice_from_card(
                card_img,
                card_text,
                step_number,
                index + 1
            )
            all_in_stock_dice.extend(dice_found)

        if step < SCROLL_STEPS - 1:
            pyautogui.scroll(SCROLL_AMOUNT)
            time.sleep(WAIT_AFTER_SCROLL)

    print("Returning shop near starting position...")
    pyautogui.scroll(RETURN_SCROLL_AMOUNT)
    time.sleep(2)

    return {
        "raw_text": "\n".join(all_raw_text),
        "in_stock_dice": sorted(set(all_in_stock_dice)),
        "weather": sorted(set(all_weather))
    }


def looks_like_shop(text):
    text_lower = text.lower()

    shop_words = [
        "dice shop",
        "restock",
        "luck",
        "dice",
        "stock"
    ]

    return any(word in text_lower for word in shop_words)


def build_discord_message(weather, in_stock_dice):
    lines = []
    lines.append("[SAB] **Shop/Weather Scan**")

    lines.append("")
    if weather:
        lines.append("**Weather Detected:**")
        for w in weather:
            lines.append(f"- {w}")
    else:
        lines.append("**Weather Detected:** None from target list")

    lines.append("")
    if in_stock_dice:
        lines.append("**Target Dice In Stock:**")
        for dice in in_stock_dice:
            lines.append(f"- {dice}")
    else:
        lines.append("**Target Dice In Stock:** None detected")

    lines.append("")
    lines.append("_Only reports target dice when the same OCR card has an exact dice-name line, a strict x<number> quantity, and no NO STOCK text._")

    return "\n".join(lines)


def main():
    global last_sent_message

    print("SAB detector started.")
    print("Open Roblox shop and keep your mouse over the shop list.")
    print("Do not click Discord/VS Code while it scans.")
    print("Press Ctrl + C to stop.")
    cleanup_debug_images()

    send_discord_message("SAB shop/weather detector started.")

    time.sleep(3)

    while True:
        shop_result = scan_shop_dice()

        if not looks_like_shop(shop_result["raw_text"]):
            print("Shop not detected. Skipping Discord message.")
        else:
            message = build_discord_message(
                shop_result["weather"],
                shop_result["in_stock_dice"]
            )

            if message != last_sent_message:
                send_discord_message(message)
                last_sent_message = message
                print("Sent cleaned scan to Discord.")
            else:
                print("No changes. Not sending duplicate.")

        print(f"Waiting {SCAN_EVERY_SECONDS} seconds...")
        time.sleep(SCAN_EVERY_SECONDS)


if __name__ == "__main__":
    main()
