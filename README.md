# TraeAccountCreatorPlus
S-Trespassing/Trae-Account-Creator 的小幅修改版。

删了周年礼包获取，删减了一些print，从mail.cx迁移到temporam，添加真·五光十色的输出，，

额，别的修改点忘了。

基于 Playwright + 临时邮箱，支持单账号注册与批量并发注册，并在完成后导出账号信息和 Cookie。

使用方法
---

①注册temporam账户获取APIkey填入mail_client第8行

②打开cmd输入register.py 注册数量 并发数量 新邮件检查CD。

前两项顾名思义。并发数越高，资源占用越大，也可能导致失败率上升。依据temporam文档，并发数建议不大于10。

第三项，检查CD，CD越高，注册效率越低，同时节省额度；

CD越低，额度开销越大，同时效率越高。

依据实测，推荐把CD填到8-15s之间。

最小值为1，最大值60。



你也可以在填好key之后直接运行register，直接运行则只注册一个。

---
账号密码会保存在accounts.txt中，cookie在.\cookies中。



⚠️ 免责声明
---
📢 重要提示：请仔细阅读以下声明

本工具仅供学习和技术研究使用，使用前请务必了解以下内容：

⚠️ 风险自负：使用者需自行承担所有风险，包括但不限于系统损坏、数据丢失、账号异常等

⚖️ 法律风险：本工具可能违反软件使用协议，请自行评估法律风险

🚫 责任豁免：作者不承担任何直接或间接损失责任

📚 使用限制：仅限个人学习研究，严禁商业用途

🔒 授权声明：不得用于绕过软件正当授权机制

✅ 同意条款：继续使用即表示您已理解并同意承担相应风险

⚠️ 如果您不同意以上条款，请立即停止使用本工具 ⚠️

🙏 项目来源
---
本项目基于 [Trae-Account-Creator](https://github.com/S-Trespassing/Trae-Account-Creator) 魔改而来。

同时一定程度上参考借鉴了[TAC的另一个已死的改版，TraeAccountRegister](https://github.com/kggzs/TraeAccountRegister)。

常见问题
---

如果总是收不到邮件，可以修改73行邮箱域名筛选条件。



