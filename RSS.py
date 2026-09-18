from playwright.sync_api import sync_playwright
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urljoin
import random
import time

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

def extract_items(page):
    rows = page.locator("div.content_NR3Mk > article")
    count = rows.count()
    print(f"📦 発見した通知数: {count}")
    
    #import sys

    #print("ここまで実行")
    #sys.exit()
    
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
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--start-maximized",
            "--profile-directory=Default",
        ]
    )
    context = browser.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        java_script_enabled=True,
        bypass_csp=True,
        ignore_https_errors=True,
        locale="ja-JP",
    )
    page = context.new_page()

    # ✅ Bot検知対策: navigator や plugins を偽装
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['ja-JP', 'ja']});
    """)

    def handle_response(response):
        if "api.collaboportal.com" in response.url:
           print(f"🌐 API呼び出し: {response.url} ステータス: {response.status}")

    page.on("response", handle_response)
    
    # ログインページへアクセス
    page.goto(LOGIN_URL, timeout=60000)

    # ランダムな待機で人間ぽさUP
    delay = random.uniform(2, 4)
    print(f"⏳ メール入力前に {delay:.2f} 秒待機")
    time.sleep(delay)

    page.wait_for_selector('#email', timeout=60000)
    page.fill('#email', USERNAME)

    delay = random.uniform(1, 3)
    print(f"⏳ パスワード入力前に {delay:.2f} 秒待機")
    time.sleep(delay)

    page.wait_for_selector('#password', timeout=60000)
    page.fill('#password', PASSWORD)

    delay = random.uniform(1, 3)
    print(f"⏳ ログインボタンクリック前に {delay:.2f} 秒待機")
    time.sleep(delay)

    page.get_by_role("button", name="ログインする").click()

    # ✅ ログイン後のリダイレクト完了を待機
    page.wait_for_url("https://dx.collaboportal.com/?opt=redirect&code=*", timeout=60000)
    print("✅ ログイン完了")

    print("ログイン後URL:", page.url)

    cookies = context.cookies()
    print("Cookie数:", len(cookies))

    for c in cookies:
        print("COOKIE:", c["name"], c["domain"])
    
    page.wait_for_url("https://dx.collaboportal.com/", timeout=60000)

    delay = random.uniform(2, 4)
    print(f"⏳ 通知ページ移動前に {delay:.2f} 秒待機")
    time.sleep(delay)

    # ✅ SPAの画面遷移を使って通知ページへ移動
    notification_link = page.locator('a[href="/notifications"]').first

    print("通知リンク数:", page.locator('a[href="/notifications"]').count())

    notification_link.click()

    page.wait_for_url("**/notifications", timeout=60000)

    print("✅ 通知ページへ移動")
    print("通知ページURL:", page.url)
    print("通知ページTITLE:", page.title())
    
    if "login-id.dx-utility.com" in page.url:
        print("❌ 認証状態が維持されておらず、ログイン画面へ戻されています")
    else:
        print("✅ 認証状態は維持されています")
    
    title = page.title()
    print(f"✅ 現在のページタイトル: {title}")
    
    print("⏳ 10秒間待機中...")
    time.sleep(10)

    title = page.title()
    print(f"✅ 現在のページタイトル: {title}")


        # ===== デバッグ情報 =====
    print("\n========== DEBUG START ==========")
    print(f"URL: {page.url}")
    print(f"TITLE: {page.title()}")

    print(f"article総数: {page.locator('article').count()}")
    print(f"content_NR3Mk数: {page.locator('div.content_NR3Mk').count()}")
    print(f"対象article数: {page.locator('div.content_NR3Mk > article').count()}")

    # content_NR3Mk が存在する場合、その中身をログに表示
    content = page.locator("div.content_NR3Mk")

    if content.count() > 0:
        print("\n--- content_NR3Mk 内部HTML ---")
        try:
            html = content.first.inner_html()
            print(html[:10000])
        except Exception as e:
            print(f"HTML取得失敗: {e}")
    else:
        print("\n⚠ content_NR3Mk 自体が見つかりません")

    print("========== DEBUG END ==========\n")

    
    # 通知の抽出と保存
    items = extract_items(page)
    save_as_xml(items, OUTPUT_PATH)

    print("⏹ 処理終了。ブラウザを閉じます。")
    browser.close()
