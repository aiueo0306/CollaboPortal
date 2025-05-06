from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

EMAIL = "sato.sota@create-sd.co.jp"
PASSWORD = "sotasato!"
START_URL = "https://dx.collaboportal.com/notifications"
BASE_URL = "https://dx.collaboportal.com"
DEFAULT_LINK = START_URL

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("DXポータル 通知")
    fg.link(href=DEFAULT_LINK)
    fg.description("DXポータルサイトの通知一覧")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
        entry.guid(guid_value, permalink=False)
        entry.pubDate(item['pub_date'])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")

def extract_items(page):
    items = []
    rows = page.locator("#__layout article")
    count = rows.count()
    print(f"📦 発見した通知数: {count}")

    for i in range(count):
        row = rows.nth(i)
        try:
            title = row.locator(".kb-title").inner_text().strip()
            description = row.locator(".kb-description").inner_text().strip()
            link_elem = row.locator("a")
            link = DEFAULT_LINK
            if link_elem.count() > 0:
                href = link_elem.first.get_attribute("href")
                if href:
                    link = urljoin(BASE_URL, href)
            time_elem = row.locator("sn-time-ago > time")
            time_str = time_elem.get_attribute("title")
            pub_date = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) if time_str else datetime.now(timezone.utc)

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

# ===== 実行ブロック =====
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("▶ ポータルサイトにアクセス中...")
        page.goto(START_URL)

        page.wait_for_url("https://login-id.dx-utility.com/login*", timeout=20000)
        print("▶ ログイン情報を入力中...")
        page.fill('input#email', EMAIL)
        page.wait_for_selector('input#password', timeout=10000)
        page.fill('input#password', PASSWORD)
        page.get_by_role("button", name="ログインする").click()

        page.wait_for_url("https://dx.collaboportal.com*", timeout=20000)
        print("✅ ログイン完了。ページ取得中...")
        page.wait_for_load_state("networkidle")

        items = extract_items(page)

        if not items:
            print("⚠ 通知が取得できませんでした。")

        rss_path = "rss_output/dxportal_notifications.xml"
        generate_rss(items, rss_path)

    finally:
        browser.close()
