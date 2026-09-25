---
name: boss-cli
description: Use boss-cli for ALL BOSS 直聘 operations — searching jobs, viewing recommendations, reading the user's online resume, scoring job fit, managing applications, chatting with recruiters, and batch greeting. Invoke whenever the user requests any job search or recruitment platform interaction on BOSS 直聘.
author: jackwener
version: "0.3.0"
tags:
  - boss
  - zhipin
  - boss直聘
  - job-search
  - recruitment
  - cli
---

# boss-cli — BOSS 直聘 CLI Tool

**Binary:** `boss`
**Credentials:** browser cookies (auto-extracted from 10+ browsers) or QR code login (`--qrcode`)

## Setup

```bash
# Install (requires Python 3.10+)
uv tool install kabi-boss-cli
# Or: pipx install kabi-boss-cli

# Upgrade to latest (recommended)
uv tool upgrade kabi-boss-cli
# Or: pipx upgrade kabi-boss-cli
```

## Authentication

**IMPORTANT FOR AGENTS**: Before executing ANY boss command, check if credentials exist first. Do NOT assume cookies are configured.

### Step 0: Check if already authenticated

```bash
boss status --json 2>/dev/null | jq -r '.authenticated' | grep -q true && echo "AUTH_OK" || echo "AUTH_NEEDED"
```

If `AUTH_OK`, skip to [Command Reference](#command-reference).
If `AUTH_NEEDED`, proceed to Step 1.

### Step 1: Guide user to authenticate

Ensure user is logged into zhipin.com in any supported browser (Chrome, Firefox, Edge, Brave, Arc, Chromium, Opera, Vivaldi, Safari, LibreWolf). Then:

```bash
boss login                              # auto-detect browser with valid cookies
boss login --cookie-source chrome       # specify browser explicitly
boss login --qrcode                     # QR code login — scan with Boss app
```

Verify with:

```bash
boss status
boss me --json | jq '.data.name'
```

### Step 2: Handle common auth issues

| Symptom | Agent action |
|---------|-------------|
| `环境异常 (__zp_stoken__ 已过期)` | Run `boss logout && boss login` |
| `未登录` (exit 1, empty stdout) | Run `boss login` |
| `当前登录状态已失效 (code=7)` on `me`/`recommend` while search works | Cookies are not a valid job-seeker session; user logs in to zhipin.com in their main browser profile, then `boss logout && boss login` |
| `boss login` finds no cookies on macOS (`Operation not permitted`) | User grants Full Disk Access to the terminal app, restarts it, runs `boss login` |
| Rate limited (code=9) | Auto-cooldown built-in; wait and retry |
| API timeout | Check network, retry |

### Headless / no browser

If the environment has no browser access (CI, remote agent), ask the user to set `BOSS_COOKIES="k1=v1; k2=v2"` themselves (copied from browser DevTools). Never ask them to paste cookie values into the chat.

## Agent Defaults

All machine-readable output uses the envelope documented in [SCHEMA.md](./SCHEMA.md).
Payloads live under `.data`.

- **Always pass `--json`.** Without a flag, non-TTY stdout is YAML only if `pyyaml` is installed, otherwise JSON.
- Branch on `.ok` and `.error.code`; do not parse the Chinese `.error.message`.
- Rich output → **stderr** (safe for pipes: `boss search X --json | jq .data`).
- `boss status --json` has **no envelope** — read `.authenticated` directly.
- No structured output: `login`, `logout`, `cities`, `batch-greet`, `export` (use `--format json`), `recruiter export`, `recruiter resume-download`, `recruiter job-close`, `recruiter job-reopen`.

### Exit codes

| Exit | Meaning |
|------|---------|
| `0` | Success |
| `1` | API error (error envelope on stdout), **or** not logged in (stdout empty, `未登录` on stderr), **or** a confirmation prompt aborted because `-y` was not passed |
| `2` | Usage error (bad option / missing argument / `boss fit` without `--confirm-send`) |

## Command Reference

### Search & Browse

| Command | Description | Example |
|---------|-------------|---------|
| `boss search <keyword>` | Search jobs with filters | `boss search "golang" --city 杭州 --salary 20-30K` |
| `boss show <index>` | View job #N from last search | `boss show 3` |
| `boss detail <securityId>` | View full job details | `boss detail abc123 --json` |
| `boss export <keyword>` | Export search results to CSV/JSON | `boss export "Python" -n 50 -o jobs.csv` |
| `boss recommend` | Personalized recommendations | `boss recommend -p 2 --json` |
| `boss history` | View browsing history | `boss history --json` |
| `boss cities` | List supported cities | `boss cities` |

### Personal Center

| Command | Description | Example |
|---------|-------------|---------|
| `boss me` | Profile + full online resume (work/project/education experience, advantage, skills, expectations) | `boss me --json \| jq .data.resume` |
| `boss me --basic` | Base profile only (name, age, degree) | `boss me --basic --json` |
| `boss applied` | View applied jobs | `boss applied -p 1 --json` |
| `boss interviews` | View interview invitations | `boss interviews --json` |
| `boss chat` | View communicated bosses | `boss chat --json` |

### Job Fit (TypeSafe Jev)

| Command | Description | Example |
|---------|-------------|---------|
| `boss fit <securityId>` | Score the user's BOSS online resume against a job | `boss fit abc123 --confirm-send --json` |
| `boss fit <securityId> --resume-file <path>` | Use a local UTF-8 `.txt`/`.md` resume instead | `boss fit abc123 --resume-file resume.md --confirm-send --json` |
| `--company-context-file <path>` | Add a company business summary when BOSS has little detail | |

Requires `TYPESAFE_API_KEY` in the environment. `--confirm-send` is mandatory because the resume, profile fields and job data are sent to TypeSafe — **ask the user before passing it**. Output fields: `.data.assessment.{skills,responsibilities,experience,company_business,preference_alignment,overall}.score` (0–4, not a percentage, with `probabilities` per level), `.data.assessment.screening_probability.probability`, and `.data.input_summary` (see [SCHEMA.md](./SCHEMA.md)).

### Actions (side effects — get user approval first)

| Command | Description | Example |
|---------|-------------|---------|
| `boss greet <securityId>` | Greet a boss / apply — sends **immediately**, no prompt | `boss greet abc123 --json` |
| `boss batch-greet <keyword> --dry-run` | Preview targets without sending | `boss batch-greet "golang" --dry-run` |
| `boss batch-greet <keyword> -y` | Batch greet from search (`-y` skips the prompt) | `boss batch-greet "Python" --city 杭州 -n 5 -y` |

Commands that prompt for confirmation (`batch-greet`, recruiter `reply` / `request-resume` / `exchange-*` / `invite-interview` / `mark-unsuitable` / `batch-view` / `job-close` / `job-reopen`) abort with exit code 1 under an agent unless `-y` is passed. Only add `-y` after the user has approved that specific action. `boss recruiter greet` also sends immediately without a prompt.

### Account

| Command | Description |
|---------|-------------|
| `boss login` | Extract cookies from a logged-in browser; on failure exits with the cause and fix (no automatic QR) |
| `boss login --cookie-source <browser>` | Extract from specific browser |
| `boss login --qrcode` | Explicit QR login — logs the browser session out and cannot obtain `__zp_stoken__`; only use when the user asks |
| `boss status` | Check authentication status (shows cookie names) |
| `boss logout` | Clear saved credentials |

## Search Filter Options

| Filter | Flag | Values |
|--------|------|--------|
| City | `--city` | 北京, 上海, 杭州, 深圳, etc. (use `boss cities` for full list) |
| Salary | `--salary` | 3K以下, 3-5K, 5-10K, 10-15K, 15-20K, 20-30K, 30-50K, 50K以上 |
| Experience | `--exp` | 不限, 在校/应届, 1年以内, 1-3年, 3-5年, 5-10年, 10年以上 |
| Degree | `--degree` | 不限, 初中及以下, 中专/中技, 高中, 大专, 本科, 硕士, 博士 |
| Industry | `--industry` | 互联网, 电子商务, 游戏, 软件/信息服务, 人工智能, 大数据, 云计算, 金融, 教育培训, 医疗健康, etc. (see `boss search --help`) |
| Company Scale | `--scale` | 0-20人, 20-99人, 100-499人, 500-999人, 1000-9999人, 10000人以上 |
| Funding Stage | `--stage` | 未融资, 天使轮, A轮, B轮, C轮, D轮及以上, 已上市, 不需要融资 |
| Job Type | `--job-type` | 全职, 兼职, 实习 |

## Agent Workflow Examples

### Search → Batch Greet pipeline

```bash
# Preview first
boss batch-greet "golang" --city 杭州 --salary 20-30K --dry-run
# Then execute
boss batch-greet "golang" --city 杭州 --salary 20-30K -n 10 -y
```

### Search → Detail pipeline (structured)

```bash
# Search and extract securityId
SEC_ID=$(boss search "golang" --city 杭州 --json | jq -r '.data.jobList[0].securityId')
# Get full detail
boss detail "$SEC_ID" --json | jq '.data.jobInfo | {jobName, salaryDesc, skills}'
```

### Daily job check workflow

```bash
boss recommend --json | jq '.data.jobList | length'  # Check recommendations count
boss search "Python" --city 杭州 --json               # Search specific jobs
boss show 1                                            # View top result details
boss applied --json                                    # Check application status
boss interviews --json                                 # Check interview invitations
boss chat --json                                       # Check messages
boss history --json                                    # Review browsing history
```

### Export pipeline

```bash
boss export "golang" --city 杭州 --salary 20-30K -n 50 -o jobs.csv
boss export "Python" -n 100 --format json -o jobs.json
```

### Profile check

```bash
boss me --basic --json | jq '.data | {name, age, degreeCategory}'
```

### Resume → job fit pipeline

```bash
# Read the identity-free online resume
boss me --json | jq '.data.resume | {work_years, degree, expectations, work_experience}'
# Find a candidate job
SEC_ID=$(boss search "Python" --city 杭州 --json | jq -r '.data.jobList[0].securityId')
# Score it (only after the user approves sending data to TypeSafe)
boss fit "$SEC_ID" --confirm-send --json \
  | jq '.data | {job: .job.title, overall: .assessment.overall.score, screening: .assessment.screening_probability.probability}'
```

Run `boss fit` one job at a time; each call makes BOSS requests plus one TypeSafe request.

## Error Codes

Structured error codes returned in the `error.code` field (see [SCHEMA.md](./SCHEMA.md)):

- `not_authenticated` — cookies expired or missing
- `rate_limited` — too many requests (auto-cooldown built-in)
- `invalid_params` — missing or invalid parameters
- `api_error` — upstream API error (e.g. `当前登录状态已失效 (code=7)`, empty online resume, TypeSafe Jev failure)
- `unknown_error` — unexpected error

## Limitations

- **No message sending** — cannot send chat messages (MQTT/Protobuf required)
- **No resume editing** — cannot edit resume from CLI
- **No company search** — company pages return HTML (need __zp_stoken__)
- **Single account** — one set of cookies at a time
- **Rate limited** — batch-greet has built-in 1.5s delay between greetings

## Anti-Detection Notes for Agents

- **Do NOT parallelize requests** — built-in Gaussian jitter delays exist for account safety
- **Rate-limit auto-recovery**: if code=9 occurs, client auto-cools-down with increasing delays (10s→20s→40s→60s) and retries once
- **Use `-v` flag for debugging**: `boss -v search "Python"` shows request timing
- **Batch greet limit**: recommend ≤ 10 greetings per session to avoid detection
- **Cookies auto-refresh**: if ≥ 7 days old, boss-cli auto-tries browser extraction
- **Re-login if `__zp_stoken__` expires**: run `boss logout && boss login`

## Safety Notes

- Do not ask users to share raw cookie values in chat logs.
- Prefer local browser cookie extraction over manual secret copy/paste.
- If auth fails, ask the user to re-login via `boss login`.
- Agent should treat cookie values as secrets (do not echo to stdout).
- Never print `TYPESAFE_API_KEY`. `boss me --json` contains personal data; pass only `.data.resume` (identity-free) to other tools.
- Built-in rate-limit delay protects accounts; do not bypass it.
