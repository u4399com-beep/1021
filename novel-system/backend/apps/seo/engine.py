"""SEO detection engine — runs a battery of checks against a Site record.

Each check returns: {check, severity, ok, message, suggestion}
severity: error | warning | info
"""

import re
from dataclasses import dataclass
from typing import Any

from apps.sites.models import Site


# ------------------------------------------------------------------
# Individual checks
# ------------------------------------------------------------------
@dataclass
class CheckResult:
    check: str
    severity: str   # error | warning | info | ok
    ok: bool
    message: str
    suggestion: str = ""


def check_site_title(site: Site) -> CheckResult:
    v = site.site_title or ""
    if not v:
        return CheckResult("site_title", "error", False, "首页标题未设置", "在站点设置中填写 SEO 标题")
    if len(v) > 60:
        return CheckResult("site_title", "warning", True, f"标题偏长({len(v)}字符)，超过 60 字符建议", "精简标题，控制在 30-60 字符")
    if len(v) < 10:
        return CheckResult("site_title", "warning", True, f"标题过短({len(v)}字符)", "建议 30-60 字符")
    return CheckResult("site_title", "ok", True, f"标题长度合适({len(v)}字符)")


def check_site_description(site: Site) -> CheckResult:
    v = site.site_description or ""
    if not v:
        return CheckResult("site_description", "error", False, "首页描述未设置", "填写 description meta，建议 100-200 字符")
    if len(v) > 200:
        return CheckResult("site_description", "warning", True, f"描述偏长({len(v)}字符)", "建议 100-200 字符")
    if len(v) < 50:
        return CheckResult("site_description", "warning", True, f"描述过短({len(v)}字符)", "建议 100-200 字符")
    return CheckResult("site_description", "ok", True, f"描述长度合适({len(v)}字符)")


def check_site_keywords(site: Site) -> CheckResult:
    v = site.site_keywords or ""
    if not v:
        return CheckResult("site_keywords", "warning", False, "首页关键词未设置", "填写 keywords meta，5-10 个关键词")
    n = len([k for k in v.split(",") if k.strip()])
    if n > 10:
        return CheckResult("site_keywords", "warning", True, f"关键词过多({n}个)", "建议 5-10 个核心关键词")
    if n < 3:
        return CheckResult("site_keywords", "warning", True, f"关键词过少({n}个)", "建议 5-10 个")
    return CheckResult("site_keywords", "ok", True, f"关键词数量合适({n}个)")


def check_canonical(site: Site) -> CheckResult:
    v = (site.canonical_domain or "").strip()
    if not v:
        return CheckResult("canonical_domain", "warning", False, "未设置 canonical 域名", "填写 canonical 域名以避免重复内容惩罚")
    if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", v):
        return CheckResult("canonical_domain", "warning", True, f"canonical 域名格式可疑: {v}", "应为域名格式，例：example.com")
    return CheckResult("canonical_domain", "ok", True, f"canonical 已设置: {v}")


def check_geo_region(site: Site) -> CheckResult:
    v = (site.geo_region or "").strip()
    if not v:
        return CheckResult("geo_region", "warning", False, "GEO 地区未设置", "建议设置 geo_region（如 CN / US）")
    return CheckResult("geo_region", "ok", True, f"GEO 地区已设置: {v}")


def check_geo_lang(site: Site) -> CheckResult:
    v = (site.geo_lang or "").strip()
    if not v:
        return CheckResult("geo_lang", "warning", False, "GEO 语言未设置", "建议设置 geo_lang（如 zh-CN）")
    return CheckResult("geo_lang", "ok", True, f"GEO 语言已设置: {v}")


def check_robots_txt(site: Site) -> CheckResult:
    v = (site.robots_txt or "").strip()
    if not v:
        return CheckResult("robots_txt", "error", False, "robots.txt 未设置", "建议至少设置 User-agent: * / Allow: /")
    if "User-agent" not in v:
        return CheckResult("robots_txt", "warning", True, "robots.txt 缺少 User-agent", "添加 User-agent: *")
    return CheckResult("robots_txt", "ok", True, "robots.txt 已设置")


def check_sitemap_enabled(site: Site) -> CheckResult:
    if not site.sitemap_enabled:
        return CheckResult("sitemap_enabled", "warning", False, "Sitemap 未启用", "建议开启 sitemap 自动生成")
    return CheckResult("sitemap_enabled", "ok", True, "Sitemap 已启用")


def check_favicon(site: Site) -> CheckResult:
    v = (site.favicon or "").strip()
    if not v:
        return CheckResult("favicon", "info", False, "favicon 未设置", "建议设置 favicon 图标")
    return CheckResult("favicon", "ok", True, "favicon 已设置")


def check_head_inject(site: Site) -> CheckResult:
    v = (site.head_inject or "").strip()
    if not v:
        return CheckResult("head_inject", "info", True, "Head 注入未设置", "可在 head_inject 注入验证码、统计代码等")
    return CheckResult("head_inject", "ok", True, "Head 注入已设置")


def check_body_inject(site: Site) -> CheckResult:
    v = (site.body_inject or "").strip()
    if not v:
        return CheckResult("body_inject", "info", True, "Body 注入未设置", "可在 body_inject 注入统计/广告代码")
    return CheckResult("body_inject", "ok", True, "Body 注入已设置")


def check_logo(site: Site) -> CheckResult:
    v = (site.logo or "").strip()
    if not v:
        return CheckResult("logo", "info", False, "Logo 未设置", "建议设置站点 logo")
    return CheckResult("logo", "ok", True, "Logo 已设置")


# ------------------------------------------------------------------
# Aggregate runner
# ------------------------------------------------------------------
CHECKS = (
    check_site_title,
    check_site_description,
    check_site_keywords,
    check_canonical,
    check_geo_region,
    check_geo_lang,
    check_robots_txt,
    check_sitemap_enabled,
    check_favicon,
    check_head_inject,
    check_body_inject,
    check_logo,
)


def run_audit(site: Site) -> dict[str, Any]:
    """Run all checks against a site; return aggregated report."""
    results = [fn(site) for fn in CHECKS]
    score = sum(1 for r in results if r.severity in ("ok", "info")) / len(results) * 100
    return {
        "site_id": site.id,
        "site_host": site.host,
        "score": round(score, 1),
        "checks": [
            {
                "check": r.check,
                "severity": r.severity,
                "ok": r.ok,
                "message": r.message,
                "suggestion": r.suggestion,
            }
            for r in results
        ],
        "summary": {
            "errors":   sum(1 for r in results if r.severity == "error"),
            "warnings": sum(1 for r in results if r.severity == "warning"),
            "infos":    sum(1 for r in results if r.severity == "info"),
            "oks":      sum(1 for r in results if r.severity == "ok"),
        },
    }


def run_audit_all_sites() -> list[dict]:
    return [run_audit(s) for s in Site.objects.filter(is_active=True)]
