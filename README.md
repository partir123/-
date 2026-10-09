# Local Deep Researcher：本地深度研究助手

本仓库基于 [langchain-ai/local-deep-researcher](https://github.com/langchain-ai/local-deep-researcher) 二次开发，保留上游来源与 MIT 许可证。现已接入 **DeepSeek 云端 API**，并保留 [Ollama](https://ollama.com/search) 和 [LMStudio](https://lmstudio.ai/) 本地模型入口。

输入研究主题后，程序生成查询、检索网页、总结资料，并按配置反思和继续检索；最终返回 Markdown 总结及本次收集的来源。使用 DeepSeek 时，Python 流程在本机运行、模型推理在云端完成，不需要下载本地模型。网页检索仍需要联网，问题和检索内容会发送给模型服务。

![本地深度研究助手工作流程](https://github.com/user-attachments/assets/1c6b28f8-6b64-42ba-a491-1ab2875d50ea)

简短演示视频：
<video src="https://github.com/user-attachments/assets/02084902-f067-4658-9683-ff312cab7944" controls></video>

## 🔥 更新记录

### 2026-10-09：本仓库 API 接入与搜索修复

- 新增 `LLM_PROVIDER=deepseek`，通过本地环境变量 `DEEPSEEK_API_KEY` 读取凭证。查询与反思使用 JSON 输出，总结通过同一个 `get_llm()` 入口使用普通文本输出。
- DeepSeek 当前适配使用非思考模式，接口地址固定为 `https://api.deepseek.com`，请求超时配置为 90 秒，自动重试为 0，单次输出上限为 2048 tokens；这些是代码内的配置，不是新增的 `.env` 开关。
- 将旧 `duckduckgo-search` 依赖迁移为 `ddgs==9.16.0`，显式选择 DuckDuckGo 后端，检查返回条目的标题、URL 和摘要。
- DuckDuckGo 请求失败或没有有效来源时停止当前研究流程，分别报告 `SEARCH_REQUEST_FAILED` 或 `SEARCH_NO_RESULTS`，不再用空检索结果继续生成总结。该保护范围是当前 DuckDuckGo 适配器，不代表所有搜索后端都已完成相同加固。
- 增加云端 API 配置示例、中文启动说明，并保留本地环境、缓存及备份的 Git 忽略规则。

**当日验证记录：**维护者在 Windows + Python 3.11 环境中完成了项目导入、DeepSeek API/JSON 检查，以及一个 CAN 总线问题的端到端运行，搜索返回 3 条有效来源并保存了报告。运行样例见 [CAN 总线报告](deepseek_report_ddgs_20261009-164239-200472.md)。这是一次运行样例，不是多场景回归或正文事实准确性的认证；本次文档整合未另行使用真实 Key 调用 API。

### 上游历史记录

* 8/6/25：新增对工具调用和 [gpt-oss](https://openai.com/index/introducing-gpt-oss/) 的支持。

> ⚠️ **注意（8/6/25）**：`gpt-oss` 模型在 Ollama 中不支持 JSON 模式。请在配置中启用 `use_tool_calling`，使用工具调用替代 JSON 模式。

## 📺 视频教程

希望查看实际运行效果，或者自己动手搭建？可以参考以下视频教程：
- [使用 R1 的 Local Deep Researcher 概览](https://www.youtube.com/watch?v=sGUjmyfof4Q)：加载并测试 [DeepSeek R1](https://api-docs.deepseek.com/news/news250120) 的[蒸馏模型](https://ollama.com/library/deepseek-r1)。
- [从零构建 Local Deep Researcher](https://www.youtube.com/watch?v=XGuTzHoqlj8)：介绍项目的构建过程。

## 🚀 快速开始

### 使用 DeepSeek API（Windows / PowerShell）

以下是本仓库新增的云端运行路径，不需要安装 Ollama 或 LMStudio。先准备 Git、[uv](https://docs.astral.sh/uv/getting-started/installation/) 和在 DeepSeek 官方平台申请的 API Key。接口与模型信息可查阅 [DeepSeek 官方文档](https://api-docs.deepseek.com/zh-cn/)。下面使用当日运行日志中的 `deepseek-flash`；第三方平台的 Key 不适用于代码中固定的官方接口地址。

#### 1. 克隆本仓库并准备环境

```powershell
git clone https://github.com/partir123/-.git local-deep-researcher
cd local-deep-researcher
uv python install 3.11
uv sync --locked --python 3.11
```

已有仓库和环境时，先保存本地改动并同步远端，不要重复克隆。`--locked` 会在锁文件与依赖声明不一致时报错，不会自动改写锁文件。命令用法见 [uv 官方文档](https://docs.astral.sh/uv/concepts/projects/sync/)。

#### 2. 配置本地 `.env`

仅在 `.env` 不存在时复制模板，避免覆盖已有 Key：

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
notepad .env
```

在本地填写或核对以下配置。同名变量只保留一行：

```dotenv
LLM_PROVIDER=deepseek
LOCAL_LLM=deepseek-flash
DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY

SEARCH_API=duckduckgo
MAX_WEB_RESEARCH_LOOPS=0
FETCH_FULL_PAGE=false
USE_TOOL_CALLING=false
STRIP_THINKING_TOKENS=true

LANGSMITH_TRACING=false
LANGCHAIN_TRACING_V2=false
```

把占位符换成你自己的真实 Key，保存为 `.env`，不要保存为 `.env.txt`。**真实 Key 不能写进源码、README、提交记录或公开日志。**确认它未被 Git 跟踪：

```powershell
git check-ignore -v .env
git ls-files -- .env
```

第一条应显示忽略规则，第二条应没有输出。`.env.example` 只包含占位符，可以提交。本说明中的命令通过 `uv run --env-file .env` 显式加载配置；普通 `python` 启动不会因为目录里有 `.env` 就自动读取它。LangGraph CLI 的环境加载由 `langgraph.json` 配置。

#### 3. 检查导入和 API

导入检查不调用模型：

```powershell
uv run --locked --env-file .env python -c "from ollama_deep_researcher.graph import graph; print('Graph import OK')"
```

下面的独立 API 检查会发出一次模型请求并产生用量，不执行网页搜索。把整段粘贴到 PowerShell：

```powershell
@'
import json
from ollama_deep_researcher.configuration import Configuration
from ollama_deep_researcher.graph import get_llm

cfg = Configuration.from_runnable_config()
if cfg.llm_provider != "deepseek" or cfg.use_tool_calling:
    raise SystemExit("Set LLM_PROVIDER=deepseek and USE_TOOL_CALLING=false.")

reply = get_llm(cfg, structured_output=True).invoke([
    ("human", 'Return only this JSON object: {"status": "ok"}')
])
if json.loads(reply.content) != {"status": "ok"}:
    raise SystemExit("JSON validation failed.")

print("DeepSeek API OK")
print("JSON validation OK")
print("Usage:", getattr(reply, "usage_metadata", None))
'@ | uv run --locked --env-file .env python -
```

#### 4. 生成研究报告

完整流程会多次调用模型。先使用公开问题；以下示例保留当日首跑的英文主题。模型生成的最终正文仍需人工核对。

```powershell
@'
from datetime import datetime
from pathlib import Path
from ollama_deep_researcher.graph import graph

print("Starting research...", flush=True)
result = graph.invoke({
    "research_topic": "What is CAN bus? Explain its purpose and basic operation with sources."
})
report = result["running_summary"]
_, separator, sources = report.rpartition("### Sources:")
if not separator or not sources.strip():
    raise SystemExit("Final sources are empty. No report saved.")

stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
output = Path(f"deepseek_report_ddgs_{stamp}.md")
output.write_text(report, encoding="utf-8")
print(report)
print("Saved:", output.resolve())
'@ | uv run --locked --env-file .env python -u -
```

报告保存在命令执行目录，文件名带时间戳。图返回 `running_summary`；保存文件由上面的运行代码完成，并非 `graph.invoke()` 自动写文件。

#### 5. 当前参数与验证边界

| 配置或现象 | 当前实现中的含义 |
|---|---|
| `MAX_WEB_RESEARCH_LOOPS=0` | 首跑会先检索一次，再反思并判断是否继续；不是零次搜索。当前路由使用 `<=`，对非负整数 N，正常完整执行时总检索次数为 N+1。 |
| `FETCH_FULL_PAGE=false` | 只使用搜索摘要。即使来源指向 PDF，也不表示已经解析了 PDF 全文。代码类默认值为 `true`，本仓库首跑模板显式覆盖为 `false`。 |
| `SEARCH_API=duckduckgo` | 仍然选 DuckDuckGo 后端；不要改为 `ddgs`，后者是软件包名。 |
| `USE_TOOL_CALLING=false` | 首跑采用 JSON 输出路径。本次没有验证思考模式或多轮工具调用。 |
| 终端中的 `result: ...` | 查询/反思步骤当前打印的模型响应，不是报错；其中可见用量不包含未打印的总结步骤。 |
| 来源列表非空 | 表示程序保存了实际检索来源，不代表正文每个结论均已被证据支持。 |

遇到 `SEARCH_REQUEST_FAILED` 或 `SEARCH_NO_RESULTS` 时，先排查搜索，不要盲目更换 DeepSeek Key。`401`、`402`、`429` 等 API 状态请对照 [DeepSeek 错误码文档](https://api-docs.deepseek.com/zh-cn/quick_start/error_codes)。

### 其他模型与可选界面

下文保留上游的 Ollama、LMStudio 和 Studio 使用说明，作为本地模型及界面运行的可选路径。**仅使用上面的 DeepSeek 命令行方式时，不必执行这些安装步骤。**这些路径未包含在 2026-10-09 的云端首跑验证中。

### 使用 Ollama 选择本地模型

1. 从[下载页面](https://ollama.com/download)下载 Mac 版 Ollama 应用。

2. 从 [Ollama](https://ollama.com/search) 拉取一个本地大语言模型。例如，可以使用[这个模型](https://ollama.com/library/deepseek-r1:8b)：
```shell
ollama pull deepseek-r1:8b
```

3. 根据需要，在 `.env` 文件中更新以下 Ollama 配置。

* 显式设置的值会覆盖 `configuration.py` 中 `Configuration` 类的默认值。
```shell
LLM_PROVIDER=ollama
OLLAMA_BASE_URL="http://localhost:11434" # Ollama 服务地址，默认值为 http://localhost:11434
LOCAL_LLM=model # 使用的模型名称；未设置时默认为 llama3.2
```

### 使用 LMStudio 选择本地模型

1. 从[官方网站](https://lmstudio.ai/)下载并安装 LMStudio。

2. 在 LMStudio 中：
   - 下载并加载你选择的模型，例如 `qwen_qwq-32b`。
   - 打开“Local Server”（本地服务器）选项卡。
   - 启动提供 OpenAI 兼容 API 的服务器。
   - 记下服务器地址，默认值为 `http://localhost:1234/v1`。

3. 根据需要，在 `.env` 文件中更新以下 LMStudio 配置。

* 显式设置的值会覆盖 `configuration.py` 中 `Configuration` 类的默认值。
```shell
LLM_PROVIDER=lmstudio
LOCAL_LLM=qwen_qwq-32b  # 请使用 LMStudio 中显示的完整模型名称
LMSTUDIO_BASE_URL=http://localhost:1234/v1
```

### 选择搜索工具

默认使用 [DuckDuckGo](https://duckduckgo.com/) 进行网页搜索，无需 API Key。也可以使用 [SearXNG](https://docs.searxng.org/)、[Tavily](https://tavily.com/) 或 [Perplexity](https://www.perplexity.ai/hub/blog/introducing-the-sonar-pro-api)，并在环境变量文件中填写相应服务需要的 API Key。根据需要，在 `.env` 文件中更新以下搜索配置；显式设置的值会覆盖 `configuration.py` 中 `Configuration` 类的默认值。
```shell
SEARCH_API=xxx # 使用的搜索接口，例如默认的 duckduckgo
TAVILY_API_KEY=xxx # 使用的 Tavily API Key
PERPLEXITY_API_KEY=xxx # 使用的 Perplexity API Key
MAX_WEB_RESEARCH_LOOPS=xxx # 网页研究的最大循环次数，默认为 3
FETCH_FULL_PAGE=xxx # 是否抓取网页全文；代码默认 true，首跑 .env 模板设置 false
```

### 通过 LangGraph Studio 运行

#### Mac

1. 创建虚拟环境（推荐）：
```bash
python -m venv .venv
source .venv/bin/activate
```

2. 启动 LangGraph 服务器：

```bash
# 安装 uv 包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev
```

#### Windows

1. 创建虚拟环境（推荐）：

* 安装 `Python 3.11`，并在安装时将其添加到 PATH。
* 重新打开终端，确认 Python 可用，然后创建并激活虚拟环境：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. 启动 LangGraph 服务器：

```powershell
# 安装依赖
pip install -e .
pip install -U "langgraph-cli[inmem]"

# 启动 LangGraph 服务器
langgraph dev
```

### 使用 LangGraph Studio 界面

启动 LangGraph 服务器后，终端应显示以下输出，Studio 会在浏览器中打开：
> Ready!

> API: http://127.0.0.1:2024

> Docs: http://127.0.0.1:2024/docs

> LangGraph Studio Web UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

通过上面的地址打开 LangGraph Studio 网页界面。在 `configuration` 选项卡中，可以直接调整助手的配置。配置值的优先级如下：

```text
1. 环境变量（优先级最高）
2. LangGraph 界面配置
3. Configuration 类中的默认值（优先级最低）
```

<img width="1621" alt="配置界面截图：2025-01-24 22:08:31" src="https://github.com/user-attachments/assets/7cfd0e04-28fd-4cfa-aee5-9a556d74ab21" />

输入研究主题后，就可以在界面中查看助手的执行过程。

<img width="1621" alt="研究流程截图：2025-01-24 22:08:22" src="https://github.com/user-attachments/assets/4de6bd89-4f3b-424c-a9cb-70ebd3d45c5f" />

### 模型兼容性说明

选择本地大语言模型时，请注意：部分步骤需要结构化的 JSON 输出。有些模型难以满足这一要求，助手会通过回退机制处理。例如，[DeepSeek R1（7B）](https://ollama.com/library/deepseek-llm:7b) 和 [DeepSeek R1（1.5B）](https://ollama.com/library/deepseek-r1:1.5b) 可能难以生成所需的 JSON，遇到这种情况时会使用回退机制。

### 浏览器兼容性说明

访问 LangGraph Studio 界面时：
- 推荐使用 Firefox，以获得更好的使用体验。
- Safari 用户可能会遇到由 HTTPS/HTTP 混合内容引起的安全提示。
- 遇到问题时，可以尝试：
  1. 使用 Firefox 或其他浏览器。
  2. 关闭广告拦截扩展。
  3. 查看浏览器控制台中的具体错误信息。

## 工作原理

Local Deep Researcher 受到 [IterDRAG](https://arxiv.org/html/2410.04343v1#:~:text=To%20tackle%20this%20issue%2C%20we,used%20to%20generate%20intermediate%20answers.) 的启发。该方法会将查询拆分为子查询，分别检索文档、回答子问题，并在已有回答的基础上继续检索后续子问题所需的资料。本项目采用类似流程：
- 根据用户提供的主题，通过所配置的 DeepSeek API 或 Ollama／LMStudio 本地模型生成网页搜索查询。
- 使用搜索引擎或搜索工具查找相关来源。
- 使用大语言模型总结搜索结果中与研究主题相关的信息。
- 让模型反思当前总结，识别缺失或尚待澄清的信息。
- 为这些问题生成新的搜索查询。
- 重复上述过程，利用新检索到的信息逐步更新总结。
- 按配置的迭代次数运行，具体设置见 `configuration` 选项卡。

## 输出结果

图返回包含 Markdown 总结的 `running_summary` 字段，并在末尾附加收集到的来源；需要像上面的 API 示例那样显式保存，才会生成文件。研究过程中收集到的来源也会保存在图状态中，可以通过 LangGraph Studio 查看：

![来源状态截图：2024-12-05 16:08:59](https://github.com/user-attachments/assets/e8ac1c0b-9acb-4a75-8c15-4e677e92f6cb)

最终总结也会保存在图状态中：

![最终总结截图：2024-12-05 16:10:11](https://github.com/user-attachments/assets/f6d997d5-9de5-495f-8556-7d3891f6bc96)

## 部署方式

可以通过[多种方式](https://langchain-ai.github.io/langgraph/concepts/#deployment-options)部署该图。有关 LangGraph 部署方案的详细教程，请参考 LangChain Academy 的[模块 6](https://github.com/langchain-ai/langchain-academy/tree/main/module-6)。

## TypeScript 实现

本项目的 TypeScript 移植版本可在以下仓库获取，该版本不包含 Perplexity 搜索：
https://github.com/PacoVK/ollama-deep-researcher-ts

## 通过 Docker 容器运行

项目提供的 `Dockerfile` 仅启动以 local-deep-researcher 为服务的 LangChain Studio，不包含 Ollama 服务。你需要单独运行 Ollama，并设置 `OLLAMA_BASE_URL` 环境变量。也可以通过 `LOCAL_LLM` 环境变量指定要使用的 Ollama 模型。

克隆仓库后，构建镜像：
```shell
$ docker build -t local-deep-researcher .
```

运行容器：

> 排版说明：下面仅清除了原命令中续行反斜杠后的多余空格，命令参数保持不变。

```shell
$ docker run --rm -it -p 2024:2024 \
  -e SEARCH_API="tavily" \
  -e TAVILY_API_KEY="tvly-***YOUR_KEY_HERE***" \
  -e LLM_PROVIDER=ollama \
  -e OLLAMA_BASE_URL="http://host.docker.internal:11434/" \
  -e LOCAL_LLM="llama3.2" \
  local-deep-researcher
```

注意：日志中会出现类似下面的信息，以下保留程序输出的原文：
```text
2025-02-10T13:45:04.784915Z [info     ] 🎨 Opening Studio in your browser... [browser_opener] api_variant=local_dev message=🎨 Opening Studio in your browser...
URL: https://smith.langchain.com/studio/?baseUrl=http://0.0.0.0:2024
```

但是，容器不会自动打开宿主机的浏览器。

请在浏览器中访问已使用正确 `baseUrl` IP 地址的链接：[`https://smith.langchain.com/studio/thread?baseUrl=http://127.0.0.1:2024`](https://smith.langchain.com/studio/thread?baseUrl=http://127.0.0.1:2024)。
