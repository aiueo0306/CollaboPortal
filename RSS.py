from playwright.sync_api import sync_playwright
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urljoin
import random
import time

# ============================================================
# 設定
# ============================================================

LOGIN_URL = "https://dx.collaboportal.com/"
USERNAME = "YOUR_USERNAME"
PASSWORD = "YOUR_PASSWORD"

BASE_URL = "https://dx.collaboportal.com"
DEFAULT_LINK = BASE_URL + "/notifications"

OUTPUT_DIR = "rss_output"
OUTPUT_FILENAME = "notifications.xml"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)


# ============================================================
# RSS XML保存
# ============================================================

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

        ET.SubElement(entry, "pubDate").text = (
            item["pub_date"].strftime(
                "%a, %d %b %Y %H:%M:%S +0000"
            )
        )

    tree = ET.ElementTree(rss)

    tree.write(
        output_path,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"✅ XMLファイルを保存しました: {output_path}")


# ============================================================
# 通知取得
# ============================================================

def extract_items(page):

    rows = page.locator("div.content_NR3Mk > article")

    count = rows.count()

    print(f"📦 発見した通知数: {count}")

    items = []

    for i in range(count):

        row = rows.nth(i)

        try:

            title = (
                row
                .locator("a > h2")
                .inner_text()
                .strip()
            )

            link_elem = row.locator("a")

            href = link_elem.first.get_attribute("href")

            if href:
                link = urljoin(BASE_URL, href)
            else:
                link = DEFAULT_LINK

            description = ""

            pub_date = datetime.now(timezone.utc)

            items.append({
                "title": title,
                "link": link,
                "description": description,
                "pub_date": pub_date
            })

        except Exception as e:

            print(
                f"⚠ 通知{i + 1}の解析に失敗: {e}"
            )

    return items


# ============================================================
# メイン処理
# ============================================================

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
        viewport={
            "width": 1366,
            "height": 768
        },
        user_agent=(
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/124.0.0.0 "
            "Safari/537.36"
        ),
        java_script_enabled=True,
        bypass_csp=True,
        ignore_https_errors=True,
        locale="ja-JP",
    )

    page = context.new_page()


    # ========================================================
    # Bot検知対策
    # ========================================================

    page.add_init_script("""
        Object.defineProperty(
            navigator,
            'webdriver',
            {get: () => undefined}
        );

        Object.defineProperty(
            navigator,
            'plugins',
            {get: () => [1, 2, 3, 4, 5]}
        );

        Object.defineProperty(
            navigator,
            'languages',
            {get: () => ['ja-JP', 'ja']}
        );
    """)


    # ========================================================
    # API通信ログ
    # ========================================================

    def handle_response(response):

        if "api.collaboportal.com" in response.url:

            print(
                f"🌐 API呼び出し: "
                f"{response.url} "
                f"ステータス: {response.status}"
            )

    page.on("response", handle_response)


    # ========================================================
    # ログインページへアクセス
    # ========================================================

    print("========== LOGIN START ==========")

    page.goto(
        LOGIN_URL,
        timeout=60000
    )

    print("ログイン画面URL:", page.url)
    print("ログイン画面TITLE:", page.title())


    # ========================================================
    # メールアドレス入力
    # ========================================================

    delay = random.uniform(2, 4)

    print(
        f"⏳ メール入力前に "
        f"{delay:.2f} 秒待機"
    )

    time.sleep(delay)

    page.wait_for_selector(
        "#email",
        timeout=60000
    )

    page.fill(
        "#email",
        USERNAME
    )


    # ========================================================
    # パスワード入力
    # ========================================================

    delay = random.uniform(1, 3)

    print(
        f"⏳ パスワード入力前に "
        f"{delay:.2f} 秒待機"
    )

    time.sleep(delay)

    page.wait_for_selector(
        "#password",
        timeout=60000
    )

    page.fill(
        "#password",
        PASSWORD
    )


    # ========================================================
    # ログイン
    # ========================================================

    delay = random.uniform(1, 3)

    print(
        f"⏳ ログインボタンクリック前に "
        f"{delay:.2f} 秒待機"
    )

    time.sleep(delay)

    page.get_by_role(
        "button",
        name="ログインする"
    ).click()


    # ========================================================
    # 認証コード付きURLを待つ
    # ========================================================

    page.wait_for_url(
        "https://dx.collaboportal.com/?opt=redirect&code=*",
        timeout=60000
    )

    print("✅ 認証コード付きURLへ到達")
    print("認証直後URL:", page.url)


    # ========================================================
    # Collabo Portalトップページを待つ
    # ========================================================

    page.wait_for_url(
        "https://dx.collaboportal.com/",
        timeout=60000
    )

    print("✅ Collabo Portalトップページへ到達")
    print("トップページURL:", page.url)
    print("トップページTITLE:", page.title())


    # ========================================================
    # Cookie確認
    # ========================================================

    cookies = context.cookies()

    print("")
    print("========== COOKIE ==========")

    print(
        "Cookie数:",
        len(cookies)
    )

    for cookie in cookies:

        print(
            "COOKIE:",
            cookie["name"],
            cookie["domain"]
        )

    print("============================")
    print("")


    # ========================================================
    # 認証状態が安定するか確認
    #
    # ★ここでは通知ページへ移動しない
    # ★10秒間トップページの状態を確認する
    # ========================================================

    print(
        "⏳ ログイン状態確認のため10秒待機..."
    )

    time.sleep(10)


    # ========================================================
    # 10秒後の状態
    # ========================================================

    print("")
    print("========== LOGIN DEBUG ==========")

    print(
        "10秒後URL:",
        page.url
    )

    print(
        "10秒後TITLE:",
        page.title()
    )

    notification_links = page.locator(
        'a[href="/notifications"]'
    )

    logout_links = page.locator(
        'a[href*="/logout"]'
    )

    print(
        "通知リンク数:",
        notification_links.count()
    )

    print(
        "ログアウトリンク数:",
        logout_links.count()
    )

    print(
        "article総数:",
        page.locator("article").count()
    )

    print(
        "content_NR3Mk数:",
        page.locator(
            "div.content_NR3Mk"
        ).count()
    )


    # ========================================================
    # ログイン画面へ戻されていないか確認
    # ========================================================

    if "login-id.dx-utility.com" in page.url:

        print(
            "❌ 10秒以内にログイン画面へ戻されました"
        )

    elif "dx.collaboportal.com" in page.url:

        print(
            "✅ Collabo Portal内に留まっています"
        )

    else:

        print(
            "⚠ 想定外のURLへ移動しています"
        )

    print("========== DEBUG END ==========")


    # ========================================================
    # 今回は原因調査のため通知ページへ移動しない
    # ========================================================

    print("")
    print(
        "🔍 今回は認証状態確認のため、"
        "通知ページへの移動・RSS更新は実行しません。"
    )

    print(
        "⏹ 処理終了。ブラウザを閉じます。"
    )

    browser.close()
