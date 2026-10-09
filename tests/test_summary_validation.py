"""Regressions for upstream issue #92 using real project functions and graph.

Model constructors and search I/O are mocked; configuration, messages, state,
summary processing, graph routing and checkpoint behavior are not reimplemented.
Run with: uv run --locked python -m unittest discover -s tests -v
"""

import importlib
import io
import os
import socket
import unittest
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from itertools import product
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver

from ollama_deep_researcher.state import SummaryState

research = importlib.import_module("ollama_deep_researcher.graph")

PROVIDERS = {
    "ollama": "ChatOllama",
    "lmstudio": "ChatLMStudio",
    "deepseek": "ChatOpenAI",
}
ERROR_PATTERN = r"^SUMMARY_EMPTY:"
EXISTING_SUMMARY = "Previously validated summary."
QUERY_REPLY = AIMessage(content='{"query": "fixture query", "rationale": "test"}')
REFLECTION_REPLY = AIMessage(
    content='{"follow_up_query": "next fixture query", "knowledge_gap": "test"}'
)
SEARCH_RESPONSE = {
    "results": [
        {
            "title": "Fixture source",
            "url": "https://example.test/source",
            "content": "Evidence supplied by a deterministic test fixture.",
            "raw_content": None,
        }
    ]
}


def make_config(provider, *, strip=True, loops=0):
    """Use the project's real Configuration parser, not a configuration mock."""
    return {
        "configurable": {
            "llm_provider": provider,
            "local_llm": "unit-test-model",
            "search_api": "duckduckgo",
            "fetch_full_page": False,
            "strip_thinking_tokens": strip,
            "use_tool_calling": False,
            "max_web_research_loops": loops,
            "thread_id": "issue92-test-thread",
        }
    }


class OfflineTestCase(unittest.TestCase):
    """Isolate environment variables and forbid accidental external requests."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(
            patch.dict(
                os.environ,
                {
                    "LANGSMITH_TRACING": "false",
                    "LANGCHAIN_TRACING_V2": "false",
                    "DEEPSEEK_API_KEY": "unit-test-placeholder-not-a-real-key",
                },
                clear=True,
            )
        )
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.getaddrinfo"):
            self.stack.enter_context(
                patch(target, side_effect=AssertionError("Network access is forbidden in tests"))
            )
        for name in ("ChatOllama", "ChatLMStudio", "ChatOpenAI"):
            self.stack.enter_context(
                patch.object(research, name, side_effect=AssertionError("Unmocked model I/O"))
            )
        for name in ("duckduckgo_search", "tavily_search", "perplexity_search", "searxng_search"):
            self.stack.enter_context(
                patch.object(research, name, side_effect=AssertionError("Unmocked search I/O"))
            )


class SummaryValidationTests(OfflineTestCase):
    """Exercise summarize_sources across three provider branches and two states."""

    def check_response(self, content, *, strip=True, expected=None, rejected=False):
        for provider, previous in product(PROVIDERS, (None, EXISTING_SUMMARY)):
            with self.subTest(provider=provider, previous_summary=previous is not None):
                state = SummaryState(
                    research_topic="Fixture research topic",
                    running_summary=previous,
                    web_research_results=["Fixture search evidence"],
                    sources_gathered=["Fixture source"],
                    research_loop_count=1,
                )
                before = deepcopy(state)
                model = Mock()
                model.invoke.return_value = AIMessage(content=content)
                with patch.object(research, PROVIDERS[provider], return_value=model) as factory:
                    if rejected:
                        with self.assertRaisesRegex(RuntimeError, ERROR_PATTERN):
                            research.summarize_sources(state, make_config(provider, strip=strip))
                    else:
                        update = research.summarize_sources(state, make_config(provider, strip=strip))
                        self.assertEqual(update, {"running_summary": expected})
                    factory.assert_called_once()
                    self.assertEqual(factory.call_args.kwargs["model"], "unit-test-model")
                    self.assertNotIn("format", factory.call_args.kwargs)

                model.invoke.assert_called_once()
                model.bind.assert_not_called()  # Summaries must remain normal text, not JSON.
                messages = model.invoke.call_args.args[0]
                self.assertIsInstance(messages[0], SystemMessage)
                self.assertIsInstance(messages[1], HumanMessage)
                self.assertIn("Fixture search evidence", messages[1].content)
                if previous is not None:
                    self.assertIn(previous, messages[1].content)
                self.assertEqual(state, before)  # No direct mutation, including error paths.

    def test_empty_response_is_rejected(self):
        self.check_response("", rejected=True)

    def test_whitespace_response_is_rejected(self):
        self.check_response(" \t\r\n\u3000", rejected=True)

    def test_thinking_only_response_is_rejected_after_stripping(self):
        self.check_response("<think>Internal processing only.</think>", rejected=True)

    def test_plain_text_is_preserved(self):
        self.check_response("Valid summary.", expected="Valid summary.")

    def test_chinese_markdown_is_preserved(self):
        text = "## 总结\n\n测试正文。[^1]\n"
        self.check_response(text, expected=text)

    def test_thinking_prefix_is_removed_without_losing_summary(self):
        self.check_response("<think>Processing.</think>Valid summary.", expected="Valid summary.")

    def test_disabled_stripping_preserves_nonempty_thinking_text(self):
        text = "<think>Processing.</think>"
        self.check_response(text, strip=False, expected=text)

    def test_valid_summary_whitespace_is_not_trimmed(self):
        text = "  Valid summary.\n\n"
        self.check_response(text, expected=text)

    def test_empty_response_is_also_rejected_when_stripping_disabled(self):
        for content in ("", " \t\n"):
            with self.subTest(content=repr(content)):
                self.check_response(content, strip=False, rejected=True)

    def test_provider_error_is_not_retried_or_relabelled(self):
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                state = SummaryState(
                    research_topic="Fixture topic",
                    running_summary=EXISTING_SUMMARY,
                    web_research_results=["Fixture evidence"],
                )
                before = deepcopy(state)
                error = TimeoutError("Simulated model timeout")
                model = Mock()
                model.invoke.side_effect = error
                with patch.object(research, PROVIDERS[provider], return_value=model):
                    with self.assertRaises(TimeoutError) as caught:
                        research.summarize_sources(state, make_config(provider))
                self.assertIs(caught.exception, error)
                model.invoke.assert_called_once()
                self.assertEqual(state, before)

    def test_accidental_network_access_is_blocked(self):
        with self.assertRaisesRegex(AssertionError, "Network access is forbidden"):
            socket.getaddrinfo("example.test", 443)


class SummaryGraphTests(OfflineTestCase):
    """Run real graph nodes and routing with deterministic external I/O."""

    def model_context(self, provider, replies):
        stack = ExitStack()
        self.addCleanup(stack.close)
        model = Mock()
        model.invoke.side_effect = replies
        model.bind.return_value = model
        stack.enter_context(patch.object(research, PROVIDERS[provider], return_value=model))
        search = stack.enter_context(
            patch.object(research, "duckduckgo_search", return_value=deepcopy(SEARCH_RESPONSE))
        )
        stack.enter_context(redirect_stdout(io.StringIO()))
        return stack, model, search

    def test_empty_first_summary_stops_before_reflection_and_finalization(self):
        for provider, content in product(PROVIDERS, ("", " \n\t", "<think>Only processing.</think>")):
            with self.subTest(provider=provider, content=repr(content)):
                replies = [QUERY_REPLY, AIMessage(content=content), REFLECTION_REPLY]
                stack, model, search = self.model_context(provider, replies)
                with stack:
                    events = []
                    with self.assertRaisesRegex(RuntimeError, ERROR_PATTERN):
                        for update in research.graph.stream(
                            {"research_topic": "Fixture topic"},
                            make_config(provider),
                            stream_mode="updates",
                        ):
                            events.extend(update.keys())
                    self.assertEqual(events, ["generate_query", "web_research"])
                    self.assertEqual(model.invoke.call_count, 2)
                    search.assert_called_once()

    def test_empty_later_summary_does_not_overwrite_last_successful_checkpoint(self):
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                # Compile the actual project builder, not a test recreation of the graph.
                graph = research.builder.compile(checkpointer=InMemorySaver())
                config = make_config(provider, loops=1)
                replies = [
                    QUERY_REPLY,
                    AIMessage(content=EXISTING_SUMMARY),
                    REFLECTION_REPLY,
                    AIMessage(content="<think>No answer.</think>"),
                    REFLECTION_REPLY,
                ]
                stack, model, search = self.model_context(provider, replies)
                with stack:
                    events = []
                    with self.assertRaisesRegex(RuntimeError, ERROR_PATTERN):
                        for update in graph.stream(
                            {"research_topic": "Fixture topic"}, config, stream_mode="updates"
                        ):
                            events.extend(update.keys())
                    snapshot = graph.get_state(config)
                    self.assertEqual(snapshot.values["running_summary"], EXISTING_SUMMARY)
                    self.assertEqual(events.count("summarize_sources"), 1)
                    self.assertEqual(events.count("reflect_on_summary"), 1)
                    self.assertNotIn("finalize_summary", events)
                    self.assertEqual(model.invoke.call_count, 4)
                    self.assertEqual(search.call_count, 2)

    def test_valid_summary_reaches_finalizer_with_actual_formatted_sources(self):
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                replies = [QUERY_REPLY, AIMessage(content="Valid summary."), REFLECTION_REPLY]
                stack, model, search = self.model_context(provider, replies)
                with stack:
                    result = research.graph.invoke(
                        {"research_topic": "Fixture topic"}, make_config(provider)
                    )
                    report = result["running_summary"]
                    self.assertIn("Valid summary.", report)
                    self.assertIn("### Sources:", report)
                    self.assertIn("Fixture source", report)
                    self.assertIn("https://example.test/source", report)
                    self.assertEqual(model.invoke.call_count, 3)
                    search.assert_called_once()


if __name__ == "__main__":
    unittest.main()
