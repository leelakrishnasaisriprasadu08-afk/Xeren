"""Comprehensive tests for Xeren Intent Routing, Hallucination Recovery Gate, and Web Search Fallback."""

import asyncio
import unittest

from xeren.core.intent import IntentClassifier, IntentResult, RoutingCategory
from xeren.core.hallucination_guard import HallucinationGuard, StructuredAnswer
from xeren.core.runtime import XerenCore
from xeren.plugins.research.tools.search import MockSearchEngine


class TestIntentRouter(unittest.TestCase):
    """Verify 3-tier intent classification and routing."""

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_general_knowledge_routing(self):
        queries = [
            "Explain what causes ocean tides",
            "What is the theory of relativity?",
            "How do black holes form in astrophysics?",
            "Tell me a fun fact about honeybees",
        ]
        for q in queries:
            result = self.classifier.classify(q)
            self.assertEqual(result.category, RoutingCategory.GENERAL_KNOWLEDGE)
            self.assertGreaterEqual(result.confidence, 0.70)

    def test_xeren_project_routing(self):
        queries = [
            "How does Xeren runtime architecture work?",
            "What is the learning rate in Xeren QLoRA curriculum?",
            "Explain Xeren training checkpoint stage1 and stage2",
            "Where is AgentController defined in this repo?",
            "How does the hallucination guard work in Xeren?",
        ]
        for q in queries:
            result = self.classifier.classify(q)
            self.assertEqual(result.category, RoutingCategory.XEREN_PROJECT)
            self.assertEqual(result.plugin, "knowledge")
            self.assertGreaterEqual(result.confidence, 0.85)

    def test_action_request_routing(self):
        queries = [
            ("write a python script to parse a json log file", "coding"),
            ("build a landing page website for a medical clinic", "website"),
            ("analyze sales csv dataset and plot histogram", "data"),
            ("find file invoice.pdf in documents folder", "file"),
            ("check open orders on upwork and send proposal", "automation"),
            ("deep search credibility of quantum computing claims", "research"),
            ("verify claim that water boils at 100 degrees Celsius", "verification"),
        ]
        for q, expected_plugin in queries:
            result = self.classifier.classify(q)
            self.assertEqual(result.category, RoutingCategory.ACTION_REQUEST)
            self.assertEqual(result.plugin, expected_plugin)
            self.assertGreaterEqual(result.confidence, 0.85)

    def test_empty_query_fallback(self):
        result = self.classifier.classify("   ")
        self.assertEqual(result.category, RoutingCategory.GENERAL_KNOWLEDGE)
        self.assertEqual(result.plugin, "conversation")


class TestHallucinationGuard(unittest.TestCase):
    """Verify active hallucination detection, probability scoring, and recovery."""

    def setUp(self):
        self.guard = HallucinationGuard(confidence_threshold=0.75, search_engine=MockSearchEngine())

    def test_confident_answer_passed_without_recovery(self):
        query = "What is the capital of France?"
        answer = "The capital of France is Paris. It is a major European city and global center for art and culture."

        res: StructuredAnswer = self.guard.verify_and_recover(query, answer, RoutingCategory.GENERAL_KNOWLEDGE)
        self.assertEqual(res.verification_status, "VERIFIED")
        self.assertGreaterEqual(res.confidence_score, 0.75)
        self.assertFalse(res.hallucination_detected)
        self.assertFalse(res.recovery_applied)
        self.assertEqual(res.routing_category, RoutingCategory.GENERAL_KNOWLEDGE.value)

    def test_uncertain_answer_triggers_recovery(self):
        query = "When was the fictional gadget XYZ released?"
        answer = "I think maybe perhaps it was released in version 9.9.9 as far as I know."

        res: StructuredAnswer = self.guard.verify_and_recover(query, answer, RoutingCategory.GENERAL_KNOWLEDGE)
        self.assertTrue(res.hallucination_detected)
        self.assertIn(res.verification_status, ["RECOVERED", "UNCERTAIN"])

    def test_confidence_evaluation_scoring(self):
        score1, suspect1, _ = self.guard.evaluate_confidence("What is Python?", "Python is a dynamic programming language.")
        self.assertGreaterEqual(score1, 0.75)
        self.assertFalse(suspect1)

        score2, suspect2, exp2 = self.guard.evaluate_confidence("Who wrote this?", "I am not sure, maybe someone else probably.")
        self.assertLess(score2, 0.70)
        self.assertTrue(suspect2)
        self.assertIn("uncertainty expression", exp2)


class TestXerenCoreAnswerPipeline(unittest.TestCase):
    """Verify XerenCore integration of Intent Router and Hallucination Guard."""

    def setUp(self):
        self.core = XerenCore(search_engine=MockSearchEngine())

    def test_general_knowledge_query(self):
        ans = self.core.answer_query("Explain how the solar system formed.")
        self.assertIsInstance(ans, StructuredAnswer)
        self.assertEqual(ans.routing_category, RoutingCategory.GENERAL_KNOWLEDGE.value)
        self.assertGreater(ans.confidence_score, 0.0)
        self.assertTrue(bool(ans.answer))

    def test_project_query(self):
        ans = self.core.answer_query("How does Xeren runtime architecture work?")
        self.assertIsInstance(ans, StructuredAnswer)
        self.assertEqual(ans.routing_category, RoutingCategory.XEREN_PROJECT.value)
        self.assertGreater(ans.confidence_score, 0.0)

    def test_action_request_query(self):
        ans = self.core.answer_query("Write a python function to compute factorial")
        self.assertIsInstance(ans, StructuredAnswer)
        self.assertEqual(ans.routing_category, RoutingCategory.ACTION_REQUEST.value)
        self.assertGreater(ans.confidence_score, 0.0)

    def test_async_answer_query(self):
        async def run_async():
            ans = await self.core.aanswer_query("What are gravitational waves?")
            self.assertIsInstance(ans, StructuredAnswer)
            self.assertEqual(ans.routing_category, RoutingCategory.GENERAL_KNOWLEDGE.value)
            self.assertGreaterEqual(ans.confidence_score, 0.70)
            dict_repr = ans.to_dict()
            self.assertIn("confidence_score", dict_repr)
            self.assertIn("verification_status", dict_repr)

        asyncio.run(run_async())


if __name__ == "__main__":
    unittest.main()
