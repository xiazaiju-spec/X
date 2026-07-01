# AI Stock Dashboard

一个用于每日自动分析 A 股、港股、美股的 Python 股票决策仪表盘基础项目。当前版本提供命令行分析、Markdown 报告、SQLite 存储、Telegram/邮箱推送和 APScheduler 定时任务，后续可扩展 Web 仪表盘。

## 功能

- 从 `config.yaml` 读取指数和自选股配置
- A 股优先使用 AKShare 获取行情
- 港股、美股优先使用 yfinance 获取行情
- 计算 MA5、MA10、MA20、MA60、RSI、MACD、成交量变化
- 指数评分和个股评分，满分 100 分
- 风控规则：跌破 MA20 扣分、跌破 MA60 标记高风险、弱指数环境限制个股建议
- 调用大模型生成 Markdown 分析报告
- 支持 Telegram 和邮箱推送
- 使用 SQLite 保存每日报告和评分结果
- 支持 Docker 和 docker-compose 部署

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py --once
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --once
```

## 配置

编辑 `config.yaml`：

- `indices`: 主要指数列表
- `watchlist`: 自选股列表
- `analysis.lookback_days`: 拉取历史天数
- `scheduler.cron`: 定时任务 cron 表达式

编辑 `.env`：

- `OPENAI_API_KEY`: 大模型 API Key
- `OPENAI_BASE_URL`: 可选，自定义 OpenAI 兼容接口
- `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`: Telegram 推送
- `SMTP_*`: 邮箱推送
- `DATABASE_PATH`: SQLite 数据库路径

所有敏感信息都从 `.env` 读取，不应写入代码或提交到仓库。

## 运行

手动运行一次完整分析：

```bash
python main.py --once
```

启动定时任务：

```bash
python main.py --schedule
```

Docker：

```bash
docker compose up --build
```

## 目录说明

- `data_provider/`: AKShare、yfinance 数据源
- `indicators/`: 技术指标计算
- `strategy/`: 指数评分、个股评分、风控规则
- `ai/`: 大模型客户端和提示词
- `report/`: Markdown 报告和控制台摘要
- `notify/`: Telegram、邮箱推送
- `database/`: SQLite 存储
- `scheduler/`: APScheduler 定时任务

## 后续扩展方向

- Web 仪表盘：FastAPI + React/Streamlit
- 日股、韩股数据源
- 行业和主题热度分析
- 多模型投票
- 回测和策略绩效归因
