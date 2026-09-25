# boss-cli

[![PyPI version](https://img.shields.io/pypi/v/kabi-boss-cli.svg)](https://pypi.org/project/kabi-boss-cli/)
[![CI](https://github.com/jackwener/boss-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/jackwener/boss-cli/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://pypi.org/project/kabi-boss-cli/)

A CLI for BOSS 直聘 — search jobs, view recommendations, manage applications, chat with recruiters, **and manage candidates as a recruiter** via reverse-engineered API 🤝

[English](#features) | [中文](#功能特性)

## More Tools

- [xiaohongshu-cli](https://github.com/jackwener/xiaohongshu-cli) — Xiaohongshu CLI for notes, search, and interactions
- [bilibili-cli](https://github.com/jackwener/bilibili-cli) — Bilibili CLI for videos, users, and search
- [twitter-cli](https://github.com/jackwener/twitter-cli) — Twitter/X CLI for timelines, bookmarks, and posting
- [discord-cli](https://github.com/jackwener/discord-cli) — Discord CLI for local-first sync, search, and export
- [tg-cli](https://github.com/jackwener/tg-cli) — Telegram CLI for local-first sync, search, and export
- [rdt-cli](https://github.com/jackwener/rdt-cli) — Reddit CLI for feed, search, posts, and interactions

## Features

- 🔐 **Auth** — auto-extract browser cookies (10+ browsers), QR code login, `--cookie-source` explicit browser selection, live validation against real search APIs
- 🔍 **Search** — jobs by keyword with city/salary/experience/degree/industry/scale/stage/job-type filters
- ⭐ **Recommendations** — personalized job recommendations based on profile
- 📋 **Detail & Export** — view full job details, short-index navigation (`boss show 3`), CSV/JSON export
- 🎯 **Job Fit** — optional TypeSafe Jev assessment of your BOSS online resume (or a local resume file) against a job posting
- 📜 **History** — browse job viewing history
- 👤 **Profile** — view personal info and full online resume (work/project/education experience, expectations)
- 📮 **Applications** — view applied jobs list
- 📋 **Interviews** — view interview invitations
- 💬 **Chat** — view communicated boss list
- 🤝 **Greet** — send greetings to recruiters, single or batch (with 1.5s rate-limit delay)
- 🏙️ **Cities** — 40+ supported cities
- 🤖 **Agent-friendly** — structured output envelope (`{ok, schema_version, data}`), stable error codes and exit codes, Rich output on stderr — see [Agent & Automation Usage](#agent--automation-usage)
- 👔 **Recruiter Mode** — view posted jobs, manage candidates, chat history, export candidate data (CSV/JSON)

## Installation

```bash
# Recommended: uv tool (fast, isolated)
uv tool install kabi-boss-cli

# Or: pipx
pipx install kabi-boss-cli

# Optional: YAML output support
uv tool install 'kabi-boss-cli[yaml]'   # or: pipx install 'kabi-boss-cli[yaml]'
```

Upgrade to the latest version:

```bash
uv tool upgrade kabi-boss-cli
# Or: pipx upgrade kabi-boss-cli
```

From source:

```bash
git clone git@github.com:jackwener/boss-cli.git
cd boss-cli
uv sync
```

## Usage

```bash
# ─── Auth ─────────────────────────────────────────
boss login                             # Auto-detect browser cookies, fallback to QR
boss login --cookie-source chrome      # Extract from specific browser
boss login --qrcode                    # QR code login only
boss status                            # Check login status (validates real search session, shows cookie names)
boss logout                            # Clear saved cookies

# ─── Search ───────────────────────────────────────
boss search "golang"                   # Search jobs
boss search "Python" --city 杭州       # Filter by city
boss search "Java" --salary 20-30K     # Filter by salary
boss search "前端" --exp 3-5年          # Filter by experience
boss search "AI" --degree 硕士         # Filter by degree
boss search "后端" --industry 互联网    # Filter by industry
boss search "产品" --scale 1000-9999人  # Filter by company size
boss search "数据" --stage 已上市       # Filter by funding stage
boss search "运维" --job-type 全职      # Filter by job type
boss search "后端" --city 深圳 -p 2    # Pagination

# ─── Detail & Export ──────────────────────────────
boss show 3                            # View job #3 from last search
boss detail <securityId>               # View full job details
boss detail <securityId> --json        # JSON output (with schema envelope)
boss export "Python" -n 50 -o jobs.csv # Export search results to CSV
boss export "golang" --format json -o jobs.json  # Export as JSON

# ─── Job Fit (opt-in TypeSafe Jev assessment) ──────
export TYPESAFE_API_KEY="your-api-key"  # Required; keep this secret
boss fit <securityId> --confirm-send --json  # Uses your BOSS online resume
boss fit <securityId> --resume-file ~/resume.txt --confirm-send --json

# ─── Recommendations ──────────────────────────────
boss recommend                         # View recommended jobs
boss recommend -p 2 --json             # Next page, JSON output

# ─── Personal Center ─────────────────────────────
boss me                                # View profile + full online resume
boss me --basic                        # Basic info only
boss me --json                         # JSON output (online resume under data.resume)
boss applied                           # View applied jobs
boss interviews                        # View interview invitations
boss history                           # View browsing history
boss chat                              # View communicated bosses

# ─── Greet ────────────────────────────────────────
boss greet <securityId>                # Send greeting to a boss
boss greet <securityId> --json         # JSON result
boss batch-greet "golang" --city 杭州 -n 5          # Batch greet top 5
boss batch-greet "Python" --salary 20-30K --dry-run  # Preview only

# ─── Utilities ────────────────────────────────────
boss cities                            # List supported cities
boss --version                         # Show version
boss -v search "Python"                # Verbose logging (request timing)
```

### Job Fit Assessment

`boss fit` evaluates one job at a time. By default it uses your BOSS online resume (the same data as `boss me`, without name, contact, age, or gender); pass `--resume-file` to use a UTF-8 `.txt` or `.md` resume instead. It fetches the full job description and job-relevant profile fields (education, work experience, and stated job preferences) from BOSS, then sends them to TypeSafe Jev. The required `--confirm-send` flag makes this external transfer explicit. Name, phone, gender, and age are excluded from the BOSS profile fields. Before sending, emails, mainland phone numbers, ID numbers, and labelled WeChat/QQ IDs are stripped from the resume text and the number of removals is reported; this is pattern-based, so still remove your name, address, and other personal data from the file yourself. Profile fields that could not be read from BOSS are listed in the output (`input_summary.profile_fields_missing`), and the preference score only reflects the fields that were found.

```bash
export TYPESAFE_API_KEY="your-api-key"
boss fit <securityId> --resume-file ~/resume.txt --company-context-file ~/company.txt --confirm-send
```

The company assessment uses BOSS company metadata and any business description present in the job details. Jev does not browse company websites, so pass `--company-context-file` with a company business summary when BOSS does not provide enough detail. The output includes skill, responsibility, experience, company-business, preference, and overall fit dimensions, plus a Jev estimate of resume-screening probability. `TYPESAFE_BASE_URL` (HTTPS origin only, no path) and `TYPESAFE_MODEL` can override the API host and model; defaults are `https://api.typesafe.ai` and `jev-latest`. HTTP 429/529 responses are retried once. Resume plus company context is capped at 40 KB. The 0–4 scores are not percentages. Jev's screening probability is not a company-specific historical hiring rate or a final-offer probability; review the resume and job requirements yourself. This command does not apply to the job or contact the recruiter.

## Recruiter Mode (雇主端)

If you are an employer on BOSS直聘, these commands let you manage candidates from the terminal:

```bash
# ─── Search & Discover (搜索 & 发现) ─────────────
boss recruiter search "golang" --city 深圳 --exp 3-5年    # Search candidates
boss recruiter recommend                                    # Recommended candidates
boss recruiter recommend --job <encryptJobId>               # Switch to different 岗位
boss recruiter recommend -p 2                               # Next page

# ─── Greet & Communicate (沟通) ──────────────────
boss recruiter greet <encryptGeekId>                        # Initiate chat with candidate
boss recruiter batch-view "Python" --city 杭州 -n 10       # Batch view top 10 (triggers "viewed" notice)
boss recruiter inbox                                        # View candidate messages
boss recruiter inbox --job <encryptJobId> -p 2              # Filter by job, page 2
boss recruiter reply <friendId> "感谢您的关注..."            # Reply to candidate
boss recruiter chat <friendId>                              # View chat history

# ─── Chat Actions (沟通页操作) ───────────────────
boss recruiter request-resume <friendId> --yes              # 求简历
boss recruiter exchange-phone <friendId> --yes              # 换电话
boss recruiter exchange-wechat <friendId> --yes             # 换微信
boss recruiter invite-interview <geekId> --job <id>         # 约面试
boss recruiter mark-unsuitable <geekId> --job <id>          # 不合适

# ─── Resume (简历) ───────────────────────────────
boss recruiter resume <encryptGeekId>                       # View full resume in terminal
boss recruiter resume-download <id> --job <jobId>           # Download resume as Markdown
boss recruiter geek <encryptGeekId> --job-id 526908510      # Quick candidate info

# ─── Job Management (职位管理) ───────────────────
boss recruiter jobs                                         # List your posted jobs
boss recruiter job-close <encryptJobId> --yes               # Take job offline
boss recruiter job-reopen <encryptJobId> --yes              # Bring job back online

# ─── Export & Tags ───────────────────────────────
boss recruiter labels                                       # View candidate tags
boss recruiter export -o candidates.csv                     # Export to CSV
boss recruiter export --format json -o out.json             # Export to JSON
```

### Recruiter Workflow Example

```bash
# 1. Check your posted jobs
boss recruiter jobs

# 2. Browse recommended candidates for a specific job
boss recruiter recommend --job f806096ea327cd610nZ80t21FVNQ

# 3. Search for specific skills
boss recruiter search "golang" --city 深圳

# 4. View a candidate's full resume
boss recruiter resume <encryptGeekId> --job <encryptJobId>

# 5. Download resume for offline review
boss recruiter resume-download <encryptGeekId> --job <encryptJobId>

# 6. Start a conversation
boss recruiter greet <encryptGeekId>

# 7. Check inbox and reply
boss recruiter inbox -p 1
boss recruiter reply <friendId> "感谢您的关注，方便电话聊聊吗？"

# 8. Export all candidates
boss recruiter export --format json -o candidates.json
```

## Agent & Automation Usage

boss-cli is designed to be driven by scripts and AI agents. The contract below is stable; see [SCHEMA.md](./SCHEMA.md) for the full schema and [SKILL.md](./SKILL.md) for an agent skill file.

### Output contract

Commands with `--json` / `--yaml` print one envelope to **stdout**; all Rich tables, progress and hints go to **stderr**:

```json
{ "ok": true,  "schema_version": "1", "data": { ... } }
{ "ok": false, "schema_version": "1", "data": null, "error": { "code": "not_authenticated", "message": "..." } }
```

- **Always pass `--json`.** Without a flag, non-TTY stdout gets YAML only when `pyyaml` is installed (the `yaml` extra) and JSON otherwise, so the format depends on the environment.
- Read the payload from `.data`; branch on `.ok` and `.error.code`, not on the message text (messages are Chinese and may change).
- `boss status --json` is the one exception: it prints a **bare object** (no envelope) — read `.authenticated` directly.
- No structured output: `login`, `logout`, `cities`, `batch-greet`, `export` (writes CSV/JSON to `-o` or stdout), `recruiter export`, `recruiter resume-download`, `recruiter job-close`, `recruiter job-reopen`.

### Exit codes and error codes

| Exit | Meaning | stdout |
|------|---------|--------|
| `0` | Success | envelope with `ok: true` |
| `1` | API/runtime error | envelope with `ok: false` (when `--json`/`--yaml`/non-TTY) |
| `1` | Not logged in (`require_auth`) | **empty** — message `未登录` on stderr only |
| `1` | Confirmation prompt aborted (no `-y` and stdin is not interactive) | empty |
| `2` | Invalid usage (unknown option, missing argument, missing `--confirm-send`) | empty — Click usage error on stderr |

| `error.code` | Meaning | Agent action |
|--------------|---------|--------------|
| `not_authenticated` | Session expired / `__zp_stoken__` invalid | Ask the user to log in to zhipin.com in a browser, then `boss logout && boss login` |
| `rate_limited` | BOSS code=9 (already auto-cooled down and retried once) | Stop, wait several minutes, do not retry in a loop |
| `invalid_params` | Bad parameters (BOSS code 17/19) | Fix arguments |
| `api_error` | Other upstream error, e.g. `当前登录状态已失效 (code=7)`, security block (121/122), empty online resume, Jev failure | Surface `.error.message` to the user |
| `unknown_error` | Unexpected error | Surface to the user |

### Preflight: authentication

```bash
boss status --json | jq -e '.authenticated' >/dev/null && echo AUTH_OK || echo AUTH_NEEDED
```

`authenticated` reflects a live search request; `search_authenticated` / `recommend_authenticated` / `reason` diagnose partial sessions (e.g. search works but personal APIs fail). If `AUTH_NEEDED`, the user must act: log in to zhipin.com in a browser and run `boss login` (or scan the QR code). Agents cannot complete login themselves. For headless environments, `BOSS_COOKIES="k1=v1; k2=v2"` injects cookies copied from the browser (treat it as a secret).

### Commands with side effects

Read-only commands are safe to run freely (still sequentially). These commands change state on BOSS or send data elsewhere — **get explicit user approval first**:

| Command | Effect | Non-interactive flag |
|---------|--------|----------------------|
| `boss greet <securityId>` | Sends a greeting / applies to the job **immediately** (no prompt) | — |
| `boss batch-greet <keyword>` | Greets up to `-n` jobs | `-y` (preview with `--dry-run` first) |
| `boss fit <securityId>` | Sends resume + job data to TypeSafe Jev | `--confirm-send` (required) |
| `boss recruiter reply / request-resume / exchange-phone / exchange-wechat / invite-interview / mark-unsuitable` | Messages or actions visible to the candidate | `-y` |
| `boss recruiter batch-view` | Candidates get a "viewed" notification | `-y` (`--dry-run` first) |
| `boss recruiter job-close / job-reopen` | Takes a job offline / online | `-y` |
| `boss recruiter greet <geekId>` | Starts a chat **immediately** (no prompt) | — |

Without `-y`, these commands prompt on stdin; under an agent (no TTY) the prompt reads EOF and the command aborts with exit code 1 — nothing is sent.

### Rules for agents

- **Run commands one at a time.** Do not parallelize; the client adds jitter delays and backs off on rate limits to protect the account.
- Keep batch sizes small (`batch-greet -n` ≤ 10 per session).
- Never print or log cookie values, `credential.json`, or `TYPESAFE_API_KEY`.
- `boss me --json` contains personal data (name, account, contact hints); only pass `data.resume` onward, which excludes identity fields.

### Typical pipelines

```bash
# Search → pick a job → full details
SEC_ID=$(boss search "Python" --city 杭州 --json | jq -r '.data.jobList[0].securityId')
boss detail "$SEC_ID" --json | jq '.data.jobInfo | {jobName, salaryDesc, skills, postDescription}'

# Read the user's online resume (identity-free section)
boss me --json | jq '.data.resume | {work_years, degree, expectations, work_experience, project_experience}'

# Score job fit against the online resume (only after the user approves sending data to TypeSafe)
boss fit "$SEC_ID" --confirm-send --json | jq '.data | {job, overall: .assessment.overall.score, screening: .assessment.screening_probability.probability}'

# Recommendations → preview greetings → greet after approval
boss recommend --json | jq '[.data.jobList[] | {jobName, brandName, salaryDesc, securityId}]'
boss batch-greet "Python" --city 杭州 -n 5 --dry-run
```

## Authentication

boss-cli supports multiple authentication methods:

1. **Saved cookies** — loads from `~/.config/boss-cli/credential.json`
2. **Browser cookies** — auto-detects installed browsers (Chrome, Firefox, Edge, Brave, Arc, Chromium, Opera, Vivaldi, Safari, LibreWolf)
3. **QR code login** — terminal QR output using Unicode half-blocks, scan with Boss 直聘 APP

`boss login` auto-extracts browser cookies first, falls back to QR login. Use `--cookie-source chrome` to specify a browser, or `--qrcode` to skip browser detection. The command now verifies the saved credential against a real authenticated API before reporting success.

`boss recommend` follows the live web app's current recommendation data source and request context, which improves compatibility when the legacy recommendation endpoint is rejected.

`boss status --json` now reports per-flow health such as `search_authenticated` and `recommend_authenticated`, which helps diagnose partial-session issues. To avoid turning repeated checks into their own anti-bot problem, health snapshots are cached briefly in-memory.

### Cookie TTL & Auto-Refresh

Saved cookies auto-refresh from browser after **7 days**. If browser refresh fails, falls back to stale cookies and logs a warning.

## Rate Limiting & Anti-Detection

- **Gaussian jitter**: request delays with `random.gauss(0.3, 0.15)`
- **Random long pauses**: 5% chance of 2-5s pause to mimic reading
- **Rate-limit auto-cooldown**: code=9 triggers exponential backoff (10s→20s→40s→60s) + request delay doubling
- **Exponential backoff**: auto-retry on HTTP 429/5xx (max 3 retries)
- **Response cookie merge**: `Set-Cookie` headers merged back into session
- **HTML redirect detection**: catches auth redirects to login page
- **Browser fingerprint**: macOS Chrome 145 UA, `sec-ch-ua`, `DNT`, `Priority` headers
- **Request logging**: `boss -v` shows request URLs, status codes, and timing

## Use as AI Agent Skill

boss-cli ships with a [`SKILL.md`](./SKILL.md) that teaches AI agents how to use it.

### [Skills CLI](https://github.com/vercel-labs/skills) (Recommended)

```bash
npx skills add jackwener/boss-cli
```

| Flag | Description |
| --- | --- |
| `-g` | Install globally (user-level, shared across projects) |
| `-a claude-code` | Target a specific agent |
| `-y` | Non-interactive mode |

### Manual Install

```bash
mkdir -p .agents/skills
git clone git@github.com:jackwener/boss-cli.git .agents/skills/boss-cli
```

### ~~OpenClaw / ClawHub~~ (Deprecated)

> ⚠️ ClawHub install method is deprecated and no longer supported. Use [Skills CLI](#skills-cli-recommended) or Manual Install above.

## Project Structure

```text
boss_cli/
├── __init__.py           # Package version
├── cli.py                # Click entry point (lightweight, add_command only)
├── client.py             # API client (rate-limit, cooldown, retry, anti-detection)
├── auth.py               # Authentication (10+ browsers, QR login, TTL refresh)
├── constants.py          # URLs, headers (Chrome 145), city codes, filter enums
├── exceptions.py         # Structured exceptions (BossApiError hierarchy)
├── index_cache.py        # Short-index cache for `boss show`
├── resume.py             # Online resume normalization (boss me / boss fit)
├── jev.py                # TypeSafe Jev client, contact-info redaction
└── commands/
    ├── _common.py        # SCHEMA envelope, handle_command, stderr console
    ├── auth.py           # login (--cookie-source/--qrcode), logout, status, me (online resume)
    ├── search.py         # search, recommend, detail, show, export, history, cities
    ├── fit.py            # fit (TypeSafe Jev job-fit assessment)
    ├── personal.py       # applied, interviews
    ├── social.py         # chat, greet (--json), batch-greet (1.5s delay)
    └── recruiter.py      # recruiter-jobs, inbox, geek, chat, labels, export
```

## Development

```bash
# Install dependencies (dev + yaml + browser extras)
uv sync --all-extras

# Unit tests — this is what CI runs (no cookies needed)
uv run pytest tests/test_cli.py -v

# All non-smoke tests
uv run pytest tests/ -v

# Smoke tests (need cookies)
uv run pytest tests/ -v -m smoke

# Lint
uv run ruff check .
```

## Troubleshooting

**Q: `boss status` says not authenticated but local cookies still exist**

`boss status` now verifies the session against a real search API. If `authenticated=false`, your local credential file exists but the underlying web session is no longer usable.

**Q: `环境异常 (__zp_stoken__ 已过期)`**

Your session cookies have expired. Run `boss logout && boss login` to refresh. If QR login only returns a partial cookie set, log in from a browser first and then run `boss login`.

**Q: `暂无投递记录` but I have applied**

Some features require fresh `__zp_stoken__`. Try re-logging in from a browser, then `boss login`.

**Q: `boss login` says no browser cookies found on macOS, although Chrome is logged in**

Run `boss -v login` and look for `Unable to read database file` / `Operation not permitted`. macOS privacy protection blocks the terminal from reading Chrome's profile directory. Grant **Full Disk Access** to your terminal app (System Settings → Privacy & Security → Full Disk Access), fully quit and reopen the terminal, then run `boss login` again and choose "Always Allow" for the "Chrome Safe Storage" keychain prompt. QR login alone cannot produce `__zp_stoken__`, so personal APIs may still fail after a QR-only login.

**Q: `当前登录状态已失效 (code=7)` from `boss me` / `boss recommend` while search works**

The cookies are not a valid job-seeker session (stale cookies or the wrong Chrome profile). Open zhipin.com in the browser profile you actually use, make sure you are logged in as a job seeker, then `boss logout && boss login`.

**Q: Search returns no results**

Check your city filter. Some keywords are city-specific. Use `boss cities` to see available cities.

---

## 功能特性

- 🔐 **认证** — 自动提取浏览器 Cookie（10+ 浏览器），二维码扫码登录，`--cookie-source` 指定浏览器
- 🔍 **搜索** — 按关键词搜索职位，支持城市/薪资/经验/学历/行业/规模/融资阶段/职位类型筛选
- ⭐ **推荐** — 基于求职期望的个性化推荐
- 📋 **详情 & 导出** — 职位详情，编号导航 (`boss show 3`)，CSV/JSON 导出
- 🎯 **岗位适配** — 使用 TypeSafe Jev 对 BOSS 在线简历（或本地简历文件）和职位要求做可选的结构化评估
- 📜 **历史** — 查看浏览历史
- 👤 **个人** — 查看个人资料和完整在线简历（工作/项目/教育经历、求职期望）
- 📮 **投递** — 查看已投递职位列表
- 📋 **面试** — 查看面试邀请
- 💬 **沟通** — 查看沟通过的 Boss 列表
- 🤝 **打招呼** — 向 Boss 打招呼/投递，支持批量操作（内置 1.5s 防风控延迟）
- 🏙️ **城市** — 40+ 城市支持
- 🤖 **Agent 友好** — 结构化输出 envelope、稳定的错误码和退出码，Rich 输出走 stderr，详见 [Agent 调用说明](#agent-调用说明)
- 👔 **招聘方模式** — 查看职位、候选人管理、聊天记录、导出候选人数据 (CSV/JSON)

## 使用示例

```bash
# 认证
boss login                             # 自动提取浏览器 Cookie，失败则二维码
boss login --cookie-source chrome      # 指定浏览器
boss status                            # 检查登录状态
boss logout                            # 清除 Cookie

# 搜索 & 详情
boss search "golang" --city 杭州       # 按城市搜索
boss search "AI" --industry 互联网 --scale 1000-9999人  # 行业+规模
boss search "数据" --stage 已上市 --salary 30-50K       # 融资+薪资
boss show 3                            # 按编号查看详情
boss detail <securityId> --json        # 指定 ID 查看（JSON envelope）
boss export "Python" -n 50 -o jobs.csv # 导出 CSV

# 岗位适配评估（需要 TypeSafe API Key，并显式确认外发简历）
export TYPESAFE_API_KEY="your-api-key"
boss fit <securityId> --confirm-send --json                        # 默认使用 BOSS 在线简历
boss fit <securityId> --resume-file ~/resume.txt --confirm-send --json  # 或使用本地简历文件
# 公司详情不足时可补充：--company-context-file ~/company.txt
# 外发前会自动移除简历中的邮箱/手机号/证件号/微信 QQ 号，姓名和住址请自行删除

# 推荐 & 历史
boss recommend                         # 个性化推荐
boss history                           # 浏览历史

# 个人中心
boss me                                # 个人资料 + 完整在线简历
boss me --basic                        # 仅基本信息
boss me --json                         # 个人资料（JSON，在线简历位于 data.resume）
boss applied                           # 已投递
boss interviews                        # 面试邀请
boss chat                              # 沟通列表

# 打招呼
boss greet <securityId> --json         # 单个打招呼
boss batch-greet "golang" -n 10        # 批量打招呼
boss batch-greet "golang" --dry-run    # 预览

# 工具
boss cities                            # 城市列表
boss -v search "Python"                # 详细日志
```

## 招聘方模式

```bash
# 搜索 & 推荐
boss recruiter search "golang" --city 深圳 --exp 3-5年
boss recruiter recommend --job <encryptJobId>  # 按岗位查看推荐牛人
boss recruiter recommend -p 2                  # 翻页

# 沟通
boss recruiter greet <encryptGeekId>           # 向候选人打招呼
boss recruiter batch-view "Python" -n 10       # 批量查看 (触发被查看通知)
boss recruiter inbox -p 1                      # 查看候选人消息
boss recruiter reply <friendId> "您好..."       # 回复候选人

# 沟通页操作
boss recruiter request-resume <friendId>       # 求简历
boss recruiter exchange-phone <friendId>       # 换电话
boss recruiter exchange-wechat <friendId>      # 换微信
boss recruiter invite-interview <id> --job <id> # 约面试
boss recruiter mark-unsuitable <id> --job <id>  # 不合适

# 简历
boss recruiter resume <encryptGeekId>          # 终端查看简历
boss recruiter resume-download <id> --job <id> # 下载简历为 Markdown

# 职位管理
boss recruiter jobs                            # 查看招聘职位
boss recruiter job-close <encryptJobId>        # 关闭职位
boss recruiter job-reopen <encryptJobId>       # 重新开启

# 导出
boss recruiter labels                          # 查看标签
boss recruiter export -o candidates.csv        # 导出候选人
```

## Agent 调用说明

boss-cli 可以被脚本和 AI Agent 直接调用，完整约定见上文 [Agent & Automation Usage](#agent--automation-usage) 和 [SCHEMA.md](./SCHEMA.md)，要点如下：

- **始终加 `--json`**：结果信封 `{ok, schema_version, data}` 输出到 stdout，Rich 表格和提示走 stderr。不加参数时，非 TTY 环境只有安装了 `pyyaml` 才输出 YAML，否则输出 JSON。
- **按 `.ok` 和 `.error.code` 分支**（`not_authenticated` / `rate_limited` / `invalid_params` / `api_error` / `unknown_error`），不要解析中文错误信息。
- **例外**：`boss status --json` 输出不带信封的对象，直接读 `.authenticated`；`login`、`logout`、`cities`、`batch-greet`、`export` 等没有结构化输出。
- **退出码**：`0` 成功；`1` 接口错误（stdout 有错误信封）、未登录（stdout 为空，stderr 提示 `未登录`）或确认被中止；`2` 参数错误。
- **先检查登录**：`boss status --json | jq -e '.authenticated'`。登录必须由用户在浏览器登录后执行 `boss login` 完成。
- **有副作用的命令需先征得用户同意**：`boss greet`（立即发送，无确认）、`batch-greet`（`-y`）、`fit`（`--confirm-send`，会外发简历）、招聘方的 `reply` / `request-resume` / `exchange-*` / `invite-interview` / `mark-unsuitable` / `batch-view` / `job-close` / `job-reopen`（`-y`）、`recruiter greet`（立即发送）。不加 `-y` 时在非交互环境会读到 EOF 并中止（退出码 1），不会发送。
- **串行执行、控制批量**：不要并发请求，`batch-greet -n` 每次不超过 10。
- **保护隐私**：不要输出 Cookie、`credential.json` 或 `TYPESAFE_API_KEY`；`boss me --json` 含个人信息，向外传递时只用 `data.resume`（不含姓名、联系方式、年龄、性别）。

```bash
# 读取在线简历 → 评估某个职位的适配度（需用户同意外发）
boss me --json | jq '.data.resume'
boss fit <securityId> --confirm-send --json | jq '.data.assessment.overall'
```

## 常见问题

- `环境异常` — Cookie 过期，执行 `boss logout && boss login` 刷新
- macOS 上 Chrome 已登录但提示找不到 Cookie — 终端没有「完全磁盘访问权限」，在「系统设置 → 隐私与安全性 → 完全磁盘访问权限」中为终端 App 开启，重启终端后重新 `boss login`
- `boss me` 返回 `当前登录状态已失效 (code=7)` 而搜索正常 — Cookie 不是有效的求职者登录态，在常用的浏览器 Profile 中登录 zhipin.com 后执行 `boss logout && boss login`
- 搜索无结果 — 检查城市筛选或关键词，使用 `boss cities` 查看支持的城市

## License

Apache-2.0
