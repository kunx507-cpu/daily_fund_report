# daily_fund_report

每天自动查询场外基金净值，并通过企业微信机器人推送日报。

## 需要配置的 GitHub Secrets

在仓库里进入：

`Settings -> Secrets and variables -> Actions -> New repository secret`

逐个添加：

```text
FUND_LIST=011612,008282,012920,016452
WECHAT_WEBHOOK_URL=你的企业微信机器人Webhook
OPENAI_API_KEY=你的模型API Key
OPENAI_BASE_URL=https://ttapi.love.gd
OPENAI_MODEL=GPT-5.5
```

`OPENAI_*` 不填也能推送基础净值日报；填了会多一段 AI 简评。

## 手动运行

进入 GitHub 仓库：

`Actions -> 每日基金净值日报 -> Run workflow`

## 自动运行

默认每个工作日北京时间 14:30 运行。

这个时间点使用的是盘中估算数据，适合在 15:00 前辅助判断当天是否调整基金操作。正式单位净值通常要晚上才更新。
