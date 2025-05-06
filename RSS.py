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

# 保存先のGitHub上のrss_outputパス（ローカル上で管理されている前提）
OUTPUT_DIR = "rss_output"
OUTPUT_FILENAME = "notifications.xml"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

# 通知のXML保存関数
def save_as_xml(items, output_path):
    # 保存先のフォルダがなければ作成
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
    page.wait_for_selector("#__layout article", timeout=60000)
    rows = page.locator("#__layout article")
    count = rows.count()
    print(f"📦 発見した通知数: {count}")

    items = []
    for i in range(count):
        row = rows.nth(i)
        try:
            title = row.locator("a > h2").inner_text().strip()
            description = ""
            link_elem = row.locator("a")
            href = link_elem.first.get_attribute("href")
            link = urljoin(BASE_URL, href) if href else DEFAULT_LINK
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
    context = browser.new_context()
    page = context.new_page()

    page.goto(LOGIN_URL, timeout=60000)
    page.wait_for_selector('#email', timeout=60000)
    page.fill('#email', USERNAME)
    page.wait_for_selector('#password', timeout=60000)
    page.fill('#password', PASSWORD)
    page.get_by_role("button", name="ログインする").click()

    page.wait_for_url("https://dx.collaboportal.com/**", timeout=60000)
    print("✅ ログイン完了")

    page.goto("https://dx.collaboportal.com/notifications", timeout=60000)

    items = extract_items(page)
    save_as_xml(items, OUTPUT_PATH)

    print("⏹ 処理終了。ブラウザを閉じます。")
    browser.close()
