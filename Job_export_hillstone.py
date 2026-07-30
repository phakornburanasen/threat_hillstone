import base64
import binascii
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import (
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    expect,
    sync_playwright,
)


ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_FILE)


def decode_env_base64(variable_name: str) -> str:
    encoded_value = os.getenv(variable_name)
    if not encoded_value:
        raise RuntimeError(f"Missing {variable_name} in {ENV_FILE}")

    try:
        return base64.b64decode(
            encoded_value,
            validate=True,
        ).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as error:
        raise RuntimeError(
            f"{variable_name} is not valid Base64 UTF-8"
        ) from error


try:
    HILLSTONE_USERNAME = decode_env_base64("HILLSTONE_USERNAME_B64")
    HILLSTONE_PASSWORD = decode_env_base64("HILLSTONE_PASSWORD_B64")
except RuntimeError as error:
    raise SystemExit(f"Hillstone configuration error: {error}")

HILLSTONE_HEADLESS = os.getenv(
    "HILLSTONE_HEADLESS",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}


def run(playwright: Playwright) -> None:
    screenshot_dir = Path(__file__).resolve().parent / "log pic"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_number = 0

    def capture(page, step_name: str) -> None:
        nonlocal screenshot_number
        screenshot_number += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_step_name = re.sub(r"[^A-Za-z0-9_-]+", "_", step_name)
        screenshot_path = screenshot_dir / (
            f"{screenshot_number:02d}_{timestamp}_{safe_step_name}.png"
        )
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot : {screenshot_path}")

    browser = playwright.chromium.launch(headless=HILLSTONE_HEADLESS)
    context = browser.new_context(
        accept_downloads=True,
        ignore_https_errors=True,
    )
    page = context.new_page()
    page.goto("http://10.0.32.161/HomeApp/")
    expect(page.get_by_role("link", name="Hillstone Networks BDS")).to_be_visible()
    with page.expect_popup() as page1_info:
        page.get_by_role("link", name="Hillstone Networks BDS").click()
    page1 = page1_info.value
    page1.wait_for_load_state("domcontentloaded")

    username_field = page1.get_by_role("textbox", name="Username")
    try:
        expect(username_field).to_be_visible(timeout=30000)
    except (AssertionError, PlaywrightTimeoutError):
        capture(page1, "login_page_error")
        raise

    username_field.fill(HILLSTONE_USERNAME)
    page1.get_by_role("textbox", name="Password").click()
    page1.get_by_role("textbox", name="Password").click()
    page1.get_by_role("textbox", name="Password").fill(HILLSTONE_PASSWORD)
    page1.get_by_role("button", name="Login").click()
    page1.get_by_text("Log & Report").click()
    expect(page1.get_by_label("Detection Period")).to_be_visible()
    capture(page1, "after_login")
    page1.get_by_label("Detection Period").click()
    # Onclick select Last 24 Hours
    page1.get_by_role("option", name="Last 24 Hours").click()
    # Onclick select filter 
    page1.get_by_role("button", name="Filter").click()
    # Onclick select severity
    # page1.get_by_text("Severity", exact=True).click()
    page1.locator(
        "xpath=/html/body/div[4]/div/li[3]"
    ).click()
    
    print("Onclick serverity")
        # Onclick Serveriry
    page1.locator(
        "xpath=/html/body/div[5]/div/div[1]"
    ).click()
    # Onclick High
    page1.locator(
        "xpath=/html/body/div[5]/div/div[2]/span[2]"
    ).click()
    print("Onclick High")
    # Onclick filter
    page1.get_by_role("button", name="Filter").click()
    # Intrusion
    page1.locator(
        "xpath=/html/body/div[4]/div/li[6]"
    ).click()
    # Onclick Detection Engine
    # page1.wait_for_timeout(30000)
    page1.locator(
        "xpath=/html/body/div[6]/div/div[1]/span[2]"
    ).click()
    page1.locator(
        "xpath=/html/body/div[6]/div/div[2]/span[2]"
    ).click()
    page1.locator("div").filter(has_text=re.compile(r"^Antivirus$")).locator("span").first.click()
    page1.locator("div").filter(has_text=re.compile(r"^Advanced Threat Detection$")).locator("span").first.click()
    page1.locator("div").filter(has_text=re.compile(r"^Sandbox Threat Detection$")).locator("span").first.click()
    page1.locator("div").filter(has_text=re.compile(r"^Deception Detection$")).locator("span").first.click()
    page1.locator("div").filter(has_text=re.compile(r"^Abnormal Behavior Detection$")).locator("span").first.click()
    page1.locator(
        "xpath=/html/body/div[6]/div/div[8]/span[2]"
    ).click()
    page1.locator(
        "xpath=/html/body/div[6]/div/div[9]/span[2]"
    ).click()
    page1.locator(
        "xpath=/html/body/div[6]/div/div[10]/span[2]"
    ).click()
    page1.get_by_role("button", name="Filter").click()
    page1.locator(
        "xpath=/html/body/div[4]/div/li[3]"
    ).click()
    expect(page1.get_by_role("button", name="OK")).to_be_visible()
    page1.get_by_role("button", name="OK").click()
    expect(page1.get_by_role("button", name="Filter")).to_be_visible()
    expect(page1.get_by_role("button", name="Filter")).to_be_visible()
    page1.get_by_role("button", name="Filter").click()
    
    page1.locator(
        "xpath=/html/body/div[4]/div/li[3]"
    ).click()
    expect(page1.get_by_role("button", name="OK")).to_be_visible()
    page1.get_by_role("button", name="OK").click()
    expect(page1.get_by_role("button", name="Export")).to_be_visible()
    capture(page1, "filters_applied")
    page1.get_by_role("button", name="Export").click()
    expect(page1.get_by_text("CSV")).to_be_visible()
    page1.get_by_text("CSV").click()
    page1.get_by_label("Name *").click()
    page1.get_by_label("Name *").fill("LogsHillstoneDaily")
    capture(page1, "export_log")

    # ExtJS keeps several hidden "OK" buttons in the DOM. Select only the
    # visible button text instead of relying on a generated window/button ID.
    export_ok_button = page1.locator(
        "span.x-btn-inner:visible",
        has_text=re.compile(r"^\s*OK\s*$"),
    ).last
    expect(export_ok_button).to_be_visible()
    export_ok_button.click()

    # Confirm the "Whether or not to save" dialog. The download starts only
    # after this second OK button is clicked.
    save_confirmation = page1.get_by_text(
        "Whether or not to save",
        exact=True,
    )
    expect(save_confirmation).to_be_visible(timeout=30000)
    capture(page1, "save_confirmation")
    confirmation_ok_button = page1.locator(
        "span.x-btn-inner:visible",
        has_text=re.compile(r"^\s*OK\s*$"),
    ).last
    expect(confirmation_ok_button).to_be_visible()

    with page1.expect_download(timeout=600000) as download_info:
        confirmation_ok_button.click()

    download = download_info.value

    # บันทึกไฟล์ลง Downloads
    #save_path = Path(r"C:\inetpub\wwwroot\threat\LogsHillstoneDaily.csv")
    save_path = Path(__file__).parent / "LogsHillstoneDaily.csv"

    download.save_as(str(save_path))

    print(f"Download Success : {save_path}")
    capture(page1, "download_completed")

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
