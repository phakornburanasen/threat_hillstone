import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://10.0.32.71/AD-Management/#Dashboard")
    page.get_by_placeholder("ADUser").click()
    page.get_by_placeholder("ADUser").fill("T9058")
    page.get_by_placeholder("ADUser").press("Tab")
    page.get_by_placeholder("Enter password").fill("TNLx789")
    page.get_by_role("button", name=" เข้าสู่ระบบ").click()
    page.get_by_label("Password Management").click()
    page.get_by_placeholder("Search...").fill("t9058")
    page.get_by_label("View User Phakorn Buranasen").click()
    page.get_by_role("button", name=" Extend Password").click()
    page.get_by_role("button", name="OK").click()
    page.get_by_role("button", name="OK").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
