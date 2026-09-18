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
PASSWORD = "SOTA0306!"

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
    # Chromium
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
    # 状態管理
    # ========================================================

    callback_detected = False
    callback_url = None

    collabo_top_detected = False


    # ========================================================
    # URL遷移監視
    # ========================================================

    def frame_navigated_handler(frame):

        global callback_detected
        global callback_url
        global collabo_top_detected

        if frame != page.main_frame:
            return

        url = frame.url

        print(
            "➡ URL:",
            url
        )

        # ----------------------------------------------------
        # 認証callback検知
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

        # ----------------------------------------------------
        # 通常トップページ
        # ----------------------------------------------------

        if (
            url.rstrip("/")
            == "https://dx.collaboportal.com"
        ):

            collabo_top_detected = True


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
    # HTTPエラー
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

            print(
                "METHOD:",
                response.request.method
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

            except Exception:
                pass

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
    # ログイン画面待機
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
    # ID / Password
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
    # callback検出待機
    # ========================================================

    print(
        "⏳ 認証callback待機..."
    )

    start_time = time.time()

    while (
        time.time() - start_time < 60
        and not callback_detected
    ):

        time.sleep(0.2)


    # ========================================================
    # callback結果
    # ========================================================

    print("")
    print(
        "========== CALLBACK RESULT =========="
    )

    print(
        "callback検知:",
        callback_detected
    )

    if callback_url:

        print(
            "callback URL:",
            callback_url
        )

    print(
        "現在URL:",
        page.url
    )

    print(
        "====================================="
    )


    # ========================================================
    # callbackが来なければ終了
    # ========================================================

    if not callback_detected:

        print(
            "❌ Collabo Portalへのcallbackを確認できませんでした"
        )

        browser.close()

        raise RuntimeError(
            "Authentication callback not detected"
        )


    # ========================================================
    # callback直後のCookie確認
    # ========================================================

    print("")
    print(
        "========== COOKIE AFTER CALLBACK =========="
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

    print(
        "==========================================="
    )


    # ========================================================
    # callback直後のStorage確認
    # ========================================================

    try:

        local_keys = page.evaluate("""
            () => Object.keys(localStorage)
        """)

        session_keys = page.evaluate("""
            () => Object.keys(sessionStorage)
        """)

        print(
            "localStorage keys:",
            local_keys
        )

        print(
            "sessionStorage keys:",
            session_keys
        )

    except Exception as e:

        print(
            "⚠ Storage確認失敗:",
            e
        )


    # ========================================================
    # Collabo Portalトップへ遷移完了するか監視
    # ========================================================

    print("")
    print(
        "⏳ callback後のSPA初期化待機..."
    )

    spa_ready = False

    start_time = time.time()

    while time.time() - start_time < 30:

        current_url = page.url

        # ログイン画面へ戻った
        if "login-id.dx-utility.com" in current_url:

            print(
                "❌ ログイン画面へ戻されました"
            )

            break

        # Collabo Portal
        if current_url.startswith(
            BASE_URL
        ):

            try:

                article_count = (
                    page
                    .locator("article")
                    .count()
                )

                link_count = (
                    page
                    .locator("a")
                    .count()
                )

                div_count = (
                    page
                    .locator("div")
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
                    "URL=",
                    current_url,
                    "a=",
                    link_count,
                    "div=",
                    div_count,
                    "article=",
                    article_count,
                    "body=",
                    len(body_text)
                )

                # SPA描画あり
                if (
                    link_count > 0
                    or div_count > 5
                    or len(body_text) > 0
                ):

                    spa_ready = True

                    print(
                        "✅ SPA描画を確認"
                    )

                    break

            except Exception as e:

                print(
                    "SPA状態確認失敗:",
                    e
                )

        time.sleep(0.5)


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
        "================================"
    )


    # ========================================================
    # SPAが不安定でも
    # callback成功済みなら通知URLへ直接遷移を試す
    # ========================================================

    if not spa_ready:

        print("")
        print(
            "⚠ SPA描画を確認できませんでした"
        )

        print(
            "ただしcallbackは成功しているため、"
            "同じ認証Contextのまま通知ページへ直接遷移します"
        )


    # ========================================================
    # 通知ページへ直接遷移
    # ========================================================

    print("")
    print(
        "========== MOVE TO NOTIFICATIONS =========="
    )

    try:

        page.goto(
            NOTIFICATIONS_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

    except Exception as e:

        print(
            "⚠ 通知ページ遷移時エラー:",
            e
        )


    print(
        "通知ページURL:",
        page.url
    )

    try:

        print(
            "通知ページTITLE:",
            page.title()
        )

    except Exception:
        pass


    # ========================================================
    # ログインへ戻されたか
    # ========================================================

    if "login-id.dx-utility.com" in page.url:

        print(
            "❌ 通知ページ遷移時に再ログイン画面へ戻されました"
        )

        browser.close()

        raise RuntimeError(
            "Authentication lost before notifications"
        )


    # ========================================================
    # 通知DOM待機
    # ========================================================

    print(
        "⏳ 通知記事DOM待機..."
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
    # 0件なら既存RSS保護
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
    # RSS
    # ========================================================

    save_as_xml(
        items,
        OUTPUT_PATH
    )

    print("")
    print(
        f"🎉 {len(items)}件をRSSへ出力しました"
    )

    browser.close()

    print(
        "========== COMPLETE =========="
    )
