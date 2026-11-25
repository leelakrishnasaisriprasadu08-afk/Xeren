"""
Tests for Xeren MoS — Autonomous Marketing & Growth Engine.
===========================================================
Validates:
1. Registration of M15 Marketing Specialist in SpecialistRegistry
2. Persona simulation with objection/rebuttal generation
3. Direct response copywriting frameworks (PAS, AIDA)
4. Multi-channel GTM Asset Pack assembly
5. Xeren Flagship Campaign validation
"""

import pytest

from backend.automation_framework.mos.marketing_engine import (
    ConversionFramework,
    MarketingEngine,
)
from backend.automation_framework.mos.specialist_registry import (
    SpecialistID,
    SpecialistRegistry,
)


class TestMarketingEngine:
    """Test suite for Xeren Marketing Engine and Specialist."""

    def test_m15_marketing_specialist_registered(self):
        """Verify M15 Marketing Specialist exists in the MoS registry with growth capabilities."""
        spec = SpecialistRegistry.get(SpecialistID.MARKETING)
        assert spec is not None
        assert spec.id == SpecialistID.MARKETING
        assert "Marketing" in spec.name
        assert "copywriting" in spec.capabilities
        assert "growth" in spec.capabilities
        assert "viral hook" in spec.capabilities

        # Verify discovery by capability
        found = SpecialistRegistry.find_by_capability("copywriting")
        assert any(s.id == SpecialistID.MARKETING for s in found)

    def test_persona_simulation(self):
        """Verify that buyer personas are simulated with realistic objections and rebuttals."""
        engine = MarketingEngine()
        personas = engine.simulate_personas("Xeren", "Local Sovereign AI")

        assert len(personas) == 4
        titles = [p.title for p in personas]
        assert any("CTO" in t for t in titles)
        assert any("CFO" in t for t in titles)
        assert any("Founder" in t for t in titles)
        assert any("Engineer" in t for t in titles)

        for p in personas:
            assert len(p.skeptical_objection) > 10
            assert len(p.killer_rebuttal) > 10
            assert 0.0 <= p.estimated_interest_score <= 1.0

    def test_viral_hooks_generation(self):
        """Verify that viral hooks generate high-CTR contrarian angles."""
        engine = MarketingEngine()
        hooks = engine.generate_viral_hooks("Xeren", "Local autonomous agents")

        assert len(hooks) == 5
        assert any("cloud" in h.lower() for h in hooks)
        assert any("Xeren" in h for h in hooks)

    def test_gtm_pack_assembly_pas_framework(self):
        """Verify complete GTM asset pack creation using PAS framework."""
        engine = MarketingEngine()
        pack = engine.generate_gtm_pack(
            product_name="DatabaseOptimizer",
            value_proposition="Automated PostgreSQL index analyzer and slow query killer",
            target_audience="DevOps & Backend Engineers",
            framework=ConversionFramework.PAS,
        )

        assert pack.product_name == "DatabaseOptimizer"
        assert pack.framework == ConversionFramework.PAS
        assert "Problem" in pack.copy_breakdown
        assert "Agitate" in pack.copy_breakdown
        assert "Solve" in pack.copy_breakdown

        # Landing page hero check
        hero = pack.landing_page_hero
        assert "headline" in hero
        assert "cta_primary" in hero
        assert "proof_metric" in hero

        # Cold email sequence check (3 steps)
        assert len(pack.cold_email_sequence) == 3
        for email in pack.cold_email_sequence:
            assert "subject" in email
            assert "body" in email

        # Social launch thread check
        assert len(pack.social_launch_thread) >= 4

        # Short video script check
        assert len(pack.short_video_script_30s) == 4

    def test_xeren_flagship_campaign(self):
        """Verify built-in flagship launch campaign for Xeren itself."""
        engine = MarketingEngine()
        campaign = engine.generate_xeren_flagship_campaign()

        assert campaign.product_name == "Xeren"
        assert "Sovereign" in campaign.value_proposition
        assert len(campaign.viral_hooks) == 5
        assert len(campaign.cold_email_sequence) == 3

        # Verify exportable dictionary representation
        d = campaign.to_dict()
        assert d["product_name"] == "Xeren"
        assert d["framework"] == "PAS"
        assert "temperature_profile" in d
        assert d["temperature_profile"]["creative_hooks"] >= 1.0
