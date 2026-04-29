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

# use discord role ids
ROLE_IDS = {
    "Kraken Dice": "1499171014675009648",
    "Seraphic Dice": "1499171089350135848",
    "Galactic Dice": "1499171130827604068",
    "Eldritch Dice": "1499171182132334602",
    "Emperor Dice": "1499171246947041420",
    "Annihilation Dice": "1499171295110103090",
    "Disaster Dice": "1499171351250993203",
    "Impossible Dice": "1499171399170920448",
    "Limbo Dice": "1499171455454150716",
    "Chronos Dice": "1499171498504487013",
    "Yinyang Dice": "1499171536681308341",
    "Uriel Dice": "1499171618021183599",
    "Matrix Dice": "1499171713467027587",
    "Overlord Dice": "1499171747059204096",
    "Baddies Dice": "1498530792362610840",
    "Charged": "1499172052135968790",
    "Void": "1499172110008844330",
    "Celestial": "1499172159816466432",
    "Solar": "1499172208445100072",
    "Rainy": "1499172246684438718",
    "Cosmic Dice": "1498530547939545128",
    "Apex Dice": "1498530655972098178"
}

SINGLE_CARD_REGION = {
    "left": 600,
    "top": 470,
    "width": 1120,
    "height": 330
}

WEATHER_REGION = {
    "left": 780,
    "top": 85,
    "width": 760,
    "height": 240
}

CARD_SCAN_STEPS = 15
RETURN_SCROLL_AMOUNT = 6000
CARD_SCROLL_AMOUNT = -430 #orig -415
WAIT_AFTER_SCROLL = 0.35
SCAN_EVERY_SECONDS = 240

# Turn this on for one test if a dice gets missed.
# creates debug_card_step_# and debug_status_crop_step_# PNG files.
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
    "Reality Dice",

    # testing item since other dices r too rare to test with, will remove later
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

COSMIC_DICE = {
    "Kraken Dice",
    "Seraphic Dice",
    "Galactic Dice",
    "Eldritch Dice",
    "Emperor Dice",
    "Annihilation Dice",
    "Disaster Dice",
    "Impossible Dice"
}

APEX_DICE = {
    "Limbo Dice",
    "Chronos Dice",
    "Yinyang Dice",
    "Matrix Dice",
    "Uriel Dice",
    "Overlord Dice",
    "Baddies Dice"
}

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
    "notstock",
    "nofstock",
    "noslog",
    "nostog",
    "nostogs",
    "nosuggs",
    "nosuoek",
    "nostiock",
    "nosiock",
    "0siock",
    "nosog",
    "nosuoets",
    "nosrods",
    "nonstock",
    "noxfstiock",
    "nonstiogk",
    "nosoe",
    "nosroere",
    "nosioer",
    "nostoel",
    "nofstiogk",
    "noxxstiock",
    "nosiroxere"
]

STRICT_QUANTITY_RE = re.compile(r"(?<![a-z0-9])x[ \t]*\d+\b", re.IGNORECASE)
QUANTITY_OCR_WHITELIST = "xX\u00d70123456789"
QUANTITY_OCR_CONFIGS = [
    f"--psm 6 -c tessedit_char_whitelist={QUANTITY_OCR_WHITELIST}",
    f"--psm 7 -c tessedit_char_whitelist={QUANTITY_OCR_WHITELIST}",
    f"--psm 11 -c tessedit_char_whitelist={QUANTITY_OCR_WHITELIST}"
]
NO_STOCK_OCR_CONFIGS = ["--psm 6", "--psm 11"]
NO_STOCK_OCR_THRESHOLDS = (110, 130, 150, 170)
RED_STATUS_PIXEL_THRESHOLD = 50
GREEN_STATUS_PIXEL_THRESHOLD = 30
WEATHER_MAX_LINES = 3
WEATHER_LINE_SUFFIX_TOLERANCE = 2
last_sent_message = ""
DEBUG_IMAGE_PATTERNS = [
    "debug_weather.png",
    "debug_weather_step_*.png",
    "debug_card_step_*.png",
    "debug_status_crop_step_*.png",
    "debug_shop_step_*.png",
    "debug_scan_step_*.png",
    "shop_crop_debug.png"
]
SINGLE_CARD_LAYOUT = {
    "name_box": (0.28, 0.04, 0.98, 0.62),
    "status_box": (0.445, 0.56, 0.72, 0.79),
    "quantity_boxes": [
        (0.28, 0.18, 0.92, 0.74),
        (0.34, 0.30, 0.78, 0.72)
    ]
}


def send_discord_message(message):
    try:
        payload = {
            "content": message,
            "allowed_mentions": {"parse": ["roles"]}
        }
        response = requests.post(WEBHOOK_URL, json=payload)
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


def get_status_crop(card_img):
    return crop_with_relative_box(card_img, SINGLE_CARD_LAYOUT["status_box"])


def save_card_debug_images(card_img, step_number):
    if not SAVE_CARD_DEBUG_IMAGES:
        return

    card_img.save(f"debug_card_step_{step_number}.png")
    get_status_crop(card_img).save(f"debug_status_crop_step_{step_number}.png")


def split_nonempty_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def get_normalized_lines(text):
    return [normalize_text(line) for line in split_nonempty_lines(text)]


def get_normalized_words(text):
    return [word for word in (normalize_text(part) for part in text.split()) if word]


def get_role_ping(name):
    role_id = ROLE_IDS.get(name, "").strip()
    if not role_id or role_id.upper().startswith("PASTE_") or not role_id.isdigit():
        return ""
    return f"<@&{role_id}>"


def build_role_pings(weather, in_stock_dice):
    if not weather and not in_stock_dice:
        return []

    pings = []
    seen_pings = set()

    def add_role_ping(name):
        ping = get_role_ping(name)
        if ping and ping not in seen_pings:
            seen_pings.add(ping)
            pings.append(ping)

    for weather_name in weather:
        add_role_ping(weather_name)

    displayed_dice = [display_dice_name(dice) for dice in in_stock_dice]
    for dice in displayed_dice:
        add_role_ping(dice)

    if any(dice in COSMIC_DICE for dice in displayed_dice):
        add_role_ping("Cosmic Dice")

    if any(dice in APEX_DICE for dice in displayed_dice):
        add_role_ping("Apex Dice")

    return pings


def line_has_exact_dice_word_sequence(line, dice):
    line_words = get_normalized_words(line)
    dice_words = get_normalized_words(dice)

    if not line_words or not dice_words or len(dice_words) > len(line_words):
        return False

    for index in range(len(line_words) - len(dice_words) + 1):
        if line_words[index:index + len(dice_words)] == dice_words:
            return True

    return False


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


def read_out_of_stock_text_variants(card_img, card_text):
    variants = [card_text]

    for config in NO_STOCK_OCR_CONFIGS:
        if config != "--psm 6":
            variants.append(pytesseract.image_to_string(card_img, config=config))

    for threshold in NO_STOCK_OCR_THRESHOLDS:
        processed = preprocess_for_ocr(card_img, threshold=threshold, scale=3)
        for config in NO_STOCK_OCR_CONFIGS:
            variants.append(pytesseract.image_to_string(processed, config=config))

    return variants


def detect_out_of_stock_from_card(card_img, card_text):
    for text in read_out_of_stock_text_variants(card_img, card_text):
        if is_out_of_stock(text):
            return True, text.strip()

    return False, ""


def is_red_status_pixel(r, g, b):
    return r > 150 and g < 100 and b < 100


def is_green_status_pixel(r, g, b):
    return g > 130 and r < 120 and b < 120


def detect_color_stock_status(card_img):
    status_crop = get_status_crop(card_img)
    red_pixels = 0
    green_pixels = 0

    for r, g, b in status_crop.convert("RGB").getdata():
        if is_red_status_pixel(r, g, b):
            red_pixels += 1
        if is_green_status_pixel(r, g, b):
            green_pixels += 1

    return {
        "red_status_pixels": red_pixels,
        "green_status_pixels": green_pixels,
        "color_out_of_stock_detected": red_pixels >= RED_STATUS_PIXEL_THRESHOLD,
        "color_quantity_detected": green_pixels >= GREEN_STATUS_PIXEL_THRESHOLD
    }


def has_quantity(text):
    text = normalize_quantity_text(text)
    return bool(STRICT_QUANTITY_RE.search(text))


def normalize_quantity_text(text):
    quantity_chars = str.maketrans({
        "X": "x",
        "\u00d7": "x",
        "\u2715": "x",
        "\u2716": "x",
        "\u2573": "x"
    })
    return text.replace("Ã—", "x").translate(quantity_chars)


def get_quantity_text_near_dice_name(card_text, dice_name):
    lines = split_nonempty_lines(card_text)

    for index, line in enumerate(lines):
        if line_has_exact_dice_word_sequence(line, dice_name):
            return "\n".join(lines[index:index + 3])

    return ""


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


def detect_exact_dice_name_from_card(card_img, card_text):
    raw_lines = split_nonempty_lines(card_text)
    raw_normalized_lines = get_normalized_lines(card_text)

    for dice in TARGET_DICE:
        dice_norm = normalize_text(dice)
        if dice_norm in raw_normalized_lines:
            return display_dice_name(dice)
        if any(line_has_exact_dice_word_sequence(line, dice) for line in raw_lines):
            return display_dice_name(dice)

    loose_name = find_loose_target_dice_name(card_text)
    if loose_name is None:
        return None

    name_crop = crop_with_relative_box(card_img, SINGLE_CARD_LAYOUT["name_box"])
    name_texts = read_text_variants(name_crop, ["--psm 6", "--psm 7"], [150])
    normalized_lines = []

    for text in name_texts:
        normalized_lines.extend(normalize_text(line) for line in split_nonempty_lines(text))

    for dice in TARGET_DICE:
        dice_norm = normalize_text(dice)
        if dice_norm in normalized_lines:
            return display_dice_name(dice)
        if any(line_has_exact_dice_word_sequence(line, dice) for text in name_texts for line in split_nonempty_lines(text)):
            return display_dice_name(dice)

    return None


def detect_quantity_from_card(card_img, card_text, detected_dice_name, require_fallback):
    quantity_texts = [card_text]
    nearby_text = get_quantity_text_near_dice_name(card_text, detected_dice_name)

    if has_quantity(nearby_text):
        return True, nearby_text.strip()

    if not require_fallback:
        return False, card_text.strip()

    for relative_box in SINGLE_CARD_LAYOUT["quantity_boxes"]:
        crop = crop_with_relative_box(card_img, relative_box)
        for config in QUANTITY_OCR_CONFIGS:
            quantity_texts.append(pytesseract.image_to_string(crop, config=config))

        for threshold in (110, 130, 150):
            processed = preprocess_for_ocr(crop, threshold=threshold, scale=4)
            for config in QUANTITY_OCR_CONFIGS:
                quantity_texts.append(pytesseract.image_to_string(processed, config=config))

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


def log_card_detection(step_number, raw_text, detected_dice_name, no_stock_detected, quantity_detected, decision, color_status=None):
    color_status = color_status or {}
    verbose_log(
        "\n".join([
            f"CARD step={step_number}",
            f"raw_ocr={raw_text or '<empty>'}",
            f"detected_dice_name={detected_dice_name or 'None'}",
            f"no_stock_detected={no_stock_detected}",
            f"quantity_detected={quantity_detected}",
            f"red_status_pixels={color_status.get('red_status_pixels', 0)}",
            f"green_status_pixels={color_status.get('green_status_pixels', 0)}",
            f"color_out_of_stock_detected={color_status.get('color_out_of_stock_detected', False)}",
            f"color_quantity_detected={color_status.get('color_quantity_detected', False)}",
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


def display_dice_name(dice):
    return DISPLAY_NAME_FIXES.get(dice, dice)


def detect_in_stock_dice_from_card(card_img, card_text, step_number):
    found = []
    ocr_out_of_stock, no_stock_source_text = detect_out_of_stock_from_card(card_img, card_text)
    color_status = detect_color_stock_status(card_img)
    card_out = ocr_out_of_stock or color_status["color_out_of_stock_detected"]
    detected_dice_name = detect_exact_dice_name_from_card(card_img, card_text)
    quantity_detected = False
    quantity_source_text = card_text.strip()

    if detected_dice_name is None:
        loose_name = find_loose_target_dice_name(card_text)
        log_card_detection(
            step_number,
            card_text,
            loose_name,
            card_out,
            quantity_detected,
            "SKIPPED: no exact normalized target dice name match.",
            color_status
        )
        return found

    if card_out:
        quantity_detected, quantity_source_text = detect_quantity_from_card(
            card_img,
            card_text,
            detected_dice_name,
            require_fallback=False
        )
        no_stock_log_text = card_text
        if no_stock_source_text and no_stock_source_text != card_text.strip():
            no_stock_log_text = f"{card_text}\n[no_stock_source]\n{no_stock_source_text}"

        log_card_detection(
            step_number,
            no_stock_log_text,
            detected_dice_name,
            card_out,
            quantity_detected,
            "SKIPPED: NO STOCK detected by OCR or red status pixels.",
            color_status
        )
        return found

    quantity_detected, quantity_source_text = detect_quantity_from_card(
        card_img,
        card_text,
        detected_dice_name,
        require_fallback=True
    )

    if not quantity_detected:
        log_card_detection(
            step_number,
            card_text,
            detected_dice_name,
            card_out,
            quantity_detected,
            "SKIPPED: no strict x<number> quantity found in this card.",
            color_status
        )
        return found

    if not color_status["color_quantity_detected"]:
        log_card_detection(
            step_number,
            f"{card_text}\n[quantity_source]\n{quantity_source_text}",
            detected_dice_name,
            card_out,
            quantity_detected,
            "SKIPPED: strict quantity found, but no green status pixels found.",
            color_status
        )
        return found

    found.append(detected_dice_name)
    log_card_detection(
        step_number,
        f"{card_text}\n[quantity_source]\n{quantity_source_text}",
        detected_dice_name,
        card_out,
        quantity_detected,
        "ACCEPTED: exact dice name + strict quantity + green status pixels + no NO STOCK/red status.",
        color_status
    )

    return found


def scan_shop_dice():
    all_in_stock_dice = []
    all_raw_text = []
    all_weather = []

    print("Starting shop scan from current position...")
    time.sleep(1)

    for step in range(CARD_SCAN_STEPS):
        step_number = step + 1
        print(f"Shop scan step {step_number}/{CARD_SCAN_STEPS}")

        # Check weather every scroll step in case it changes mid-scan.
        weather_now = detect_weather(step_number)
        all_weather.extend(weather_now)

        card_img = take_screenshot(SINGLE_CARD_REGION)

        save_card_debug_images(card_img, step_number)

        card_text = read_text_from_image(card_img)
        all_raw_text.append(card_text)

        print("Card OCR:")
        print(card_text)
        print("-" * 20)

        dice_found = detect_in_stock_dice_from_card(
            card_img,
            card_text,
            step_number
        )
        all_in_stock_dice.extend(dice_found)

        if step < CARD_SCAN_STEPS - 1:
            pyautogui.scroll(CARD_SCROLL_AMOUNT)
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
    weather_emojis = {
        "Solar": "☀️",
        "Celestial": "🌌",
        "Void": "🕳️",
        "Charged": "⚡",
        "Rainy": "🌧️",
        "Cold": "❄️",
        "Golden": "🟡",
        "Emerald": "🟢",
        "Diamond": "💎"
    }

    header_lines = ["[SAB] Shop/Weather Scan"]
    role_pings = build_role_pings(weather, in_stock_dice)
    if role_pings:
        header_lines.append(" ".join(role_pings))

    lines = []
    lines.append("🌦️ Weather Stock")
    if weather:
        for w in weather:
            lines.append(f"- {weather_emojis.get(w, '🌦️')} {w}")
    else:
        lines.append("- None from target list")

    lines.append("")
    lines.append("🎲 Dice Stock")
    if in_stock_dice:
        for dice in in_stock_dice:
            lines.append(f"- {dice}")
    else:
        lines.append("- None detected")

    lines.append("")
    lines.append("Only reports target dice when the same OCR card has an exact dice-name line, a strict x<number> quantity, and no NO STOCK text.")

    return "\n".join(header_lines) + "\n```text\n" + "\n".join(lines) + "\n```"


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
