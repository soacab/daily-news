# daily-news

本地/Codex 自动化生成的 AI 产品机会与巨头动态日报。

## 本地运行

```bash
scripts/daily-news run-daily --date 2026-05-02 --no-push
```

自动化运行时需要在环境中提供 `OPENAI_API_KEY`。密钥不写入仓库，也不需要放到 GitHub Secrets。

## 输出

- `reports/YYYY-MM-DD.md`：人读 Markdown 日报。
- `site/data/latest.json`：主页使用的最新日报数据。
- `site/data/reports/YYYY-MM-DD.json`：单期结构化数据。
- `site/data/archive.json`：归档索引。
- `site/index.html`：归藏 article 风格静态主页。

## 发布

`scripts/daily-news publish` 会提交本地变更并推送到当前 git remote。GitHub Pages 只部署静态站，不参与内容生成。
