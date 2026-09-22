# XME-bot-qq

[![wakatime](https://wakatime.com/badge/user/33b54570-06cf-487b-a2ac-cb0ffe9baa34/project/de7449e9-22fe-42f2-8852-409a9efe8b87.svg)](https://wakatime.com/badge/user/33b54570-06cf-487b-a2ac-cb0ffe9baa34/project/de7449e9-22fe-42f2-8852-409a9efe8b87)

个人制作 qq 机器人 XME bot

使用 Nonebot 1 + 实现 Onebot 11 API 的客户端（推荐 NapCat 或 SnowLuma（目前使用 SnowLuma））

本 README 以下内容由 AI 生成。

> 仓库内 `nonebot/` 目录是一份修改过的 NoneBot 1（支持 `REPORT_SELF_MESSAGE` 等 OneBot 11 扩展事件），
> 运行时以仓库内这份为准；`requirements.txt` 里的 nonebot 只用来装齐它的依赖。

## 目录结构

| 路径                                        | 说明                                                                           |
| ------------------------------------------- | ------------------------------------------------------------------------------ |
| `bot.py`                                    | 程序入口：加载插件、执行初始化、启动 NoneBot                                   |
| `bot_init.py`                               | 启动初始化：建目录、初始化数据文件、生成指令文档、迁移数据库、同步 cloudflared |
| `watchdog.py` / `start.sh`                  | 生产启动方式：守护进程，崩溃自动重启                                           |
| `config.py`                                 | NoneBot 与业务配置（SUPERUSERS、端口、群白名单、代理等）                       |
| `keys.py.template`                          | 密钥模板，复制为 `keys.py` 后填写（`keys.py` 不会进仓库）                      |
| `character.py` + `characters/`              | 角色系统与文件：bot 的名字、昵称、语气与各类回复文案                           |
| `ai_configs.json`                           | AI 助手的管理名单与系统提示词                                                  |
| `xme/plugins/commands/`                     | 指令插件（weather、ai_helper、shop、maimai、games 等）                         |
| `xme/plugins/server_app/`                   | bot 附带 Web 接口（指令文档页、爱发电 OAuth/Webhook、文件分发等）              |
| `xme/plugins/event_parsers/`、`schedulers/` | 事件处理器与定时任务                                                           |
| `xme/xmetools/`                             | 通用工具库（文件、数据库、消息、绘图等）                                       |
| `nonebot/`                                  | 修改版 NoneBot 1 框架（随仓库分发，勿用 pip 版覆盖）                           |
| `deploy/cloudflared/`                       | API 服务的 cloudflared 隧道配置（唯一来源，bot 启动时自动同步到 /etc）         |
| `data/`、`logs/`、`.backup/`                | 运行数据、日志与自动备份（启动时自动创建，不进仓库）                           |

## 快速上手与构建

### 环境要求

- **Linux**（推荐，`start.sh`/`watchdog.py` 依赖 bash 与 flock），**Python 3.11**
- 一个实现 OneBot 11 的协议端，如 [NapCat](https://github.com/NapNeko/NapCatQQ) 或 [SnowLuma](https://snowluma.github.io/)
- 可选：`cloudflared`（把 Web 接口暴露到公网）、Go 工具链（构建 mai-arcade）
- 部分依赖需要系统库：`pyenchant` 需要 libenchant；浏览器/截图相关功能需要本机有 Chrome/Chromium

### 1. 拉取仓库并安装依赖

```bash
git clone <本仓库> XME-bot-qq
cd XME-bot-qq
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` 内置清华 PyPI 镜像。依赖清单以 `requirements.in` 为准，增删依赖后重新编译：

```bash
pip install pip-tools
pip-compile requirements.in   # 重新生成 requirements.txt
```

### 2. 填写配置

```bash
cp keys.py.template keys.py
```

编辑 `keys.py`，至少填写：

- `ACCESS_TOKEN`：与协议端约定的鉴权 token，可用 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成
- `LLM_PROVIDERS` 中各 Provider 的 `api_key`（AI 功能需要，如 `GLM_API_KEY`）
- `SEARCH_PROVIDERS` 的搜索 key（不需要联网搜索可只留免 key 的 duckduckgo）
- 其余按需：SMTP 邮箱、爱发电系列、天气 key、`DOMAIN` 等

再按需修改 `config.py`，各项含义见文件内注释。

### 3. 配置协议端

在 NapCat / SnowLuma 中添加**反向 WebSocket** 连接，指向本 bot：

```text
ws://<bot 所在主机>:18980/ws/
```

鉴权 token 填 `keys.py` 里的 `ACCESS_TOKEN`，两边需要一致。

### 4. 选择角色（可选）

`characters/` 内置 `Deon`（默认）、`XME`、`Deon_en` 三个角色文件，决定 bot 的名字、语气和全部回复文案。
修改 `character.py` 顶部的 `CHARACTER` 即可切换；想自定义人格，照着现有文件写一个新的 JSON 就行。

### 5. 启动

```bash
# 生产环境：flock 防止双开，watchdog 守护 bot.py，崩溃后按退避间隔自动重启
# 测试建议自己 clone 一份 dev 用
./start.sh
```

首次启动会自动完成：创建 `data/`、`logs/` 目录 → 初始化数据 JSON → 生成指令文档 `docs.md` →
检查/迁移数据库表结构 → 下载 maimai 官方资源包（体积较大，仅 `/mai` 相关功能用到）→
同步 cloudflared 配置（本机没装 cloudflared 时自动跳过，不影响启动）。

`start.sh` 启动时（watchdog 拉起前）会把 `data/` 完整备份到 `.backup/datas-<时间戳>/`，保留最近 300 份。

### 6. 公网访问 Web 接口（可选）

bot 自带的 Web 接口（指令文档页 `/docs`、爱发电 OAuth/Webhook、文件分发等）与 NoneBot 同端口 `:18980`，
内网可直接访问。要暴露到公网，使用仓库内置的 cloudflared 方案：

```bash
sudo bash deploy/cloudflared/install.sh   # 一次性 sudoers 授权（只放行安装配置和重启服务两条命令）
# 编辑 deploy/cloudflared/config.yml 增删放行路径，重启 bot 后自动同步生效
```

白名单机制与回滚方法详见 deploy/cloudflared 中的 README。

### 7. 构建 mai-arcade（可选，`/mai` 指令需要）

```bash
./scripts/build_arcade.sh
# 指定本机源码目录或仓库地址：
# MAI_ARCADE_SRC=~/src/mai-arcade ./scripts/build_arcade.sh
# MAI_ARCADE_REPO=https://github.com/you/mai-arcade ./scripts/build_arcade.sh
```

需要 Go 工具链，构建产物会安装到 `bin/mai-arcade`（`bin/` 不进仓库）。

## 建议自行修改的地方

以下是"每套部署必然不一样"的部分，fork / 二次部署时优先改它们：

| 文件                            | 需要改什么                                                                                                                                                                                                |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `keys.py`                       | 全部密钥与 token（`ACCESS_TOKEN`、LLM key、搜索 key、邮箱、爱发电系列等），并按需增删 `LLM_PROVIDERS` / `SEARCH_PROVIDERS` 条目                                                                           |
| `config.py`                     | `SELF_ID`（bot 的 QQ 号）、`SUPERUSERS`（管理员 QQ 号白名单）、`GROUPS_WHITELIST` / `ANTI_MESSAGEBURST_GROUP` / `PEEK_GROUP`（群号）、`MIN_GROUP_MEMBER_COUNT`、`PORT`、`USE_PROXY` / `HTTP_PORT`（代理） |
| `characters/*.json`             | bot 的名字、昵称、语气词、金币名称与各类回复文案；切换角色改 `character.py` 的 `CHARACTER`                                                                                                                |
| `ai_configs.json`               | AI 助手的管理员名单与系统提示词                                                                                                                                                                           |
| `deploy/cloudflared/config.yml` | 公网放行路径与域名（不用 cloudflared 可忽略）                                                                                                                                                             |
| `requirements.in`               | 按需增删依赖（改完记得 `pip-compile`）                                                                                                                                                                    |

`data/`、`logs/`、`.backup/` 下的内容全部由 bot 自动生成和维护，不需要也不建议手工修改。

## 相关文档

- 指令文档：启动后访问 `http://<host>:18980/docs` 或者本文档，Markdown 源在 `docs.md`（每次启动自动从各插件生成）
