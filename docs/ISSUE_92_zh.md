# Issue #92：摘要非空检查与项目内回归测试

关联上游问题：<https://github.com/langchain-ai/local-deep-researcher/issues/92>。
本次开发基点为本仓库 `9a64465df27437dd203feacc2466a4ac56519c85`。

## 修复范围

`summarize_sources()` 在按配置清理 `<think>...</think>` 后，检查剩余文本是否仅为空白。为空时抛出带 `SUMMARY_EMPTY:` 前缀的 `RuntimeError`，不返回成功的状态更新，不进入后续反思和报告汇总。

```python
if not running_summary.strip():
    raise RuntimeError(
        "SUMMARY_EMPTY: the model returned no summary text. "
        "Check its context window and output settings."
    )
```

`.strip()` 仅用于判断，不修改有效正文及其 Markdown 排版。关闭 `strip_thinking_tokens` 时仍保持原有配置语义：纯标签文本本身非空，不在本次修复中擅自删除；真正的空字符串和空白字符串仍被拒绝。

不新增自动重试，不用旧摘要冒充本次生成成功，不更改 DeepSeek/Ollama/LMStudio 客户端参数、搜索后端或研究轮数边界。此修复不诊断模型返回空内容的根因；上下文窗口、输出限制与真实模型行为仍需分别排查。不新增跨进程恢复能力。

## 与上一版隔离验证的区别

测试直接导入 `ollama_deep_researcher.graph`，调用实际的 `summarize_sources()`、`get_llm()`、`Configuration`、消息类型、状态类型和标签清理函数，不再复制被测函数到实验脚本。

仅替换外部 I/O：三个模型客户端构造器返回受控的 mock，搜索返回固定资料。图集成测试运行项目导出的 `graph`；检查点测试使用原项目 `builder` 加真实 `InMemorySaver` 编译，不重写图结构。

测试使用标准库 `unittest`，没有新增测试依赖，也不改变 `pyproject.toml` 或 `uv.lock`。

## 覆盖内容

共 14 个测试方法，参数组合通过 `subTest` 表达，不能把子用例失败次数当作独立 Bug 数量。

| 层次 | 检查内容 |
|---|---|
| 真实函数 | 空字符串、全空白、清理后只剩空白的 thinking-only 响应被拒绝 |
| 真实函数 | 英文、中文 Markdown、thinking 后有正文、有效正文首尾空白保持预期 |
| 配置 | 三个模型提供商分支；初次总结和已有总结；开启/关闭标签清理 |
| 状态 | 失败时没有有效状态更新，也不原地修改传入状态 |
| 模型调用 | 总结保持普通文本模式；一次调用；模型原有异常原样传播 |
| 图流程 | 首次空摘要后不执行反思/最终汇总；正常摘要仍产生正文和实际格式化来源 |
| 检查点 | 第一轮正常、第二轮为空时，中止本次运行，之前有效摘要仍在测试使用的内存检查点中 |
| 安全隔离 | 不加载 `.env`；关闭追踪；使用假 Key；网络连接和未替换的模型/搜索调用会导致测试失败 |

原先的 28 个组合（7 种文本 × 2 种旧状态 × 2 个本地后端）包含在新的真实函数测试中，并扩展了 DeepSeek 分支和图流程断言。测试替身不代表真实服务兼容性认证。

## 本地运行（Windows PowerShell / Python 3.11）

先确认已经进入包含本次修复的分支。已有 `.env` 不需要改动，不要上传真实 Key。

```powershell
uv sync --locked --python 3.11
uv run --locked python -m unittest discover -s tests -p test_summary_validation.py -v -b
```

预期最终显示 `Ran 14 tests` 和 `OK`。这是预期结果，具体运行是否通过应以本机日志或 GitHub Actions 结果为准。

## 自动回归与负对照

`.github/workflows/issue92-regression.yml` 配置 Ubuntu / Windows 两个 Python 3.11 任务。依赖安装需要联网，测试阶段不需要模型服务、搜索服务或密钥。

每个任务先临时移除这六行保护逻辑，执行同一套测试，要求得到 42 个“应抛出 RuntimeError 但未抛出”的子用例失败，且没有导入错误或其他异常；随后在 `finally` 中恢复原文件，重新执行测试，要求全部通过。最后检查源码与锁文件未被测试修改。

此负对照用于证明测试确实能发现本次修复针对的问题，不能用任意非零退出码充当复现成功。工作流本身配置完成不等于 CI 已通过，需查看具体运行记录。

## 不包含的结论

- 不保证所有模型都能生成有效摘要。
- 不证明摘要中的事实正确，或引用与陈述逐条对应。
- 不声称空输出一定由上下文窗口过小导致。
- 不修复结构化响应块、多模态内容、残缺/嵌套 thinking 标签及其他解析议题。
- 不改变上游 #117 的研究次数边界语义。
- 尚未提交到上游仓库；本分支与 PR 仅位于用户 fork。
