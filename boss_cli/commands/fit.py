"""Opt-in job-fit assessment for a local resume and a BOSS job posting."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import click
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..client import BossClient
from ..jev import MAX_STATE_BYTES, JevServiceError, assess_job_fit, redact_contact_info, state_size_bytes
from ..resume import normalize_resume, resume_to_text
from ._common import console, handle_command, require_auth, structured_output_options

_DIMENSION_LABELS = {
    "skills": "技能匹配",
    "responsibilities": "职责匹配",
    "experience": "经验匹配",
    "company_business": "公司业务相关度（0–4）",
    "preference_alignment": "求职期望匹配（0–4）",
}

_PROFILE_FIELD_LABELS = {
    "education": "学历",
    "work_experience": "工作年限",
    "desired_positions": "期望职位",
    "desired_cities": "期望城市",
    "desired_salary": "期望薪资",
}

_REDACTION_LABELS = {
    "email": "邮箱",
    "id_number": "证件号",
    "phone": "手机号",
    "messenger_id": "微信/QQ 号",
}


@click.command()
@click.argument("security_id")
@click.option(
    "--resume-file",
    type=click.STRING,
    help="UTF-8 简历文本文件（支持 .txt/.md）；不传则使用 BOSS 在线简历",
)
@click.option("--company-context-file", type=click.STRING, help="可选：公司官网/业务介绍的 UTF-8 文本文件")
@click.option(
    "--confirm-send",
    is_flag=True,
    help="确认将简历、求职资料及职位/公司信息发送至 TypeSafe Jev 进行评估",
)
@structured_output_options
def fit(
    security_id: str,
    resume_file: str | None,
    company_context_file: str | None,
    confirm_send: bool,
    as_json: bool,
    as_yaml: bool,
) -> None:
    """使用 TypeSafe Jev 评估简历与职位的适配度（需要明确确认外发简历）。"""
    credential = require_auth()

    if not confirm_send:
        raise click.UsageError("简历、求职资料和职位/公司信息会发送至 TypeSafe Jev；确认后请添加 --confirm-send。")
    if not os.environ.get("TYPESAFE_API_KEY", "").strip():
        raise click.ClickException("未设置 TYPESAFE_API_KEY；请先配置 TypeSafe API Key。")

    local_resume = _read_resume_file(resume_file) if resume_file else ""
    company_context = _read_optional_text(company_context_file, "公司业务介绍")
    # Fail before any BOSS request when the local inputs alone exceed the Jev state limit.
    if state_size_bytes({"candidate_resume": local_resume, "company_business": company_context}) > MAX_STATE_BYTES:
        raise click.ClickException("简历与公司业务介绍合计超过 40 KB；请先精简文本后重试。")

    def _action(client: BossClient) -> dict[str, Any]:
        detail = client.get_job_detail(security_id=security_id)
        if not isinstance(detail, dict):
            raise JevServiceError("职位详情数据格式无效，无法进行适配度评估。")
        job = detail.get("jobInfo", detail)
        brand = detail.get("brandComInfo") or {}
        if not isinstance(job, dict) or not isinstance(brand, dict):
            raise JevServiceError("职位详情数据格式无效，无法进行适配度评估。")

        description = job.get("postDescription") or job.get("jobDesc") or detail.get("jobDesc") or ""
        if not isinstance(description, str) or not description.strip():
            raise JevServiceError("该职位详情缺少职位描述，无法进行可靠的语义评估。")

        skills = job.get("skills", [])
        if not isinstance(skills, (list, str)):
            skills = []

        if local_resume:
            resume_text = local_resume
            profile = client.get_resume_baseinfo()
            expectations = client.get_resume_expect()
        else:
            # The online resume carries both base info and expectations, so one request covers the profile.
            profile = expectations = client.get_resume_detail()
            resume_text = resume_to_text(normalize_resume(profile))
            if not resume_text:
                raise JevServiceError("BOSS 在线简历为空；请先完善在线简历，或通过 --resume-file 提供简历文本。")
        resume_text, redactions = redact_contact_info(resume_text)
        candidate_profile = _candidate_profile(profile, expectations)
        business = _company_business(brand, company_context, job.get("brandName", ""))

        if state_size_bytes({"candidate_resume": resume_text, "company_business": company_context}) > MAX_STATE_BYTES:
            raise JevServiceError("在线简历与公司业务介绍合计超过 40 KB；请改用 --resume-file 提供精简后的简历。")

        state = {
            "candidate_resume": resume_text,
            "candidate_profile_and_preferences": candidate_profile,
            "company_business": business["context"],
            "job_requirements": {
                "title": job.get("jobName", ""),
                "required_skills": skills,
                "experience": job.get("experienceName", job.get("jobExperience", "")),
                "education": job.get("degreeName", job.get("jobDegree", "")),
                "location": job.get("locationName", job.get("cityName", "")),
                "salary": job.get("salaryDesc", ""),
                "description": description.strip(),
            },
        }
        result = assess_job_fit(state)
        return {
            "job": {
                "security_id": security_id,
                "title": job.get("jobName", "-"),
                "company": brand.get("brandName", job.get("brandName", "-")),
                "salary": job.get("salaryDesc", "-"),
                "location": job.get("locationName", job.get("cityName", "-")),
                "business_context_source": business["source"],
            },
            **result,
            "input_summary": {
                "profile_fields_sent": [key for key in _PROFILE_FIELD_LABELS if key in candidate_profile],
                "profile_fields_missing": [key for key in _PROFILE_FIELD_LABELS if key not in candidate_profile],
                "resume_source": "file" if local_resume else "boss_online_resume",
                "resume_redactions": redactions,
            },
            "notice": (
                "模型评估仅供求职参考；0–4 评分不是百分比。初筛概率是 Jev 对简历通过初筛的模型概率，"
                "不是该公司基于历史招聘数据统计的录用率，也不代表最终 offer 概率。请人工复核。"
            ),
        }

    handle_command(
        credential,
        action=_action,
        render=_render_fit,
        as_json=as_json,
        as_yaml=as_yaml,
    )


def _render_fit(data: dict[str, Any]) -> None:
    """Render a concise fit breakdown without echoing the resume text."""
    job = data["job"]
    assessment = data["assessment"]
    table = Table(title="岗位适配度评估", show_lines=True)
    table.add_column("评估维度", style="bold")
    table.add_column("结果")
    table.add_column("置信度 / 说明", style="dim")

    overall = assessment["overall"]
    table.add_row(
        "整体适配度（0–4）",
        f"{overall['score']:.2f} / 4",
        _format_confidence(overall.get("confidence")),
    )
    probability = assessment["screening_probability"]["probability"]
    table.add_row("简历初筛入选概率", f"{probability:.0%}", "Jev 模型概率；非公司历史录用率")
    for key, label in _DIMENSION_LABELS.items():
        answer = assessment[key]
        result = f"{answer['score']:.2f} / 4" if "score" in answer else answer["label"]
        table.add_row(label, result, _format_confidence(answer.get("confidence")))

    heading = Text(f"{job['title']} @ {job['company']}  ·  {job['salary']}  ·  {job['location']}")
    console.print(Panel(heading, title=Text("📋 职位")))
    console.print(table)

    summary = data["input_summary"]
    missing = [_PROFILE_FIELD_LABELS[key] for key in summary["profile_fields_missing"]]
    if missing:
        console.print(
            f"[yellow]⚠️  未从 BOSS 资料中取到：{escape('、'.join(missing))}；"
            "求职期望匹配仅基于已取到的信息，参考价值有限。[/yellow]"
        )
    redactions = summary["resume_redactions"]
    if redactions:
        removed = "、".join(f"{_REDACTION_LABELS.get(key, key)} {count} 处" for key, count in redactions.items())
        console.print(f"[dim]外发前已从简历中移除：{escape(removed)}。[/dim]")
    console.print(
        f"[dim]公司业务信息来源：{escape(job['business_context_source'])}。{escape(data['notice'])} "
        f"模型：{escape(data['model'])}。简历文本不会回显到终端。[/dim]"
    )


def _format_confidence(value: float | None) -> str:
    if value is None:
        return "未提供"
    return f"{value:.0%}（不保证单次判断正确）"


def _read_resume_file(resume_file: str) -> str:
    path = Path(resume_file).expanduser()
    if not path.is_file():
        raise click.ClickException(f"简历文件不存在或不是普通文件：{path}")
    try:
        if path.stat().st_size > MAX_STATE_BYTES:
            raise click.ClickException("简历文件超过 40 KB；请先精简文本后重试。")
    except OSError as exc:
        raise click.ClickException(f"无法检查简历文件：{exc}") from exc
    try:
        resume_text = path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError as exc:
        raise click.ClickException("简历文件不是 UTF-8 文本；请先转换为 UTF-8 的 .txt 或 .md 文件。") from exc
    except OSError as exc:
        raise click.ClickException(f"无法读取简历文件：{exc}") from exc
    if not resume_text:
        raise click.ClickException("简历文件为空。")
    return resume_text


def _read_optional_text(file_path: str | None, label: str) -> str:
    if not file_path:
        return ""
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise click.ClickException(f"{label}文件不存在或不是普通文件：{path}")
    try:
        if path.stat().st_size > MAX_STATE_BYTES:
            raise click.ClickException(f"{label}文件超过 40 KB；请先精简文本后重试。")
        text = path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError as exc:
        raise click.ClickException(f"{label}文件不是 UTF-8 文本。") from exc
    except OSError as exc:
        raise click.ClickException(f"无法读取{label}文件：{exc}") from exc
    if not text:
        raise click.ClickException(f"{label}文件为空。")
    return text


def _candidate_profile(base_info: Any, expectations: Any) -> dict[str, str]:
    """Keep job-relevant profile fields; omit name, contact, gender, and age.

    Only human-readable strings are sent: BOSS often returns numeric codes (city, position)
    alongside display names, and a bare code would mislead the model.
    """
    profile_sources = _nested_dicts(base_info)
    expectation_sources = _nested_dicts(expectations)
    aliases = {
        "education": (profile_sources, ("degreeCategory", "degreeName", "degree", "highestDegree")),
        "work_experience": (profile_sources, ("workYearDesc", "workYearsDesc", "workYear")),
        "desired_positions": (
            expectation_sources,
            ("expectPositionName", "positionName", "expectPosition", "expectJobTitle"),
        ),
        "desired_cities": (expectation_sources, ("expectCityName", "locationName", "cityName", "expectCity")),
        "desired_salary": (expectation_sources, ("salaryDesc", "expectSalaryDesc", "expectSalary")),
    }
    profile: dict[str, str] = {}
    for label, (sources, keys) in aliases.items():
        values: list[str] = []
        for source in sources:
            # Aliases are ordered by preference; take one value per source to avoid near-duplicates.
            for key in keys:
                value = source.get(key)
                if isinstance(value, str) and value.strip() and not value.strip().isdigit():
                    normalized = value.strip()
                    if normalized not in values:
                        values.append(normalized)
                    break
        if values:
            profile[label] = "；".join(values)
    return profile


def _nested_dicts(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    sources = [data]
    for key in ("baseInfo", "geekBaseInfo", "expectInfo", "resumeExpect", "expect", "expectList", "expectationList"):
        nested = data.get(key)
        if isinstance(nested, dict):
            sources.append(nested)
        elif isinstance(nested, list):
            sources.extend(item for item in nested if isinstance(item, dict))
    return sources


def _company_business(brand: dict[str, Any], user_context: str, fallback_name: str) -> dict[str, Any]:
    company: dict[str, str] = {}
    if isinstance(brand.get("brandName"), str) and brand["brandName"].strip():
        company["name"] = brand["brandName"].strip()
    elif isinstance(fallback_name, str) and fallback_name.strip():
        company["name"] = fallback_name.strip()

    for label, key in (
        ("industry", "industryName"),
        ("company_size", "scaleName"),
        ("funding_stage", "stageName"),
    ):
        value = brand.get(key)
        if isinstance(value, str) and value.strip():
            company[label] = value.strip()

    description_keys = ("brandIntro", "brandDescription", "brandDesc", "companyIntroduction", "introduce")
    brand_description = next(
        (brand[key].strip() for key in description_keys if isinstance(brand.get(key), str) and brand[key].strip()),
        "",
    )
    descriptions = list(dict.fromkeys(text for text in (user_context.strip(), brand_description) if text))
    if descriptions:
        company["business_description"] = "\n\n".join(descriptions)
    else:
        company["business_description"] = ""

    if user_context and brand_description:
        source = "用户提供的介绍 + BOSS 公司资料"
    elif user_context:
        source = "用户提供的公司业务介绍"
    elif brand_description:
        source = "BOSS 公司资料中的业务介绍"
    elif any(key in company for key in ("industry", "company_size", "funding_stage")):
        source = "BOSS 基础公司信息（缺少具体业务介绍）"
    else:
        source = "信息不足；可用 --company-context-file 补充"
    return {"context": company, "source": source}
