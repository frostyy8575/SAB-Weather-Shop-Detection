import time
import pyautogui

print("Open the shop and put your mouse over the shop list.")
print("Scrolling down in 3 seconds...")
time.sleep(3)

pyautogui.scroll(-500)

print("Done.")