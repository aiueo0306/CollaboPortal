from playwright.sync_api import sync_playwright
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urljoin
import random
import time
import json


# ============================================================
# 設定
# ============================================================

LOGIN_URL = "https://dx.collaboportal.com/"

USERNAME = "sato.sota@create-sd.co.jp"
PASSWORD = "sota0306!"

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
    # ブラウザConsoleログ
    # ========================================================

    def handle_console(msg):
        try:
            print(
                f"🖥 CONSOLE [{msg.type}]: "
                f"{msg.text}"
            )
        except Exception as e:
            print(
                "⚠ Consoleログ取得失敗:",
                e
            )

    page.on("console", handle_console)


    # ========================================================
    # JavaScriptエラー
    # ========================================================

    def handle_page_error(error):
        print(
            "💥 PAGE ERROR:",
            error
        )

    page.on(
        "pageerror",
        handle_page_error
    )


    # ========================================================
    # 通信失敗
    # ========================================================

    def handle_request_failed(request):
        try:
            print(
                "❌ REQUEST FAILED:",
                request.method,
                request.url,
                request.failure
            )
        except Exception as e:
            print(
                "⚠ requestfailed取得失敗:",
                e
            )

    page.on(
        "requestfailed",
        handle_request_failed
    )


    # ========================================================
    # APIレスポンス確認
    # ========================================================

    def handle_response(response):

        if "api.collaboportal.com" not in response.url:
            return

        print("")
        print("========== API RESPONSE ==========")

        print(
            "URL:",
            response.url
        )

        print(
            "STATUS:",
            response.status
        )

        try:
            content_type = response.headers.get(
                "content-type",
                ""
            )

            print(
                "CONTENT-TYPE:",
                content_type
            )

        except Exception as e:
            print(
                "⚠ Content-Type取得失敗:",
                e
            )

        try:
            body = response.text()

            print(
                "RESPONSE BODY:"
            )

            # ログが巨大にならないよう最大10000文字
            print(
                body[:10000]
            )

        except Exception as e:
            print(
                "⚠ レスポンス本文取得失敗:",
                e
            )

        print(
            "========== API RESPONSE END =========="
        )
        print("")


    page.on(
        "response",
        handle_response
    )


    # ========================================================
    # ログインページへアクセス
    # ========================================================

    print("")
    print("========== LOGIN START ==========")

    page.goto(
        LOGIN_URL,
        timeout=60000
    )

    print(
        "ログイン画面URL:",
        page.url
    )

    print(
        "ログイン画面TITLE:",
        page.title()
    )


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

    print(
        "✅ ログインボタンをクリックしました"
    )


    # ========================================================
    # ログイン後待機
    # ========================================================

    print(
        "⏳ ログイン後15秒待機..."
    )

    time.sleep(15)


    # ========================================================
    # 状態確認
    # ========================================================

    print("")
    print(
        "========== LOGIN RESULT =========="
    )

    print(
        "15秒後URL:",
        page.url
    )

    print(
        "15秒後TITLE:",
        page.title()
    )


    # ========================================================
    # 画面本文
    # ========================================================

    try:
        body_text = (
            page
            .locator("body")
            .inner_text()
        )

        print("")
        print(
            "---------- 画面本文 ----------"
        )

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
    # HTML基本状態
    # ========================================================

    try:
        html = page.content()

        print("")
        print(
            "---------- HTML STATUS ----------"
        )

        print(
            "HTML文字数:",
            len(html)
        )

        print(
            "bodyタグ数:",
            page.locator("body").count()
        )

        print(
            "#__layout数:",
            page.locator("#__layout").count()
        )

        print(
            "#__nuxt数:",
            page.locator("#__nuxt").count()
        )

        print(
            "scriptタグ数:",
            page.locator("script").count()
        )

        print(
            "div総数:",
            page.locator("div").count()
        )

    except Exception as e:
        print(
            "⚠ HTML確認失敗:",
            e
        )


    # ========================================================
    # Cookie確認
    # ========================================================

    print("")
    print(
        "---------- COOKIE ----------"
    )

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
    # localStorage確認
    # ========================================================

    print("")
    print(
        "---------- LOCAL STORAGE ----------"
    )

    try:
        local_storage = page.evaluate("""
            () => {
                const result = {};

                for (
                    let i = 0;
                    i < localStorage.length;
                    i++
                ) {
                    const key = localStorage.key(i);

                    result[key] = localStorage.getItem(key);
                }

                return result;
            }
        """)

        print(
            "localStorageキー数:",
            len(local_storage)
        )

        for key in local_storage.keys():
            print(
                "LOCALSTORAGE KEY:",
                key
            )

    except Exception as e:
        print(
            "⚠ localStorage取得失敗:",
            e
        )


    # ========================================================
    # sessionStorage確認
    # ========================================================

    print("")
    print(
        "---------- SESSION STORAGE ----------"
    )

    try:
        session_storage = page.evaluate("""
            () => {
                const result = {};

                for (
                    let i = 0;
                    i < sessionStorage.length;
                    i++
                ) {
                    const key = sessionStorage.key(i);

                    result[key] = sessionStorage.getItem(key);
                }

                return result;
            }
        """)

        print(
            "sessionStorageキー数:",
            len(session_storage)
        )

        for key in session_storage.keys():
            print(
                "SESSIONSTORAGE KEY:",
                key
            )

    except Exception as e:
        print(
            "⚠ sessionStorage取得失敗:",
            e
        )


    # ========================================================
    # DOM確認
    # ========================================================

    print("")
    print(
        "---------- DOM ----------"
    )

    print(
        "email入力欄数:",
        page.locator(
            "#email"
        ).count()
    )

    print(
        "password入力欄数:",
        page.locator(
            "#password"
        ).count()
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

    print(
        "aタグ総数:",
        page.locator(
            "a"
        ).count()
    )


    # ========================================================
    # ログイン状態判定
    # ========================================================

    print("")
    print(
        "---------- URL判定 ----------"
    )

    current_url = page.url

    if "login-id.dx-utility.com" in current_url:

        print(
            "❌ ログインページに戻っています"
        )

    elif (
        current_url.rstrip("/")
        == "https://dx.collaboportal.com"
    ):

        print(
            "✅ Collabo Portalトップページにいます"
        )

    elif "dx.collaboportal.com" in current_url:

        print(
            "✅ Collabo Portal内にいます"
        )

    else:

        print(
            "⚠ 想定外のURLです"
        )


    print("")
    print(
        "========== LOGIN RESULT END =========="
    )


    # ========================================================
    # 今回はここで終了
    # ========================================================

    print("")
    print(
        "🔍 今回はSPA/APIの状態確認のみ行います。"
    )

    print(
        "RSSファイルは更新しません。"
    )

    print(
        "⏹ 処理終了。ブラウザを閉じます。"
    )

    browser.close()
