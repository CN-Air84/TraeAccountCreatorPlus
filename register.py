from ast import For
import asyncio
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
from mail_client import AsyncMailClient
from colorama import Fore, Style,Back
from colorama import init as coloinit

coloinit(autoreset=True)
#颜色列表
colors = [Back.GREEN, Back.YELLOW, Back.BLUE, Back.MAGENTA, Back.CYAN, Fore.CYAN,Fore.GREEN,Fore.BLUE,Fore.YELLOW,Fore.MAGENTA]


# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
os.makedirs(COOKIES_DIR, exist_ok=True)

def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

async def save_account(email, password):
    write_header = not os.path.exists(ACCOUNTS_FILE) or os.path.getsize(ACCOUNTS_FILE) == 0
    with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
        if write_header:
            f.write("Email    Password\n")
        f.write(f"{email}    {password}\n")
    #print(f"账号已保存到: {ACCOUNTS_FILE}")

async def run_registration(CD,thread_num):
    global colors
    print(colors[thread_num-1] + "开始单账号注册流程...")

    
    #依据CD计算重试次数
    total_duration = 60
    retry_num= int(total_duration / CD)


    
    mail_client = AsyncMailClient()
    browser = None
    context = None
    page = None

    try:
        # 1. Setup Mail
        await mail_client.start()
        password = generate_password()

        # 2. Setup Browser
        async with async_playwright() as p:
            print(colors[thread_num-1] + f"[线程{thread_num}] 启动浏览器...")
            # Use headless=False if you want to watch it, True for background
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # 3. Sign Up Process
            print(colors[thread_num-1] + f"[线程{thread_num}] 打开注册页面...")
            # 使用 domcontentloaded 替代默认的 load，更快完成；增加超时时间
            await page.goto("https://www.trae.ai/sign-up", wait_until="domcontentloaded", timeout=6000)
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(2)

            # 4. 成功打开注册页面后，调用API获取邮箱
            print(colors[thread_num-1] + f"[线程{thread_num}] 注册页面加载成功，正在获取邮箱...")
            email = mail_client.get_email()
            if not email:
                print(colors[thread_num-1] + f"[线程{thread_num}] 获取邮箱失败，无可用域名")
                return
            
            # Fill Email
            email_input = page.get_by_role("textbox", name="Email")
            await email_input.wait_for(state="visible", timeout=15000)
            await email_input.fill(email)
            await page.get_by_text("Send Code").click()
            print(colors[thread_num-1] + f"[线程{thread_num}] 验证码已发送，等待邮件...")

            # Poll for code
            verification_code = None
            for i in range(retry_num): # 60 seconds max
                await asyncio.sleep(CD)
                await mail_client.check_emails()
                if mail_client.last_verification_code:
                    verification_code = mail_client.last_verification_code
                    break
                print(colors[thread_num-1] + f"[线程{thread_num}] 正在检查邮箱... ({i+1}/{retry_num})")
                

            if not verification_code:
                print(colors[thread_num-1] + f"[线程{thread_num}] 60秒内未收到验证码。")
                return

            # Fill Code & Password
            await page.get_by_role("textbox", name="Verification code").fill(verification_code)
            await page.get_by_role("textbox", name="Password").fill(password)

            # Click Sign Up
            signup_btns = page.get_by_text("Sign Up")
            if await signup_btns.count() > 1:
                await signup_btns.nth(1).click()
            else:
                await signup_btns.click()
            
            print(colors[thread_num-1] + f"[线程{thread_num}] 正在提交注册...")

            # Verify Success (Check URL change or specific element)
            try:
                ###
                await page.wait_for_url(lambda url: "setting" in url, timeout=20000)
                print(colors[thread_num-1] + f"[线程{thread_num}] 注册成功（页面已跳转）")
            except:
                # Check for errors
                if await page.locator(".error-message").count() > 0:
                    err = await page.locator(".error-message").first.inner_text()
                    print(f"[线程{thread_num}] 注册失败：{err}")
                    return
                print(colors[thread_num-1] + f"[线程{thread_num}] 注册出现常见问题默认成功，继续后续流程...")

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
            print(colors[thread_num-1] + f"[线程{thread_num}] 账号已保存，已保存浏览器 Cookie 到: {cookie_path}")

    except Exception as e:
        print(colors[thread_num-1] + f"[线程{thread_num}]发生异常：{e}")
    finally:
        if mail_client:
            await mail_client.close()
        # Browser closes automatically with context manager

async def run_batch(total, concurrency, mailsCheckCD):
    global colors
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
    elif mailsCheckCD <=6:
        if input("邮件检查CD小于6s易导致API用量消耗过快。是否继续?[Y/n]") != 'Y':
            return
    elif mailsCheckCD >=15:
        if input("邮件检查CD大于15s将严重降低注册效率。是否继续?[Y/n]") != 'Y':
            return
    concurrency = min(concurrency, total)
    print(f"开始批量注册，总数量：{total}，并发数：{concurrency}，邮件检查CD：{mailsCheckCD}s")

    queue = asyncio.Queue()
    for i in range(1, total + 1):
        queue.put_nowait(i)
    for _ in range(concurrency):
        queue.put_nowait(None)

    async def worker(worker_id):
        while True:
            index = await queue.get()
            if index is None:
                queue.task_done()
                return
            print(colors[worker_id-1] + f"[线程 {worker_id}] 开始注册第 {index}/{total} 个账号...")
            try:
                await run_registration(mailsCheckCD,thread_num=worker_id)
            finally:
                print(colors[worker_id-1] + f"[线程 {worker_id}] 第 {index}/{total} 个账号完成。")
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
