# SCHEMA.md — Structured Output Contract

This is the machine-readable contract for scripts and AI agents. Pass `--json` to every command that supports it.

## Envelope

Commands with `--json` / `--yaml` print exactly one envelope to **stdout**. Rich tables, progress and hints go to **stderr**, so `boss search X --json | jq .data` is always clean.

### Success

```json
{
  "ok": true,
  "schema_version": "1",
  "data": { ... }
}
```

### Error

```json
{
  "ok": false,
  "schema_version": "1",
  "data": null,
  "error": {
    "code": "not_authenticated",
    "message": "环境异常 (__zp_stoken__ 已过期)。请重新登录: boss logout && boss login"
  }
}
```

Branch on `ok` and `error.code`. `error.message` is human-readable Chinese text and may change between versions.

## Error Codes

| Code | Description | Suggested agent action |
|------|-------------|------------------------|
| `not_authenticated` | Session expired or not logged in (BOSS code 37) | Ask the user to log in to zhipin.com in a browser, then `boss logout && boss login` |
| `rate_limited` | Too many requests (BOSS code 9); the client already cooled down and retried once | Stop and wait several minutes; do not retry in a loop |
| `invalid_params` | Missing or invalid parameters (BOSS code 17/19) | Fix the arguments |
| `api_error` | Any other upstream or service error — e.g. `当前登录状态已失效 (code=7)`, security block (code 121/122), empty online resume, TypeSafe Jev failure | Show `error.message` to the user |
| `unknown_error` | Unexpected error | Show `error.message` to the user |

## Exit Codes

| Exit | Situation | stdout |
|------|-----------|--------|
| `0` | Success | Success envelope |
| `1` | API / runtime error | Error envelope (with `--json`, `--yaml`, or non-TTY stdout) |
| `1` | Not logged in — no saved credential, no `BOSS_COOKIES`, no browser cookies | Empty; `未登录` on stderr |
| `1` | Confirmation prompt aborted (no `-y` and stdin is not interactive) | Empty |
| `2` | Usage error: unknown option, missing argument, `boss fit` without `--confirm-send` | Empty; Click usage message on stderr |

An agent should treat "exit ≠ 0 and empty stdout" as a local precondition failure and read stderr.

## Format Selection

- `--json` → JSON (recommended for agents).
- `--yaml` → YAML; falls back to JSON when `pyyaml` is not installed.
- No flag and stdout is **not** a TTY → YAML if `pyyaml` is installed (`kabi-boss-cli[yaml]`), otherwise JSON.
- No flag and stdout is a TTY → Rich output on stderr, nothing on stdout.

## Exceptions to the Envelope

| Command | Output |
|---------|--------|
| `boss status --json` | Bare object, no envelope: `{"authenticated", "credential_present", "cookie_count", "cookies", "search_authenticated", "recommend_authenticated", "reason"}` (only `authenticated` and `credential_present` when no credential exists). `cookies` lists names only, never values. |
| `boss export` | CSV or JSON rows written to `-o` or stdout (`--format csv\|json`) |
| `boss recruiter export`, `boss recruiter resume-download` | Files written to disk |
| `boss login`, `boss logout`, `boss cities`, `boss batch-greet`, `boss recruiter batch-view`, `boss recruiter job-close`, `boss recruiter job-reopen` | Rich output only |

## Selected Payloads

`data` mirrors BOSS's `zpData` for most commands (e.g. `boss search` → `data.jobList[]` with `securityId`, `lid`, `jobName`, `brandName`, `salaryDesc`, `cityName`, `skills`). The following commands shape their own payloads.

### `boss me --json`

Top-level fields are BOSS base info (`name`, `nickName`, `age`, `gender`, `degreeCategory`, `workYearDesc`, `account`, …) — these contain personal data. The normalized online resume is under `data.resume` and **excludes** name, account, birthday, age, gender, email and WeChat:

```json
{
  "degree": "本科",
  "work_years": "6年经验",
  "advantage": "个人优势文本",
  "professional_skill": "专业技能文本",
  "expectations": [{ "position": "Python", "city": "北京", "salary": "20-30K", "industry": "互联网" }],
  "work_experience": [{ "company": "…", "position": "…", "department": "…", "period": "2022.09 - 至今", "content": "…", "performance": "…", "skills": "…" }],
  "project_experience": [{ "name": "…", "role": "…", "period": "2023.01 - 2025.01", "description": "…", "performance": "…" }],
  "education": [{ "school": "…", "major": "…", "degree": "本科", "period": "2016 - 2020", "description": "…" }],
  "certifications": ["…"],
  "last_update": "2026.09.23 22:16"
}
```

Empty fields and empty sections are omitted. `boss me --basic --json` returns only the base info (no `resume` key).

### `boss fit <securityId> --confirm-send --json`

```json
{
  "job": { "security_id": "…", "title": "…", "company": "…", "salary": "…", "location": "…", "business_context_source": "…" },
  "model": "jev-latest",
  "assessment": {
    "skills":           { "choice": "partial_match", "label": "部分匹配", "confidence": 0.7, "probabilities": { … } },
    "responsibilities": { "choice": "…", "label": "…", "confidence": 0.0, "probabilities": { … } },
    "experience":       { "choice": "…", "label": "…", "confidence": 0.0, "probabilities": { … } },
    "company_business":     { "score": 2.6, "scale": "0–4（模型评分，不是百分比）", "confidence": 0.5, "probabilities": { … } },
    "preference_alignment": { "score": 0.0, "scale": "…", "confidence": 0.0, "probabilities": { … } },
    "overall":              { "score": 0.0, "scale": "…", "confidence": 0.0, "probabilities": { … } },
    "screening_probability": { "probability": 0.42, "label": "简历初筛通过概率（非公司历史发生率）" }
  },
  "input_summary": {
    "resume_source": "boss_online_resume",
    "profile_fields_sent": ["education", "work_experience", "desired_positions", "desired_cities", "desired_salary"],
    "profile_fields_missing": [],
    "resume_redactions": { "email": 1 }
  },
  "notice": "模型评估仅供求职参考；…"
}
```

- `choice` ∈ `strong_match`, `partial_match`, `clear_gap`, `insufficient_evidence`.
- Scores are 0–4, not percentages. `confidence` and `probabilities` may be `null`.
- `resume_source` is `boss_online_resume` (default) or `file` (`--resume-file`).
- The resume text itself is never echoed in the output.
