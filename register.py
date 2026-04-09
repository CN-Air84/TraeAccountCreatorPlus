from ast import For
import asyncio
import warnings
from ctypes import cdll
import random
import string
import os
import re
import json
import sys
from turtle import back
from httpx import ReadTimeout
from playwright.async_api import async_playwright
from mail_client import AsyncMailClient, check_api_key
from colorama import Fore, Style, Back
from colorama import init as coloinit
import httpx

# 屏蔽RuntimeWarning
warnings.filterwarnings("ignore", category=RuntimeWarning)

coloinit(autoreset=True)
# 颜色列表
colors = [
    Back.GREEN,
    Back.YELLOW,
    Back.BLUE,
    Back.MAGENTA,
    Back.CYAN,
    Fore.CYAN,
    Fore.GREEN,
    Fore.BLUE,
    Fore.YELLOW,
    Fore.MAGENTA,
]

# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
SESSION_DIR = os.path.join(BASE_DIR, "sessions")
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
os.makedirs(COOKIES_DIR, exist_ok=True)
os.makedirs(SESSION_DIR, exist_ok=True)

# Chrome 139 真实浏览器指纹
CHROME_139_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/139.0.7258.154 Safari/537.36"
)


def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choices(chars, k=length))


async def save_account(email, password):
    write_header = (
        not os.path.exists(ACCOUNTS_FILE) or os.path.getsize(ACCOUNTS_FILE) == 0
    )
    with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
        if write_header:
            f.write("Email    Password\n")
        f.write(f"{email}    {password}\n")
    # print(f"账号已保存到: {ACCOUNTS_FILE}")


async def check_network():
    """检查网络连接（访问Google）"""
    test_urls = ["https://www.google.com", "https://www.youtube.com"]
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in test_urls:
            try:
                response = await client.get(url, follow_redirects=True)
                if response.status_code == 200:
                    return True
            except Exception:
                input("")
                continue
    return False


async def load_cookies(context, email):
    """加载保存的Cookie"""
    cookie_path = os.path.join(COOKIES_DIR, f"{email}.json")
    if os.path.exists(cookie_path):
        try:
            with open(cookie_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            return True
        except Exception:
            pass
    return False


async def load_session_storage(playwright, email):
    """加载保存的Session存储"""
    session_path = os.path.join(SESSION_DIR, f"{email}.json")
    if os.path.exists(session_path):
        try:
            with open(session_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


async def save_session_storage(email, page):
    """保存Session存储（localStorage等）"""
    try:
        session_data = await page.evaluate("""() => {
            return {
                localStorage: localStorage,
                sessionStorage: sessionStorage
            };
        }""")
        session_path = os.path.join(SESSION_DIR, f"{email}.json")
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f)
    except Exception:
        pass


async def inject_stealth_scripts(page):
    """注入反检测脚本"""
    await page.add_init_script("""
        // 1. navigator.webdriver 设置为 undefined
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
        
        // 2. 插件检测伪装
        const fakePlugins = [
            { name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', description: '', filename: 'internal-nacl-plugin' }
        ];
        Object.defineProperty(navigator, 'plugins', {
            get: () => fakePlugins.slice(0, 3),
            configurable: true
        });
        
        // 3. mimeTypes 伪装
        const fakeMimeTypes = [
            new MimeType('application/pdf', 'Portable Document Format', 'pdf', 'internal-pdf-viewer'),
            new MimeType('text/html', 'HTML Document', 'html', 'internal-nacl-plugin')
        ];
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => fakeMimeTypes,
            configurable: true
        });
        
        // 4. permissions API 伪装
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission, force: true }) :
                originalQuery(parameters)
        );
        
        // 5. platform 伪装
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
            configurable: true
        });
        
        // 6. hardwareConcurrency 伪装
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => Math.floor(Math.random() * 8) + 8,
            configurable: true
        });
        
        // 7. deviceMemory 伪装
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            configurable: true
        });
        
        // 8. languages 伪装
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            configurable: true
        });
        
        // 9. Chrome 运行时对象
        window.chrome = {
            runtime: { sendMessage: () => {}, onMessage: { addListener: () => {} } }
        };
    """)

    # WebGL 伪装
    await page.add_init_script("""
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Google Inc. (NVIDIA)';
            if (parameter === 37446) return 'ANGLE (NVIDIA GeForce RTX 3080, Direct3D11 vs_5_0 ps_5_0)';
            return getParameter.apply(this, arguments);
        };
    """)


async def setup_request_interception(page):
    """设置请求拦截，移除自动化相关headers"""

    async def handle_route(route):
        request = route.request
        headers = request.headers.copy()

        # 移除可能泄露自动化的headers
        headers.pop("x-playwright", None)
        headers.pop("x-devtools", None)
        headers.pop(" playwright", None)

        # 确保Accept头部符合真实浏览器
        if request.resource_type == "document":
            headers["Accept"] = (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            )
            headers["Upgrade-Insecure-Requests"] = "1"

        await route.continue_(headers=headers)

    await page.route("**/*", handle_route)


async def run_registration(CD, thread_num):
    global colors
    print(colors[thread_num - 1] + "开始单账号注册流程...")

    # 检查 API_KEY
    if not check_api_key():
        return False

    # 依据CD计算重试次数
    total_duration = 60
    retry_num = int(total_duration / CD)

    mail_client = AsyncMailClient()
    browser = None
    context = None
    page = None

    try:
        # 1. Setup Mail
        await mail_client.start()
        password = generate_password()
        email = mail_client.get_email()

        # 2. Setup Browser
        async with async_playwright() as p:
            print(colors[thread_num - 1] + f"[线程{thread_num}] 启动浏览器...")

            # 启动浏览器（轻量化配置，维持反检测）
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    # 反检测核心
                    "--disable-blink-features=AutomationControlled",
                    # 轻量化优化
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-gpu-compositing",
                    "--disable-gpu-sandbox",
                    "--disable-accelerated-2d-canvas",
                    "--disable-dev-shm-usage",
                    "--renderer-process-limit=1",
                    "--disable-renderer-backgrounding",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-sync",
                    "--disable-hang-monitor",
                    "--disable-prompt-on-repost",
                    "--disable-popup-blocking",
                    "--disable-ipc-flooding-protection",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--js-flags=--max-old-space-size=256",
                    # 窗口位置
                    "--start-minimized",
                    "--window-position=10000,10000",
                ],
            )

            # 创建上下文（包含真实浏览器指纹）
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                screen={"width": 1920, "height": 1080},
                user_agent=CHROME_139_USER_AGENT,
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                permissions=["geolocation"],
                geolocation={"latitude": 31.2304, "longitude": 121.4737},
                color_scheme="light",
                has_touch=False,
                is_mobile=False,
                java_script_enabled=True,
                extra_http_headers={
                    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "sec-ch-ua": '"Chromium";v="139", "Not-A Brand";v="8"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1",
                },
            )

            # 加载已保存的Cookie（如果有）
            if email:
                await load_cookies(context, email)

            page = await context.new_page()

            # 注入反检测脚本
            await inject_stealth_scripts(page)

            # 设置请求拦截
            await setup_request_interception(page)

            # 加载Session存储（如果有）
            if email:
                session_data = await load_session_storage(p, email)
                if session_data:
                    await page.evaluate(f"""() => {{
                        for (let key in {json.dumps(session_data.get("localStorage", {}))}) {{
                            localStorage.setItem(key, {json.dumps(session_data.get("localStorage", {}))}[key]);
                        }}
                    }}""")

            # 3. Sign Up Process
            print(colors[thread_num - 1] + f"[线程{thread_num}] 打开注册页面...")
            # 使用 domcontentloaded 替代默认的 load，更快完成；增加超时时间
            await page.goto(
                "https://www.trae.ai/sign-up",
                wait_until="domcontentloaded",
                timeout=6000,
            )
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(2)

            # 4. 成功打开注册页面后，调用API获取邮箱
            print(
                colors[thread_num - 1]
                + f"[线程{thread_num}] 注册页面加载成功，正在获取邮箱..."
            )
            email = mail_client.get_email()
            if not email:
                print(
                    colors[thread_num - 1]
                    + f"[线程{thread_num}] 获取邮箱失败，无可用域名"
                )
                return False

            # Fill Email
            email_input = page.get_by_role("textbox", name="Email")
            await email_input.wait_for(state="visible", timeout=15000)
            await email_input.fill(email)
            await page.get_by_text("Send Code").click()
            print(
                colors[thread_num - 1] + f"[线程{thread_num}] 验证码已发送，等待邮件..."
            )

            # Poll for code
            verification_code = None
            for i in range(retry_num):  # 60 seconds max
                await asyncio.sleep(CD)
                await mail_client.check_emails()
                if mail_client.last_verification_code:
                    verification_code = mail_client.last_verification_code
                    break
                print(
                    colors[thread_num - 1]
                    + f"[线程{thread_num}] 正在检查邮箱... ({i + 1}/{retry_num})"
                )

            if not verification_code:
                print(
                    colors[thread_num - 1] + f"[线程{thread_num}] 60秒内未收到验证码。"
                )
                return False

            # Fill Code & Password
            await page.get_by_role("textbox", name="Verification code").fill(
                verification_code
            )
            await page.get_by_role("textbox", name="Password").fill(password)

            # Click Sign Up
            signup_btns = page.get_by_text("Sign Up")
            if await signup_btns.count() > 1:
                await signup_btns.nth(1).click()
            else:
                await signup_btns.click()

            print(colors[thread_num - 1] + f"[线程{thread_num}] 正在提交注册...")

            # Verify Success (Check URL change or specific element)
            try:
                ###
                await page.wait_for_url(lambda url: "setting" in url, timeout=20000)
                print(
                    colors[thread_num - 1]
                    + f"[线程{thread_num}] 注册成功（页面已跳转）"
                )
            except:
                # Check for errors
                if await page.locator(".error-message").count() > 0:
                    err = await page.locator(".error-message").first.inner_text()
                    print(f"[线程{thread_num}] 注册失败：{err}")
                    return False
                print(
                    colors[thread_num - 1]
                    + f"[线程{thread_num}] 注册出现常见问题默认成功，继续后续流程..."
                )

            # Save Account
            await save_account(email, password)

            # 4. Claim Gift
            # print("周年礼包活动结束了孩子们")
            # await page.goto("https://www.trae.ai/2026-anniversary-gift")
            # await page.wait_for_load_state("networkidle")

            # claim_btn = page.get_by_role("button", name=re.compile("claim", re.IGNORECASE))
            # if await claim_btn.count() > 0:
            #     text = await claim_btn.first.inner_text()
            #     if "claimed" in text.lower():
            #         print("礼包状态：已领取")
            #     else:
            #         print(f"点击领取按钮：{text}")
            #         await claim_btn.first.click()
            #         # Wait for status update
            #         try:
            #             await page.wait_for_function(
            #                 "btn => btn.innerText.toLowerCase().includes('claimed')",
            #                 arg=await claim_btn.first.element_handle(),
            #                 timeout=10000
            #             )
            #             print("礼包领取成功！")
            #         except:
            #             print("已点击领取，但状态未更新为"已领取"。")
            # else:
            #     print("未找到领取按钮。")

            # 5. Save Cookies
            cookies = await context.cookies()
            cookie_path = os.path.join(COOKIES_DIR, f"{email}.json")
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f)
            print(
                colors[thread_num - 1]
                + f"[线程{thread_num}] 账号已保存，已保存浏览器 Cookie 到: {cookie_path}"
            )

            # 6. Save Session Storage
            await save_session_storage(email, page)

            return True  # 注册成功

    except Exception as e:
        print(colors[thread_num - 1] + f"[线程{thread_num}]发生异常：{e}")
        return False
    finally:
        if mail_client:
            await mail_client.close()
        # Browser closes automatically with context manager


# 连续失败计数器（CLI用）
consecutive_failures = 0
failure_lock = None
MAX_CONSECUTIVE_FAILURES = 10


async def run_batch(total, concurrency, mailsCheckCD):
    global colors, consecutive_failures, failure_lock

    # 检查 API_KEY
    if not check_api_key():
        return

    # 检查网络连接（只检查一次）
    print("检查网络连接...")
    if not await check_network():
        print("必须挂VPN，否则连不上trae国际版服务器！")
        return
    print("网络连接正常\n")

    if total <= 0:
        print("批量注册数量必须大于 0。")
        return
    if concurrency <= 0:
        print("并发数量必须大于 0。")
        return
    elif concurrency >= 10:
        print("并发数量不能超过10。")
    if mailsCheckCD <= 1:
        print("邮件检查CD必须大于1s。")
        return
    elif mailsCheckCD <= 6:
        if input("邮件检查CD小于6s易导致API用量消耗过快。是否继续?[Y/n]") != "Y":
            return
    elif mailsCheckCD >= 15:
        if input("邮件检查CD大于15s将严重降低注册效率。是否继续?[Y/n]") != "Y":
            return
    concurrency = min(concurrency, total)
    print(
        f"开始批量注册，总数量：{total}，并发数：{concurrency}，邮件检查CD：{mailsCheckCD}s"
    )

    # 初始化连续失败计数器
    consecutive_failures = 0
    failure_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    queue = asyncio.Queue()
    for i in range(1, total + 1):
        queue.put_nowait(i)
    for _ in range(concurrency):
        queue.put_nowait(None)

    async def worker(worker_id):
        global consecutive_failures
        while True:
            # 检查是否已达到连续失败上限
            if stop_event.is_set():
                print(
                    colors[worker_id - 1]
                    + f"[线程 {worker_id}] 连续失败达上限，停止注册"
                )
                return

            index = await queue.get()
            if index is None:
                queue.task_done()
                return
            print(
                colors[worker_id - 1]
                + f"[线程 {worker_id}] 开始注册第 {index}/{total} 个账号..."
            )

            success = False
            try:
                success = await run_registration(mailsCheckCD, thread_num=worker_id)
            except Exception as e:
                print(colors[worker_id - 1] + f"[线程 {worker_id}] 注册异常：{e}")
            finally:
                # 更新连续失败计数
                if failure_lock is not None:
                    async with failure_lock:
                        if success:
                            consecutive_failures = 0
                        else:
                            consecutive_failures += 1
                            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                                print(f"\n{'=' * 50}")
                                print(
                                    f"[警告] 连续失败 {MAX_CONSECUTIVE_FAILURES} 次，停止所有注册！"
                                )
                                print(f"{'=' * 50}\n")
                                stop_event.set()

                print(
                    colors[worker_id - 1]
                    + f"[线程 {worker_id}] 第 {index}/{total} 个账号完成。"
                )
                queue.task_done()

    tasks = [asyncio.create_task(worker(i + 1)) for i in range(concurrency)]
    await queue.join()
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    # if sys.platform == 'win32':
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    total = 1
    concurrency = 1
    mailscheckcd = 10
    if len(sys.argv) > 1:
        try:
            total = int(sys.argv[1])
        except ValueError:
            print("参数错误：请输入批量注册数量（整数）。")
            sys.exit(1)
    if len(sys.argv) > 2:
        try:
            concurrency = int(sys.argv[2])
        except ValueError:
            print("参数错误：请输入并发数量（整数）。")
            sys.exit(1)
    if len(sys.argv) > 3:
        try:
            mailscheckcd = int(sys.argv[3])
        except ValueError:
            print("参数错误：请输入邮件检查CD（整数）。")
            sys.exit(1)
    asyncio.run(run_batch(total, concurrency, mailscheckcd))
