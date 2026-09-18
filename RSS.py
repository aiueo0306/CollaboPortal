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
# RSS保存
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
                .locator("h2")
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

            link = (
                urljoin(BASE_URL, href)
                if href
                else NOTIFICATIONS_URL
            )

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
    # ★ GitHub Runner上のGoogle Chromeを使用
    #
    # Playwright付属Chromiumではなく
    # channel="chrome" を指定
    # ========================================================

    print("")
    print(
        "========== BROWSER START =========="
    )

    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
    )

    print(
        "✅ Google Chrome起動"
    )

    print(
        "Browser version:",
        browser.version
    )

    print(
        "==================================="
    )


    # ========================================================
    # Context
    # ========================================================

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
    # 状態
    # ========================================================

    callback_detected = False
    callback_url = None


    # ========================================================
    # URL遷移監視
    # ========================================================

    def frame_navigated_handler(frame):

        global callback_detected
        global callback_url

        if frame != page.main_frame:
            return

        url = frame.url

        print(
            "➡ URL:",
            url
        )

        # ----------------------------------------------------
        # Collabo Portal callback
        # ----------------------------------------------------

        if (
            url.startswith(
                "https://dx.collaboportal.com/"
            )
            and "opt=redirect" in url
            and "code=" in url
        ):

            callback_detected = True
            callback_url = url

            print("")
            print(
                "🎯 認証callbackを検知"
            )

            print(
                "CALLBACK URL:",
                url
            )

            print("")


    page.on(
        "framenavigated",
        frame_navigated_handler
    )


    # ========================================================
    # Console
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
            "💥 PAGE ERROR:",
            error
        )


    page.on(
        "pageerror",
        page_error_handler
    )


    # ========================================================
    # 通信失敗
    # ========================================================

    def request_failed_handler(request):

        if "google-analytics.com" in request.url:
            return

        print("")
        print(
            "========== REQUEST FAILED =========="
        )

        print(
            "METHOD:",
            request.method
        )

        print(
            "URL:",
            request.url
        )

        print(
            "FAILURE:",
            request.failure
        )

        print(
            "========== REQUEST FAILED END =========="
        )

        print("")


    page.on(
        "requestfailed",
        request_failed_handler
    )


    # ========================================================
    # HTTP 4xx / 5xx
    # ========================================================

    def response_handler(response):

        try:

            if response.status < 400:
                return

            print("")
            print(
                "========== HTTP ERROR =========="
            )

            print(
                "STATUS:",
                response.status
            )

            print(
                "URL:",
                response.url
            )

            try:

                print(
                    "METHOD:",
                    response.request.method
                )

            except Exception:
                pass

            try:

                print(
                    "CONTENT-TYPE:",
                    response.headers.get(
                        "content-type",
                        ""
                    )
                )

            except Exception:
                pass

            # ------------------------------------------------
            # body取得
            #
            # callback処理と競合する可能性があるので
            # 失敗しても処理自体は止めない
            # ------------------------------------------------

            try:

                body = response.text()

                print(
                    "BODY:"
                )

                print(
                    body[:3000]
                )

            except Exception as e:

                print(
                    "BODY取得失敗:",
                    e
                )

            print(
                "========== HTTP ERROR END =========="
            )

            print("")

        except Exception as e:

            print(
                "HTTP ERROR監視失敗:",
                e
            )


    page.on(
        "response",
        response_handler
    )


    # ========================================================
    # LOGIN START
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
    # ID入力
    # ========================================================

    page.locator(
        "#email"
    ).fill(
        USERNAME
    )

    page.wait_for_timeout(
        500
    )


    # ========================================================
    # Password入力
    # ========================================================

    page.locator(
        "#password"
    ).fill(
        PASSWORD
    )

    page.wait_for_timeout(
        500
    )


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
    # 認証処理待機
    #
    # time.sleep()ではなくPlaywright側のwaitを使用
    # ========================================================

    print(
        "⏳ Auth0認証処理待機..."
    )

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
        # callback検知済み
        # ----------------------------------------------------

        if callback_detected:

            print(
                "✅ callback検知済み"
            )

            break


        # ----------------------------------------------------
        # callbackイベントより先に
        # Collabo Portalへ戻った場合も成功扱い
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

            # 最初のトップページ表示直後は除外
            if time.time() - start_time > 2:

                print(
                    "✅ Collabo Portalへの帰還を確認"
                )

                callback_detected = True
                callback_url = current_url

                break


        page.wait_for_timeout(
            250
        )


    # ========================================================
    # 認証結果
    # ========================================================

    print("")
    print(
        "========== AUTH RESULT =========="
    )

    print(
        "callback検知:",
        callback_detected
    )

    print(
        "現在URL:",
        page.url
    )

    try:

        print(
            "TITLE:",
            page.title()
        )

    except Exception:
        pass

    print(
        "================================="
    )


    # ========================================================
    # 認証失敗
    # ========================================================

    if not callback_detected:

        print("")
        print(
            "❌ Google Chromeでも認証callbackを確認できませんでした"
        )

        print(
            "RSSは更新しません"
        )

        # responseイベントのログが出切る時間を少し確保
        page.wait_for_timeout(
            2000
        )

        browser.close()

        raise RuntimeError(
            "Authentication callback not detected"
        )


    # ========================================================
    # 認証成功直後Cookie
    # ========================================================

    print("")
    print(
        "========== COOKIES =========="
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
            "|",
            cookie["domain"]
        )

    print(
        "============================="
    )


    # ========================================================
    # SPA処理を待つ
    # ========================================================

    print("")
    print(
        "⏳ Collabo Portal SPA初期化待機..."
    )

    spa_ready = False

    start_time = time.time()

    while time.time() - start_time < 30:

        current_url = page.url


        # ----------------------------------------------------
        # ログインページへ戻った
        # ----------------------------------------------------

        if (
            "login-id.dx-utility.com"
            in current_url
        ):

            print(
                "❌ SPA初期化中にログインページへ戻りました"
            )

            break


        # ----------------------------------------------------
        # Collabo Portal
        # ----------------------------------------------------

        if current_url.startswith(
            BASE_URL
        ):

            try:

                links = page.locator(
                    "a"
                ).count()

                divs = page.locator(
                    "div"
                ).count()

                notification_links = (
                    page
                    .locator(
                        'a[href="/notifications"]'
                    )
                    .count()
                )

                body_text = (
                    page
                    .locator("body")
                    .inner_text(
                        timeout=1000
                    )
                    .strip()
                )

                print(
                    "SPA状態:",
                    "a=",
                    links,
                    "div=",
                    divs,
                    "notification=",
                    notification_links,
                    "body=",
                    len(body_text)
                )


                # ------------------------------------------------
                # 通知リンクが見つかれば最も確実
                # ------------------------------------------------

                if notification_links > 0:

                    spa_ready = True

                    print(
                        "✅ 通知リンクを確認"
                    )

                    break


                # ------------------------------------------------
                # SPA自体が描画された場合
                # ------------------------------------------------

                if (
                    links > 0
                    and divs > 5
                    and len(body_text) > 0
                ):

                    spa_ready = True

                    print(
                        "✅ SPA描画を確認"
                    )

                    break

            except Exception as e:

                print(
                    "SPA確認失敗:",
                    e
                )


        page.wait_for_timeout(
            500
        )


    # ========================================================
    # SPA結果
    # ========================================================

    print("")
    print(
        "========== SPA RESULT =========="
    )

    print(
        "SPA ready:",
        spa_ready
    )

    print(
        "URL:",
        page.url
    )

    try:

        print(
            "TITLE:",
            page.title()
        )

    except Exception:
        pass

    print(
        "================================"
    )


    # ========================================================
    # 通知ページへ移動
    #
    # まずSPAリンクを優先
    # ========================================================

    notification_link = page.locator(
        'a[href="/notifications"]'
    )

    notification_link_count = (
        notification_link.count()
    )


    print("")
    print(
        "🔔 通知リンク数:",
        notification_link_count
    )


    if notification_link_count > 0:

        print(
            "🔔 通知リンクをクリック"
        )

        try:

            notification_link.first.click(
                timeout=15000
            )

            page.wait_for_timeout(
                2000
            )

        except Exception as e:

            print(
                "⚠ 通知リンククリック失敗:",
                e
            )


    # ========================================================
    # リンクで移動できなければ直接遷移
    # ========================================================

    if "/notifications" not in page.url:

        print(
            "➡ 認証済みContextで通知URLへ直接遷移"
        )

        try:

            page.goto(
                NOTIFICATIONS_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

        except Exception as e:

            print(
                "⚠ 通知ページ直接遷移エラー:",
                e
            )


    # ========================================================
    # 通知ページ状態
    # ========================================================

    print("")
    print(
        "========== NOTIFICATIONS =========="
    )

    print(
        "URL:",
        page.url
    )

    try:

        print(
            "TITLE:",
            page.title()
        )

    except Exception:
        pass


    # ========================================================
    # 再ログインチェック
    # ========================================================

    if (
        "login-id.dx-utility.com"
        in page.url
    ):

        print(
            "❌ 通知ページ移動時に認証が失われました"
        )

        browser.close()

        raise RuntimeError(
            "Authentication lost before notifications"
        )


    # ========================================================
    # 通知DOM待機
    # ========================================================

    print(
        "⏳ 通知article待機..."
    )

    try:

        page.locator(
            "div.content_NR3Mk > article"
        ).first.wait_for(
            state="attached",
            timeout=30000
        )

        print(
            "✅ 通知articleを確認"
        )

    except PlaywrightTimeoutError:

        print(
            "⚠ 通知article待機タイムアウト"
        )


    # ========================================================
    # DOM診断
    # ========================================================

    print("")
    print(
        "========== NOTIFICATION DOM =========="
    )

    print(
        "URL:",
        page.url
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
        "対象article数:",
        page.locator(
            "div.content_NR3Mk > article"
        ).count()
    )

    print(
        "aタグ数:",
        page.locator(
            "a"
        ).count()
    )

    print(
        "======================================"
    )


    # ========================================================
    # 通知取得
    # ========================================================

    items = extract_items(
        page
    )


    # ========================================================
    # 0件
    # ========================================================

    if len(items) == 0:

        print("")
        print(
            "❌ 通知を取得できませんでした"
        )

        print(
            "既存RSSを保護するため更新しません"
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
        f"🎉 {len(items)}件をRSSへ出力しました"
    )


    # ========================================================
    # 終了
    # ========================================================

    browser.close()

    print(
        "========== COMPLETE =========="
    )
