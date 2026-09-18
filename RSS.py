from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urljoin
import time


# ============================================================
# 設定
# ============================================================

LOGIN_URL = "https://dx.collaboportal.com/"

USERNAME = "sato.sota@create-sd.co.jp"
PASSWORD = "YOUR_PASSWORD"

BASE_URL = "https://dx.collaboportal.com"
NOTIFICATIONS_URL = BASE_URL + "/notifications"

OUTPUT_DIR = "rss_output"
OUTPUT_FILENAME = "notifications.xml"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)


# ============================================================
# RSS XML保存
# ============================================================

def save_as_xml(items, output_path):

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )

    rss = ET.Element(
        "rss",
        version="2.0"
    )

    channel = ET.SubElement(
        rss,
        "channel"
    )

    ET.SubElement(
        channel,
        "title"
    ).text = "Collabo Portal Notifications"

    ET.SubElement(
        channel,
        "link"
    ).text = NOTIFICATIONS_URL

    ET.SubElement(
        channel,
        "description"
    ).text = "COLLABO Portal 通知一覧"

    for item in items:

        entry = ET.SubElement(
            channel,
            "item"
        )

        ET.SubElement(
            entry,
            "title"
        ).text = item["title"]

        ET.SubElement(
            entry,
            "link"
        ).text = item["link"]

        ET.SubElement(
            entry,
            "description"
        ).text = item["description"]

        ET.SubElement(
            entry,
            "pubDate"
        ).text = item["pub_date"].strftime(
            "%a, %d %b %Y %H:%M:%S +0000"
        )

    tree = ET.ElementTree(rss)

    tree.write(
        output_path,
        encoding="utf-8",
        xml_declaration=True
    )

    print(
        f"✅ RSS保存完了: {output_path}"
    )


# ============================================================
# 通知取得
# ============================================================

def extract_items(page):

    rows = page.locator(
        "div.content_NR3Mk > article"
    )

    count = rows.count()

    print(
        f"📦 発見した通知数: {count}"
    )

    items = []

    for i in range(count):

        row = rows.nth(i)

        try:

            title = (
                row
                .locator("a > h2")
                .first
                .inner_text()
                .strip()
            )

            href = (
                row
                .locator("a")
                .first
                .get_attribute("href")
            )

            if href:
                link = urljoin(
                    BASE_URL,
                    href
                )
            else:
                link = NOTIFICATIONS_URL

            items.append({
                "title": title,
                "link": link,
                "description": "",
                "pub_date": datetime.now(
                    timezone.utc
                )
            })

            print(
                f"  {i + 1}. {title}"
            )

        except Exception as e:

            print(
                f"⚠ 通知{i + 1}取得失敗: {e}"
            )

    return items


# ============================================================
# メイン
# ============================================================

with sync_playwright() as p:

    # ========================================================
    # Chromium起動
    #
    # AutomationControlled等の偽装設定は使用しない
    # User-AgentもPlaywright標準に任せる
    # ========================================================

    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
    )

    context = browser.new_context(
        viewport={
            "width": 1366,
            "height": 768
        },
        locale="ja-JP",
        ignore_https_errors=True
    )

    page = context.new_page()


    # ========================================================
    # Consoleエラー
    # ========================================================

    def console_handler(msg):

        if msg.type in [
            "error",
            "warning"
        ]:

            print(
                f"🖥 CONSOLE [{msg.type}]: "
                f"{msg.text}"
            )

    page.on(
        "console",
        console_handler
    )


    # ========================================================
    # JavaScriptエラー
    # ========================================================

    def page_error_handler(error):

        print(
            f"💥 PAGE ERROR: {error}"
        )

    page.on(
        "pageerror",
        page_error_handler
    )


    # ========================================================
    # 通信失敗
    # ========================================================

    def request_failed_handler(request):

        # Google Analytics失敗は無視
        if "google-analytics.com" in request.url:
            return

        print(
            "❌ REQUEST FAILED:",
            request.method,
            request.url,
            request.failure
        )

    page.on(
        "requestfailed",
        request_failed_handler
    )


    # ========================================================
    # URL遷移監視
    # ========================================================

    def frame_navigated_handler(frame):

        if frame == page.main_frame:

            print(
                "➡ URL:",
                frame.url
            )

    page.on(
        "framenavigated",
        frame_navigated_handler
    )


    # ========================================================
    # 開始
    # ========================================================

    print("")
    print(
        "========== LOGIN START =========="
    )

    page.goto(
        LOGIN_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    print(
        "初期URL:",
        page.url
    )


    # ========================================================
    # ログイン画面
    # ========================================================

    try:

        page.locator(
            "#email"
        ).wait_for(
            state="visible",
            timeout=60000
        )

    except PlaywrightTimeoutError:

        print(
            "❌ メールアドレス入力欄が表示されません"
        )

        print(
            "現在URL:",
            page.url
        )

        browser.close()
        raise


    print(
        "✅ ログイン画面表示"
    )


    # ========================================================
    # 認証情報入力
    # ========================================================

    page.locator(
        "#email"
    ).fill(
        USERNAME
    )

    time.sleep(1)

    page.locator(
        "#password"
    ).fill(
        PASSWORD
    )

    time.sleep(1)


    # ========================================================
    # ログイン
    # ========================================================

    page.get_by_role(
        "button",
        name="ログインする"
    ).click()

    print(
        "✅ ログインボタンをクリック"
    )


    # ========================================================
    # 認証処理を監視
    #
    # 特定のcallback URLをwait_for_urlで待たない。
    # SPAの認証処理が完了するまで状態を見る。
    # ========================================================

    print(
        "⏳ Auth0 / SPA認証完了待機..."
    )

    authenticated = False

    start_time = time.time()

    last_url = ""

    while time.time() - start_time < 60:

        current_url = page.url

        if current_url != last_url:

            print(
                "🔗 現在URL:",
                current_url
            )

            last_url = current_url


        # ----------------------------------------------------
        # Collabo Portalへ戻っている
        # ----------------------------------------------------

        if (
            current_url.startswith(
                BASE_URL
            )
            and "login-id.dx-utility.com"
            not in current_url
            and "id.dx-utility.com"
            not in current_url
        ):

            title = ""

            try:
                title = page.title()
            except Exception:
                pass

            print(
                "📄 TITLE:",
                title
            )


            # -----------------------------------------------
            # SPAのDOMが生成されたか
            # -----------------------------------------------

            try:

                layout_count = (
                    page
                    .locator("#__layout")
                    .count()
                )

                link_count = (
                    page
                    .locator("a")
                    .count()
                )

                body_text = (
                    page
                    .locator("body")
                    .inner_text(
                        timeout=2000
                    )
                    .strip()
                )

            except Exception:

                layout_count = 0
                link_count = 0
                body_text = ""


            print(
                "   layout:",
                layout_count,
                "links:",
                link_count,
                "body:",
                len(body_text)
            )


            # -----------------------------------------------
            # 認証後SPAが実際に描画されたと判断
            # -----------------------------------------------

            if (
                layout_count > 0
                or link_count > 0
                or len(body_text) > 0
            ):

                authenticated = True

                print(
                    "✅ Collabo Portal SPA描画確認"
                )

                break


        time.sleep(2)


    # ========================================================
    # 認証結果
    # ========================================================

    print("")
    print(
        "========== AUTH RESULT =========="
    )

    print(
        "最終URL:",
        page.url
    )

    print(
        "TITLE:",
        page.title()
    )

    print(
        "認証状態:",
        authenticated
    )

    print(
        "================================="
    )


    # ========================================================
    # 認証失敗
    # ========================================================

    if not authenticated:

        print("")
        print(
            "❌ Collabo PortalのSPA描画まで到達できませんでした。"
        )

        print(
            "RSSは更新しません。"
        )

        browser.close()

        raise RuntimeError(
            "Collabo Portal authentication failed"
        )


    # ========================================================
    # 認証成功後 少し安定待ち
    # ========================================================

    print(
        "⏳ SPA安定待機..."
    )

    time.sleep(5)


    # ========================================================
    # 通知リンク確認
    # ========================================================

    notification_link = page.locator(
        'a[href="/notifications"]'
    )

    notification_link_count = (
        notification_link.count()
    )

    print(
        "🔔 通知リンク数:",
        notification_link_count
    )


    # ========================================================
    # SPAリンクがある場合はクリック
    # ========================================================

    if notification_link_count > 0:

        print(
            "🔔 SPA内の通知リンクをクリック"
        )

        notification_link.first.click()

        try:

            page.wait_for_url(
                "**/notifications*",
                timeout=30000
            )

        except PlaywrightTimeoutError:

            print(
                "⚠ URL待機タイムアウト"
            )

            print(
                "現在URL:",
                page.url
            )


    # ========================================================
    # 通知リンクが見つからない場合
    #
    # 認証済み状態なので直接遷移を試す
    # ========================================================

    else:

        print(
            "⚠ 通知リンクが見つからないため"
            "認証済みContextで直接遷移します"
        )

        page.goto(
            NOTIFICATIONS_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )


    # ========================================================
    # 通知ページ確認
    # ========================================================

    print("")
    print(
        "========== NOTIFICATIONS =========="
    )

    print(
        "URL:",
        page.url
    )

    print(
        "TITLE:",
        page.title()
    )


    # ========================================================
    # 通知記事の描画待ち
    # ========================================================

    try:

        page.locator(
            "div.content_NR3Mk > article"
        ).first.wait_for(
            state="attached",
            timeout=30000
        )

        print(
            "✅ 通知記事DOMを確認"
        )

    except PlaywrightTimeoutError:

        print(
            "⚠ 30秒待っても通知記事が表示されません"
        )


    # ========================================================
    # 最終DOM診断
    # ========================================================

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
        "対象article数:",
        page.locator(
            "div.content_NR3Mk > article"
        ).count()
    )

    print(
        "====================================="
    )


    # ========================================================
    # 通知取得
    # ========================================================

    items = extract_items(
        page
    )


    # ========================================================
    # 0件ならRSSを上書きしない
    # ========================================================

    if len(items) == 0:

        print("")
        print(
            "❌ 通知を1件も取得できませんでした。"
        )

        print(
            "既存RSSを保護するため"
            "notifications.xmlは更新しません。"
        )

        browser.close()

        raise RuntimeError(
            "No notifications found"
        )


    # ========================================================
    # RSS生成
    # ========================================================

    save_as_xml(
        items,
        OUTPUT_PATH
    )

    print("")
    print(
        f"🎉 {len(items)}件の通知をRSSへ出力しました"
    )


    # ========================================================
    # 終了
    # ========================================================

    browser.close()

    print(
        "========== COMPLETE =========="
    )
