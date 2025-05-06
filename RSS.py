from playwright.sync_api import sync_playwright
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urljoin

# ログイン情報とURL設定
LOGIN_URL = "https://dx.collaboportal.com/"
USERNAME = "sato.sota@create-sd.co.jp"
PASSWORD = "sota0306!"
BASE_URL = "https://dx.collaboportal.com"
DEFAULT_LINK = BASE_URL + "/notifications"

# 保存先のパス（GitHub上のフォルダを想定）
OUTPUT_DIR = "rss_output"
OUTPUT_FILENAME = "notifications.xml"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

# 通知のXML保存関数
def save_as_xml(items, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Collabo Portal Notifications"
    ET.SubElement(channel, "link").text = DEFAULT_LINK
    ET.SubElement(channel, "description").text = "通知一覧"

    for item in items:
        entry = ET.SubElement(channel, "item")
        ET.SubElement(entry, "title").text = item["title"]
        ET.SubElement(entry, "link").text = item["link"]
        ET.SubElement(entry, "description").text = item["description"]
        ET.SubElement(entry, "pubDate").text = item["pub_date"].strftime("%a, %d %b %Y %H:%M:%S +0000")

    tree = ET.ElementTree(rss)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"✅ XMLファイルを保存しました: {output_path}")

# 通知一覧の抽出関数
def extract_items(page):
    page.wait_for_selector("article a > h2", timeout=60000)
    rows = page.locator("article")
    count = rows.count()
    print(f"📦 発見した通知数: {count}")

    items = []
    for i in range(count):
        row = rows.nth(i)
        try:
            title = row.locator("a > h2").inner_text().strip()
            link_elem = row.locator("a")
            href = link_elem.first.get_attribute("href")
            link = urljoin(BASE_URL, href) if href else DEFAULT_LINK
            description = ""
            pub_date = datetime.now(timezone.utc)

            items.append({
                "title": title,
                "link": link,
                "description": description,
                "pub_date": pub_date
            })
        except Exception as e:
            print(f"⚠ 通知{i+1}の解析に失敗: {e}")
            continue
    return items

# メイン処理
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # ログインページへアクセス
    page.goto(LOGIN_URL, timeout=60000)
    page.wait_for_selector('#email', timeout=60000)
    page.fill('#email', USERNAME)
    page.wait_for_selector('#password', timeout=60000)
    page.fill('#password', PASSWORD)
    page.get_by_role("button", name="ログインする").click()

    # ✅ ログイン後のリダイレクト完了を待機
    page.wait_for_url("https://dx.collaboportal.com/?opt=redirect&code=*", timeout=10000)
    print("✅ ログイン完了")
    print(f"📍 遷移先URL: {page.url}")

    # ✅ 通知ページへ遷移し、記事を明示的に待つ
    page.goto("https://dx.collaboportal.com/notifications", timeout=60000)
    page.wait_for_selector("article a > h2", timeout=60000)

    # 通知の抽出と保存
    items = extract_items(page)
    save_as_xml(items, OUTPUT_PATH)

    print("⏹ 処理終了。ブラウザを閉じます。")
    browser.close()
    
