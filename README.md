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

## 首次 GitHub 设置

当前实现假设你会新建一个公开仓库并把它设为 `origin`。如果使用 GitHub CLI，可以在本机重新登录后运行：

```bash
gh auth login -h github.com
gh repo create daily-news --public --source=. --remote=origin --push
```

如果不用 GitHub CLI，也可以在网页上新建 `daily-news` 仓库，再运行：

```bash
git remote add origin git@github.com:<your-user>/daily-news.git
git push -u origin main
```

## Codex 自动化

Codex app 里已有一个每日任务 `daily-news local generator`，计划每天北京时间 08:00 在本地运行：

```bash
scripts/daily-news run-daily
```

请在 Codex 自动化运行环境里提供 `OPENAI_API_KEY`，并确保本机 git remote 与 GitHub 凭据可用。GitHub Actions workflow 只部署 `site/`，不会读取 OpenAI key。
