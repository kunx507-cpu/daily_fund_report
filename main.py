import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

import requests


CN_TZ = timezone(timedelta(hours=8))


def get_env(name, default=""):
    return os.getenv(name, default).strip()


def parse_jsonp(text):
    match = re.search(r"\((\{.*\})\)", text, re.S)
    if not match:
        raise ValueError("JSONP response format not recognized")
    return json.loads(match.group(1))


def fetch_fund_realtime(code):
    url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time() * 1000)}"
    response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    data = parse_jsonp(response.text)
    return {
        "code": code,
        "name": data.get("name", "未知基金"),
        "unit_nav_date": data.get("jzrq", "N/A"),
        "unit_nav": data.get("dwjz", "N/A"),
        "estimate_nav": data.get("gsz", "N/A"),
        "estimate_change": data.get("gszzl", "N/A"),
        "estimate_time": data.get("gztime", "N/A"),
    }


def build_basic_report(funds):
    now = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M")
    lines = [
        f"📊 每日基金盘中估算日报",
        f"时间: {now}",
        "用途: 14:30 盘中估算，辅助 15:00 前判断是否调整。",
        "",
    ]

    for fund in funds:
        lines.extend(
            [
                f"### {fund['name']} ({fund['code']})",
                f"- 净值日期: {fund['unit_nav_date']}",
                f"- 单位净值: {fund['unit_nav']}",
                f"- 估算净值: {fund['estimate_nav']}",
                f"- 估算涨跌: {fund['estimate_change']}%",
                f"- 估算时间: {fund['estimate_time']}",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "数据来自公开基金净值接口。盘中估算可能与晚间正式净值存在偏差，仅供参考，不构成投资建议。",
        ]
    )
    return "\n".join(lines)


def build_ai_summary(basic_report):
    api_key = get_env("OPENAI_API_KEY")
    base_url = get_env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = get_env("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        return ""

    prompt = (
        "你是严谨的基金盘中观察助手。请基于下面的基金盘中估算数据，输出中文分析。"
        "要求：不要编造未给出的持仓、同类排名、基金经理或新闻；"
        "重点说明每只基金今天估算涨跌、可能的短期风险、明日观察重点；"
        "最后给出一个保守的操作倾向，只能在“偏加仓 / 观望 / 偏减仓”三者里选，"
        "并解释理由。这个倾向必须写成辅助判断，不要写成确定性投资建议。"
        "如果数据不足，优先给“观望”。\n\n"
        f"{basic_report}"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严谨的基金日报分析助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    response = requests.post(
        f"{base_url}/v1/chat/completions" if not base_url.endswith("/v1") else f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def send_wechat(content):
    webhook = get_env("WECHAT_WEBHOOK_URL")
    if not webhook:
        raise RuntimeError("WECHAT_WEBHOOK_URL is not configured")

    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content[:3900]},
    }
    response = requests.post(webhook, json=payload, timeout=15)
    response.raise_for_status()
    result = response.json()
    if result.get("errcode") != 0:
        raise RuntimeError(f"WeChat webhook failed: {result}")


def main():
    fund_list = get_env("FUND_LIST")
    if not fund_list:
        raise RuntimeError("FUND_LIST is not configured")

    codes = [item.strip() for item in fund_list.split(",") if item.strip()]
    funds = []
    errors = []

    for code in codes:
        try:
            funds.append(fetch_fund_realtime(code))
        except Exception as exc:
            errors.append(f"{code}: {exc}")

    if not funds:
        raise RuntimeError("No fund data fetched. " + "; ".join(errors))

    report = build_basic_report(funds)
    try:
        summary = build_ai_summary(report)
    except Exception as exc:
        summary = f"AI 简评生成失败: {exc}"

    if summary:
        report = f"{report}\n\n## AI 简评\n{summary}"

    if errors:
        report = f"{report}\n\n## 数据异常\n" + "\n".join(f"- {item}" for item in errors)

    print(report)
    send_wechat(report)


if __name__ == "__main__":
    main()
