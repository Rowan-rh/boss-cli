"""Normalize the BOSS online resume (geek preview) for display and job-fit assessment."""

from __future__ import annotations

from typing import Any

# Contact and identity fields are intentionally absent from the normalized resume:
# name, account, birthday, age, gender, email and WeChat stay in the raw base info only.


def _text(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _items(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _period(item: dict[str, Any], start_keys: tuple[str, ...], end_keys: tuple[str, ...]) -> str:
    start = _text(item, *start_keys)
    end = _text(item, *end_keys)
    if start and end:
        return f"{start} - {end}"
    return start or end


def _compact(entry: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in entry.items() if value}


def normalize_resume(data: Any) -> dict[str, Any]:
    """Extract job-relevant sections from `/wapi/zpgeek/resume/geek/preview/data.json` zpData."""
    if not isinstance(data, dict):
        return {}
    base = data.get("baseInfo") if isinstance(data.get("baseInfo"), dict) else {}

    expectations = [
        _compact({
            "position": _text(item, "positionName"),
            "city": _text(item, "locationName"),
            "salary": _text(item, "salaryDesc", "salaryDescNew"),
            "industry": _text(item, "industryDesc"),
        })
        for item in _items(data, "expectList")
    ]
    work = [
        _compact({
            "company": _text(item, "companyName"),
            "position": _text(item, "positionName", "customPositionName"),
            "department": _text(item, "department"),
            "period": _period(item, ("startDateStr", "startDate"), ("endDateStr", "endDate")),
            "content": _text(item, "workContent"),
            "performance": _text(item, "workPerformance"),
            "skills": _text(item, "emphasis"),
        })
        for item in _items(data, "workExpList")
    ]
    projects = [
        _compact({
            "name": _text(item, "name"),
            "role": _text(item, "roleName"),
            "period": _period(item, ("startDateStr", "startDate"), ("endDateStr", "endDate")),
            "description": _text(item, "projectDesc"),
            "performance": _text(item, "performance"),
        })
        for item in _items(data, "projectExpList")
    ]
    education = [
        _compact({
            "school": _text(item, "school"),
            "major": _text(item, "major"),
            "degree": _text(item, "degreeName"),
            "period": _period(item, ("startYearStr", "startYear"), ("endYearStr", "endYear")),
            "description": _text(item, "educationDesc"),
        })
        for item in _items(data, "educationExpList")
    ]
    certifications = [
        name for item in _items(data, "certificationList") if (name := _text(item, "certName", "name"))
    ]

    resume = {
        "degree": _text(base, "degreeCategory"),
        "work_years": _text(base, "workYearDesc"),
        "advantage": _text(data, "userDesc"),
        "professional_skill": _text(data, "professionalSkill"),
        "expectations": [item for item in expectations if item],
        "work_experience": [item for item in work if item],
        "project_experience": [item for item in projects if item],
        "education": [item for item in education if item],
        "certifications": certifications,
        "last_update": _text(data, "lastUpdateTime"),
    }
    return {key: value for key, value in resume.items() if value}


def resume_to_text(resume: dict[str, Any]) -> str:
    """Render a normalized resume as plain text for external assessment (no identity fields)."""
    lines: list[str] = []

    def section(title: str) -> None:
        if lines:
            lines.append("")
        lines.append(f"## {title}")

    summary = "，".join(value for value in (resume.get("degree"), resume.get("work_years")) if value)
    if summary:
        section("概况")
        lines.append(summary)
    if resume.get("advantage"):
        section("个人优势")
        lines.append(resume["advantage"])
    if resume.get("professional_skill"):
        section("专业技能")
        lines.append(resume["professional_skill"])
    if resume.get("expectations"):
        section("求职期望")
        for item in resume["expectations"]:
            lines.append("- " + " | ".join(item.values()))
    if resume.get("work_experience"):
        section("工作经历")
        for item in resume["work_experience"]:
            lines.append("### " + " | ".join(v for v in (item.get("company"), item.get("position"), item.get("period")) if v))
            if item.get("department"):
                lines.append(f"部门：{item['department']}")
            if item.get("skills"):
                lines.append(f"技能标签：{item['skills']}")
            if item.get("content"):
                lines.append(f"工作内容：{item['content']}")
            if item.get("performance"):
                lines.append(f"工作业绩：{item['performance']}")
    if resume.get("project_experience"):
        section("项目经历")
        for item in resume["project_experience"]:
            lines.append("### " + " | ".join(v for v in (item.get("name"), item.get("role"), item.get("period")) if v))
            if item.get("description"):
                lines.append(f"项目描述：{item['description']}")
            if item.get("performance"):
                lines.append(f"项目业绩：{item['performance']}")
    if resume.get("education"):
        section("教育经历")
        for item in resume["education"]:
            lines.append("- " + " | ".join(v for v in (item.get("school"), item.get("major"), item.get("degree"), item.get("period")) if v))
            if item.get("description"):
                lines.append(f"  {item['description']}")
    if resume.get("certifications"):
        section("资格证书")
        lines.append("、".join(resume["certifications"]))
    return "\n".join(lines).strip()
