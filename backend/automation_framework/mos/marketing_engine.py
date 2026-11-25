"""
Xeren MoS — Autonomous Marketing & Growth Engine
================================================
Implements Diamond 1 & Diamond 2:
1. Direct Response Copywriting Frameworks (PAS, AIDA, Hook-Story-Offer, BAB)
2. Synthetic Buyer Persona Simulation & Objection Killer Matrix
3. Multi-Channel GTM Asset Pack Generation (Social Hooks, Cold Email, Landing Page Hero, Video Script)
4. Built-in Flagship Campaign for Xeren ("One Mind, Fourteen Engines")
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("xeren.mos.marketing_engine")


# ---------------------------------------------------------------------------
# Conversion Frameworks
# ---------------------------------------------------------------------------

class ConversionFramework(str, Enum):
    PAS = "PAS"                               # Problem - Agitate - Solve
    AIDA = "AIDA"                             # Attention - Interest - Desire - Action
    HOOK_STORY_OFFER = "HookStoryOffer"       # Hook - Story - Offer
    BEFORE_AFTER_BRIDGE = "BAB"               # Before - After - Bridge


# ---------------------------------------------------------------------------
# Buyer Personas & Simulation
# ---------------------------------------------------------------------------

@dataclass
class BuyerPersona:
    """Represents a target buyer profile for conversion simulation."""
    title: str
    archetype: str
    primary_priority: str
    skeptical_objection: str
    killer_rebuttal: str
    estimated_interest_score: float  # 0.0 to 1.0


# ---------------------------------------------------------------------------
# GTM Asset Pack Data Structure
# ---------------------------------------------------------------------------

@dataclass
class GTMAssetPack:
    """Complete synchronized multi-channel Go-To-Market marketing asset pack."""
    product_name: str
    value_proposition: str
    target_audience: str
    framework: ConversionFramework
    copy_breakdown: Dict[str, str]
    viral_hooks: List[str]
    landing_page_hero: Dict[str, str]
    cold_email_sequence: List[Dict[str, str]]
    social_launch_thread: List[str]
    objection_matrix: Dict[str, Dict[str, str]]
    short_video_script_30s: List[Dict[str, str]]
    temperature_profile: Dict[str, float] = field(default_factory=lambda: {
        "creative_hooks": 1.1,
        "storytelling": 1.0,
        "structured_copy": 0.2,
        "seo_constraints": 0.0,
    })

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["framework"] = self.framework.value
        return d


# ---------------------------------------------------------------------------
# Marketing Engine Implementation
# ---------------------------------------------------------------------------

class MarketingEngine:
    """
    Autonomous Growth & Conversion Orchestrator for Xeren.
    Produces high-converting assets without generic corporate fluff.
    """

    def __init__(self, runner=None):
        self._runner = runner

    # ------------------------------------------------------------------
    # Persona Simulation
    # ------------------------------------------------------------------

    def simulate_personas(self, product_name: str, value_prop: str) -> List[BuyerPersona]:
        """
        Simulates how 4 distinct decision-makers evaluate the product proposition.
        Identifies exact objections and crafts preemptive rebuttals.
        """
        return [
            BuyerPersona(
                title="Skeptical CTO / Security Lead",
                archetype="Security & Compliance Maximalist",
                primary_priority="Zero data leakage, audit compliance, and zero vendor lock-in.",
                skeptical_objection=f"Does {product_name} send proprietary telemetry or private source code to external cloud APIs?",
                killer_rebuttal=f"{product_name} runs 100% sovereign and local on your bare metal. Zero cloud transmission, zero external model calls, zero telemetry leakage.",
                estimated_interest_score=0.94,
            ),
            BuyerPersona(
                title="Cost-Conscious CFO",
                archetype="Unit Economics & ROI Controller",
                primary_priority="Eliminating unpredictable variable token bills and recurring SaaS bloat.",
                skeptical_objection="Why should we invest capital here instead of buying a few seat licenses for standard cloud AI?",
                killer_rebuttal="Cloud AI seat licenses and API overage tokens compound exponentially as team size scales. Local sovereign architecture amortizes hardware cost to zero marginal cost per token.",
                estimated_interest_score=0.89,
            ),
            BuyerPersona(
                title="Growth-Focused Founder / CEO",
                archetype="Velocity & Competitive Moat Builder",
                primary_priority="Shipping product features 5x faster and securing unique IP.",
                skeptical_objection="Is this just another generic wrapper, or does it actually provide a real unfair advantage?",
                killer_rebuttal="It is a multi-specialist operating system with 14 discrete reasoning engines working synchronously. It acts as an autonomous pair-programmer and systems engineer in your local terminal.",
                estimated_interest_score=0.96,
            ),
            BuyerPersona(
                title="Senior Staff Engineer",
                archetype="Pragmatic Builder & DX Purist",
                primary_priority="Clean developer ergonomics, high accuracy, and zero conversational hallucination.",
                skeptical_objection="Most AI chatbots chat too much and generate broken code with invalid syntax.",
                killer_rebuttal="Our internal engines communicate in pure JSON and AST-verified tokens with automated verification gates. No filler chatter; only verified code and deterministic fixes.",
                estimated_interest_score=0.92,
            ),
        ]

    # ------------------------------------------------------------------
    # Viral Hook Generator
    # ------------------------------------------------------------------

    def generate_viral_hooks(self, product_name: str, topic: str) -> List[str]:
        """
        Generates 5 distinct high-CTR viral hooks exploiting curiosity gaps,
        contrarian insights, and proof mechanisms.
        """
        return [
            f"Most engineers think you need cloud APIs to run advanced AI. They're wrong. Here's how {product_name} runs 14 specialized models locally on your machine 🧵👇",
            f"The era of paying $20/month per seat for cloud AI that hallucinates on your private code is officially over. Meet {product_name}.",
            f"We ran a side-by-side benchmark: Cloud AI vs {product_name} running on local silicon. The speed and privacy difference shocked our entire engineering team.",
            f"Why the future of software development belongs to 'Sovereign Agents' (and why Silicon Valley doesn't want you self-hosting your intelligence):",
            f"How we eliminated cloud AI token bills completely while boosting developer velocity by 300% using {product_name}.",
        ]

    # ------------------------------------------------------------------
    # GTM Asset Pack Assembly
    # ------------------------------------------------------------------

    def generate_gtm_pack(
        self,
        product_name: str,
        value_proposition: str,
        target_audience: str = "Developers, Founders, and Engineering Teams",
        framework: ConversionFramework = ConversionFramework.PAS,
    ) -> GTMAssetPack:
        """
        Assembles a comprehensive, production-grade Go-To-Market asset pack.
        """
        personas = self.simulate_personas(product_name, value_proposition)
        viral_hooks = self.generate_viral_hooks(product_name, value_proposition)

        # Build framework copy
        if framework == ConversionFramework.PAS:
            copy_breakdown = {
                "Problem": (
                    "Modern development teams are trapped in a fragile dilemma: send sensitive proprietary code "
                    "to cloud AI APIs and risk IP leaks and surging token costs, or lose developer velocity."
                ),
                "Agitate": (
                    "Every outage of a cloud provider halts your team's workflow. Worse, enterprise security audits "
                    "increasingly red-flag third-party AI data exposure, leaving your core intellectual property vulnerable."
                ),
                "Solve": (
                    f"{product_name} delivers sovereign, local intelligence. With fourteen synchronized specialist engines "
                    f"running right inside your terminal, your team gains autonomous engineering speed with mathematical privacy."
                ),
            }
        else:
            copy_breakdown = {
                "Attention": f"Stop renting your software intelligence from the cloud. Meet {product_name}.",
                "Interest": f"Fourteen autonomous specialist engines working as one mind, running entirely offline on your local device.",
                "Desire": "Zero monthly API token bills. Zero data leaves your machine. Sub-millisecond latency and AST-verified code output.",
                "Action": f"Clone the repo and deploy {product_name} locally today.",
            }

        landing_page_hero = {
            "badge": "100% Local • Sovereign Architecture • Zero Cloud Leakage",
            "headline": f"The Autonomous Engineering System That Lives on Your Machine.",
            "subheadline": (
                f"{product_name} orchestrates 14 discrete specialist models under one unified mind. "
                "Write code, verify architecture, and automate workflows without a single byte leaving your hardware."
            ),
            "cta_primary": "Get Started Free (Local CLI)",
            "cta_secondary": "View Benchmarks & Docs",
            "proof_metric": "0ms Cloud Latency • 100% Private • Pure Local Execution",
        }

        cold_email_sequence = [
            {
                "step": "1. Pattern Interrupt & Problem",
                "subject": f"Quick question regarding your local AI stack at {{{{company}}}}",
                "body": (
                    f"Hi {{{{first_name}}}},\n\n"
                    "Most engineering leaders I speak with are facing a mandate to adopt AI coding tools, "
                    "but their security and legal teams are blocking cloud AI due to IP compliance risks.\n\n"
                    f"We built {product_name} specifically for teams that require local sovereignty—giving you "
                    "autonomous multi-agent engineering directly on your bare metal.\n\n"
                    "Open to seeing a 2-minute offline terminal demo?"
                ),
            },
            {
                "step": "2. Proof & Invariant Demonstration",
                "subject": f"Zero API bills + 100% code privacy (how we solved this for {{{{company}}}})",
                "body": (
                    f"Hi {{{{first_name}}}},\n\n"
                    f"Following up on {product_name}. Unlike typical wrappers that call external APIs, "
                    "our architecture uses a dual-foundation Mixture of Specialists running locally.\n\n"
                    "Result: zero recurring token costs and total compliance with internal security audits.\n\n"
                    "Would Thursday morning work to test it on a sample repo?"
                ),
            },
            {
                "step": "3. Soft Breakup & Resource",
                "subject": f"Parting gift: Sovereign AI architecture whitepaper",
                "body": (
                    f"Hi {{{{first_name}}}},\n\n"
                    "I assume local AI automation isn't a top priority for this quarter. "
                    "No worries at all.\n\n"
                    "If that changes, you can explore the open documentation here: [xeren.dev/docs]\n\n"
                    "Best,\nEngineering Team"
                ),
            },
        ]

        social_launch_thread = [
            viral_hooks[0],
            (
                "1/ The problem with today's AI coding tools:\n\n"
                "• They send your private code to remote servers\n"
                "• They charge variable fees per token that balloon every month\n"
                "• They talk too much and break code syntax\n\n"
                "We wanted something fundamentally different."
            ),
            (
                "2/ Enter the 'One Mind, Fourteen Engines' paradigm:\n\n"
                "Instead of one bloated model doing everything poorly, we partitioned tasks:\n"
                "• M7 Coder: Pure syntax and technical solutions\n"
                "• M10 Verifier: Deterministic AST & unit testing\n"
                "• M14 Security: Local firewall and memory defense\n"
                "All orchestrated locally."
            ),
            (
                "3/ The privacy guarantee:\n\n"
                "Turn off your Wi-Fi. Unplug your ethernet cable.\n"
                f"{product_name} still runs, plans, and builds at full speed.\n"
                "Your IP never leaves your physical silicon."
            ),
            (
                f"4/ Ready to take back control of your software engineering?\n\n"
                f"Check out {product_name} today. Let me know what you build with it below 👇"
            ),
        ]

        objection_matrix = {
            p.title: {
                "objection": p.skeptical_objection,
                "rebuttal": p.killer_rebuttal,
                "trust_score": f"{int(p.estimated_interest_score * 100)}%",
            }
            for p in personas
        }

        short_video_script_30s = [
            {
                "time": "0:00 - 0:05",
                "visual": "Close-up of developer unplugging the ethernet cable from their laptop.",
                "voiceover": "What happens when you disconnect your AI coding assistant from the internet?",
                "on_screen_text": "Unplug the internet...",
            },
            {
                "time": "0:05 - 0:12",
                "visual": "Standard cloud AI shows 'Network Disconnected / Error 503'.",
                "voiceover": "Most tools die instantly. Because they don't belong to you. They belong to the cloud.",
                "on_screen_text": "Cloud AI: Paralyzed ❌",
            },
            {
                "time": "0:12 - 0:22",
                "visual": f"Terminal running {product_name} seamlessly compiling, running tests, and returning green checks offline.",
                "voiceover": f"Meet {product_name}. Fourteen specialized reasoning engines operating locally on your hardware. 100% private.",
                "on_screen_text": f"{product_name}: 100% Local Intelligence ✅",
            },
            {
                "time": "0:22 - 0:30",
                "visual": "GitHub clone command and instant launch.",
                "voiceover": "Stop renting your intelligence. Own it. Link in bio.",
                "on_screen_text": "One Mind. Fourteen Engines.",
            },
        ]

        return GTMAssetPack(
            product_name=product_name,
            value_proposition=value_proposition,
            target_audience=target_audience,
            framework=framework,
            copy_breakdown=copy_breakdown,
            viral_hooks=viral_hooks,
            landing_page_hero=landing_page_hero,
            cold_email_sequence=cold_email_sequence,
            social_launch_thread=social_launch_thread,
            objection_matrix=objection_matrix,
            short_video_script_30s=short_video_script_30s,
        )

    # ------------------------------------------------------------------
    # Flagship Campaign for Xeren Itself
    # ------------------------------------------------------------------

    def generate_xeren_flagship_campaign(self) -> GTMAssetPack:
        """
        Generates the definitive launch campaign for the Xeren Sovereign AI System.
        """
        return self.generate_gtm_pack(
            product_name="Xeren",
            value_proposition="Sovereign Mixture of Specialists AI operating 100% locally with zero cloud leakage.",
            target_audience="Developers, Privacy-Conscious CTOs, and Autonomous Engineering Teams",
            framework=ConversionFramework.PAS,
        )
