import json
import structlog
from decimal import Decimal
from typing import List, Dict, Any
from pydantic import UUID4

from app.domain.llm import ILLMProvider
from app.application.recommendation_service import TenderRecommendationService

logger = structlog.get_logger("app.analyst")


class AITenderAnalystService:
    """Orchestrates rule-based bid assessment results and uses LLM to generate narrative explanations."""

    def __init__(
        self,
        recommendation_service: TenderRecommendationService,
        llm_provider: ILLMProvider,
    ):
        self.recommendation_service = recommendation_service
        self.llm_provider = llm_provider

    async def generate_analyst_report(
        self,
        tender_id: UUID4,
        annual_turnovers: List[Decimal],
        net_worth: Decimal,
        eligibility_rules: List[str]
    ) -> Dict[str, Any]:
        """Runs the rule-based evaluation, packages the results for the LLM, and retrieves/validates AI explanations."""
        logger.info("Generating AI analyst report", tender_id=str(tender_id))

        # 1. Run the deterministic rule-based evaluation first
        rec_report = await self.recommendation_service.get_recommendation(
            tender_id=tender_id,
            annual_turnovers=annual_turnovers,
            net_worth=net_worth,
            eligibility_rules=eligibility_rules
        )

        # 2. Package rule-based results into a prompt context block
        context = {
            "recommendation": str(rec_report["recommendation"].value),
            "win_probability": float(rec_report["win_probability"]),
            "risk_level": str(rec_report["risk_level"]),
            "risk_summary": str(rec_report["risk_summary"]),
            "key_reasons": rec_report["key_reasons"],
            "required_documents": rec_report["required_documents"]
        }

        system_instruction = (
            "You are an expert AI Tender Analyst specialized in railways and government bidding.\n"
            "Your sole responsibility is to explain and write narratives for pre-calculated, "
            "rule-based evaluation results.\n"
            "IMPORTANT: You MUST NOT make decisions or change the final recommendation (GO, REVIEW, or NO_BID) "
            "or modify calculated win probability scores. You must explain them exactly as they are provided.\n"
            "Provide all generated text using standard GitHub-style markdown inside JSON fields.\n"
            "Return your response ONLY as a valid JSON object matching the following structure:\n"
            "{\n"
            "  \"executive_summary\": \"string\",\n"
            "  \"management_brief\": \"string\",\n"
            "  \"eligibility_explanation\": \"string\",\n"
            "  \"risk_explanation\": \"string\",\n"
            "  \"bid_recommendation_narrative\": \"string\"\n"
            "}"
        )

        prompt = (
            f"Please write an analyst explanation for the following rule-based tender evaluation output:\n"
            f"```json\n"
            f"{json.dumps(context, indent=2)}\n"
            f"```\n"
            f"Follow the system instructions precisely."
        )

        # 3. Request LLM response
        logger.info("Invoking LLM provider for report generation", tender_id=str(tender_id))
        response_text = await self.llm_provider.generate_response(system_instruction, prompt)

        # 4. Parse & Validate LLM output (Guardrail)
        parsed = None
        try:
            # Strip markdown json code blocks if returned
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned.strip())
        except Exception as e:
            logger.error("Failed to parse LLM response as JSON. Falling back to offline simulator.", error=str(e), tender_id=str(tender_id))

        # Check if parsing failed or was missing required keys, run simulation fallback
        required_keys = ["executive_summary", "management_brief", "eligibility_explanation", "risk_explanation", "bid_recommendation_narrative"]
        if not parsed or not all(k in parsed for k in required_keys):
            # Check if llm_provider has fallback helper
            if hasattr(self.llm_provider, "_generate_fallback_response"):
                fallback_json = self.llm_provider._generate_fallback_response(prompt)
                parsed = json.loads(fallback_json)
            else:
                parsed = {}

        # 5. Assemble final response, guaranteeing that decisions remain strictly rule-based
        return {
            "tender_id": tender_id,
            "recommendation": rec_report["recommendation"],
            "win_probability": rec_report["win_probability"],
            "executive_summary": parsed.get("executive_summary", "No executive summary available."),
            "management_brief": parsed.get("management_brief", "No management brief available."),
            "eligibility_explanation": parsed.get("eligibility_explanation", "No eligibility explanation available."),
            "risk_explanation": parsed.get("risk_explanation", "No risk explanation available."),
            "bid_recommendation_narrative": parsed.get("bid_recommendation_narrative", "No recommendation narrative available.")
        }
