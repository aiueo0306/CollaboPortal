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

# GitHub Secretsを使う場合
USERNAME = os.getenv("COLLABO_USERNAME", "YOUR_USERNAME")
PASSWORD = os.getenv("COLLABO_PASSWORD", "YOUR_PASSWORD")

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
    # ログインボタン
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

    print("✅ ログインボタンをクリックしました")


    # ========================================================
    # ログイン後の状態確認
    #
    # 今回はwait_for_urlを使わず
    # 実際にどこへ遷移したか確認
    # ========================================================

    print("⏳ ログイン後10秒待機...")
    time.sleep(10)

    print("")
    print("========== LOGIN RESULT ==========")

    print(
        "10秒後URL:",
        page.url
    )

    print(
        "10秒後TITLE:",
        page.title()
    )


    # ========================================================
    # 画面本文を取得
    # ========================================================

    try:
        body_text = page.locator("body").inner_text()

        print("")
        print("---------- 画面本文 ----------")

        print(
            body_text[:5000]
        )

        print(
            "---------- 画面本文ここまで ----------"
        )

    except Exception as e:

        print(
            "⚠ 画面本文取得失敗:",
            e
        )


    # ========================================================
    # URL判定
    # ========================================================

    current_url = page.url

    print("")
    print("---------- URL判定 ----------")

    if "login-id.dx-utility.com" in current_url:

        print(
            "❌ ログインページに留まっています"
        )

    elif (
        "dx.collaboportal.com" in current_url
        and "opt=redirect" in current_url
    ):

        print(
            "✅ 認証コード付きURLまで到達しています"
        )

    elif current_url.rstrip("/") == "https://dx.collaboportal.com":

        print(
            "✅ Collabo Portalトップページまで到達しています"
        )

    elif "dx.collaboportal.com" in current_url:

        print(
            "✅ Collabo Portal内のページへ移動しています"
        )

    else:

        print(
            "⚠ 想定外のURLです"
        )


    # ========================================================
    # Cookie確認
    # ========================================================

    print("")
    print("---------- COOKIE ----------")

    cookies = context.cookies()

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


    # ========================================================
    # DOM確認
    # ========================================================

    print("")
    print("---------- DOM ----------")

    print(
        "email入力欄数:",
        page.locator("#email").count()
    )

    print(
        "password入力欄数:",
        page.locator("#password").count()
    )

    print(
        "通知リンク数:",
        page.locator(
            'a[href="/notifications"]'
        ).count()
    )

    print(
        "article総数:",
        page.locator(
            "article"
        ).count()
    )

    print(
        "content_NR3Mk数:",
        page.locator(
            "div.content_NR3Mk"
        ).count()
    )

    print("")
    print("========== LOGIN RESULT END ==========")


    # ========================================================
    # 今回はここで終了
    #
    # RSSは0件で上書きしない
    # ========================================================

    print("")
    print(
        "🔍 今回はログイン状態確認のみ行いました。"
    )

    print(
        "RSSファイルの更新は行いません。"
    )

    print(
        "⏹ 処理終了。ブラウザを閉じます。"
    )

    browser.close()
