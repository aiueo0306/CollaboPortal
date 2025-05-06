from playwright.sync_api import sync_playwright
import time

EMAIL = "sato.sota@create-sd.co.jp"
PASSWORD = "sotasato!"
START_URL = "https://dx.collaboportal.com/notifications"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # デバッグ時は headless=False に
    context = browser.new_context()
    page = context.new_page()

    print("▶ ポータルサイトにアクセス中...")
    page.goto(START_URL)

    # 自動でログイン画面にリダイレクトされる
    page.wait_for_url("https://login-id.dx-utility.com/login*", timeout=20000)

    print("▶ ログイン情報を入力中...")
    page.fill('input[type="email"]', EMAIL)
    page.click('button[type="submit"]')  # 「続行」など

    page.wait_for_selector('input[type="password"]', timeout=10000)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button[type="submit"]')

    # ログイン後のページにリダイレクトされるのを待つ
    page.wait_for_url("https://dx.collaboportal.com*", timeout=20000)

    print("✅ ログイン完了。ページ取得中...")
    page.wait_for_load_state("networkidle")

    # 例：新着通知情報を取得
    html = page.content()
    print(html)

    browser.close()
