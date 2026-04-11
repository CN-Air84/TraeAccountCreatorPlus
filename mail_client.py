
# ——————Config——————
API_BASE_URL = "https://api.temporam.com/v1"
API_KEY = "tm_gpdjl7ocPrVa78_p_qtGF0WVZLvWv8Dj"#自行填入
 #   https://temporam.com/zh/dashboard
# ——————————————————

def check_api_key():
    """检查API_KEY是否已填写"""
    if not API_KEY or API_KEY.strip() == "":
        print("=" * 60)
        print("[错误] API_KEY 未填写！")
        print("=" * 60)
        print("请按以下步骤获取并填写 API Key：")
        print("1. 访问 https://temporam.com/zh/dashboard")
        print("2. 注册/登录账号")
        print("3. 在控制台中创建 API Key（名称随意）并获取")
        print(f"4. 打开 mail_client.py 文件，将刚才获取到的API Key粘贴进mail_client第四行")
        print("=" * 60)
        return False
    return True

import httpx
import random
import string
import re
import asyncio
import configparser
import os
import json

ERROR_MESSAGES = {
    400: "请求参数无效",
    401: "API Key 缺失或无效",
    403: "API Key 未关联用户或无有效订阅",
    404: "资源未找到",
    429: "请求频率过高或月度配额已耗尽",
}

class AsyncMailClient:
    def __init__(self):
        self.client = None
        self.email_address = None
        self.processed_ids = set()
        self.api_headers = {"Authorization": f"Bearer {API_KEY}"}
        self.last_verification_code = None
        self.available_domains = []
        self.rate_limit = None
        self.rate_remaining = None
        self.rate_reset = None
        self.quota_remaining = None
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

    def _print_rate_info(self, response):
        self.rate_limit = response.headers.get("X-RateLimit-Limit")
        self.rate_remaining = response.headers.get("X-RateLimit-Remaining")
        self.rate_reset = response.headers.get("X-RateLimit-Reset")
        self.quota_remaining = response.headers.get("X-Quota-Remaining")
        print(f"                                [API]剩余配额: {self.quota_remaining}")

    def _print_error(self, response):
        status = response.status_code
        msg = ERROR_MESSAGES.get(status, f"HTTP {status}")
        try:
            body = response.json()
            detail = body.get("message", "")
            if detail:
                msg = f"{msg} - {detail}"
        except Exception:
            pass
        print(f"[API错误] {msg}")

    async def start(self):
        """Initialize Async HTTP Client and load available domains from config"""
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=30.0
        )
        #print("邮箱客户端已初始化...")
        await self._load_domains_from_config()

    async def _load_domains_from_config(self):
        """Load domains from config file, fetch from API if not exists or empty"""
        config = configparser.ConfigParser()
        if os.path.exists(self.config_path):
            try:
                config.read(self.config_path, encoding='utf-8')
                if 'domains' in config and 'list' in config['domains']:
                    domains_str = config['domains']['list']
                    if domains_str:
                        self.available_domains = json.loads(domains_str)
                        if self.available_domains:
                            #print(f"从配置文件加载了 {len(self.available_domains)} 个可用域名")
                            return
            except Exception as e:
                print(f"读取配置文件失败: {e}")
        
        # 配置文件不存在或没有有效域名，从API获取
        print("配置文件无效或不存在，从API获取域名列表...")
        await self._fetch_domains()

    def _save_domains_to_config(self, domains):
        """Save domains list to config file"""
        config = configparser.ConfigParser()
        config['domains'] = {
            'list': json.dumps(domains, ensure_ascii=False)
        }
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            print(f"已将 {len(domains)} 个域名保存到配置文件: {self.config_path}")
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    async def _fetch_domains(self):
        """Fetch available domains from API and save to config"""
        assert self.client is not None, "HTTP client not initialized"
        url = f"{API_BASE_URL}/domains"
        try:
            response = await self.client.get(url, headers=self.api_headers)
            self._print_rate_info(response)
            if response.status_code == 200:
                data = response.json()
                if data.get("error") is False and isinstance(data.get("data"), list):
                    self.available_domains = [item["domain"] for item in data["data"] if "domain" in item and ".edu" in item["domain"] and "mona" in item["domain"] and "rs" not in item["domain"]]
                    
                    print(f"已获取可用域名：{self.available_domains}")
                    # 保存到配置文件
                    if self.available_domains:
                        self._save_domains_to_config(self.available_domains)
                else:
                    print("获取域名列表失败")
            else:
                self._print_error(response)
        except Exception as e:
            print(f"获取域名列表异常：{e}")

    def get_email(self):
        """Generate Temp Email"""
        if not self.available_domains:
            print("无可用域名，请先调用 start()")
            return None
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        domain = random.choice(self.available_domains)
        self.email_address = f"{username}@{domain}"
        self.last_verification_code = None
        self.processed_ids.clear()
        #print(f"已生成邮箱：{self.email_address}")
        return self.email_address

    async def check_emails(self):
        """Check for new emails"""
        if not self.email_address:
            return
        assert self.client is not None, "HTTP client not initialized"

        try:
            response = await self.client.get(
                f"{API_BASE_URL}/emails",
                headers=self.api_headers,
                params={"email": self.email_address}
            )

            self._print_rate_info(response)

            if response.status_code == 200:
                data = response.json()
                messages = data.get("data", [])

                if messages and len(messages) > 0:
                    latest_msg = messages[0]
                    msg_id = latest_msg.get('id')
                    if not self.last_verification_code or (msg_id and msg_id not in self.processed_ids):
                         await self._process_message(latest_msg)
            elif response.status_code == 429:
                self._print_error(response)
            else:
                self._print_error(response)

        except Exception as e:
            print(f"邮箱检查异常：{e}")

    async def _process_message(self, msg):
        if not isinstance(msg, dict):
            return

        msg_id = msg.get('id')
        if msg_id:
            subject = msg.get('subject', 'No Subject')
            #print(f"\n新邮件：{subject}")
            await self._fetch_and_parse_content(msg_id)
            self.processed_ids.add(msg_id)

    async def _fetch_and_parse_content(self, msg_id):
        assert self.client is not None, "HTTP client not initialized"
        url = f"{API_BASE_URL}/emails/{msg_id}"
        try:
            response = await self.client.get(url, headers=self.api_headers)
            self._print_rate_info(response)
            if response.status_code == 200:
                data = response.json()
                detail = data.get("data", {})
                content = detail.get("content", "")
                self._parse_verification_code(content)
            else:
                self._print_error(response)
        except Exception as e:
            print(f"获取邮件内容异常：{e}")

    def _parse_verification_code(self, content):
        content_str = str(content)
        text = re.sub(r'<[^>]+>', ' ', content_str)
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        codes = re.findall(r'\b\d{6}\b', text)
        if codes:
            self.last_verification_code = codes[0]
            #print(f"已找到验证码：{self.last_verification_code}")

    async def close(self):
        if self.client:
            await self.client.aclose()
