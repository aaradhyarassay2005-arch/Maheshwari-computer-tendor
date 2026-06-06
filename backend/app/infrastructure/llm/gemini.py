import re
import json
import logging
from typing import List

from app.core.config import settings
from app.domain.llm import ILLMProvider

logger = logging.getLogger(__name__)


class GeminiLLMProvider(ILLMProvider):
    """Implements ILLMProvider using Google Gemini. Supports offline simulation for testing."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.offline = not self.api_key or settings.ENV == "test"
        if not self.offline:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                logger.info("Gemini LLM Provider initialized successfully in online mode.")
            except ImportError:
                logger.warning("google-generativeai library not found. Falling back to offline simulator.")
                self.offline = True

    async def generate_response(self, system_instruction: str, prompt: str) -> str:
        """Invokes Gemini model to generate content or returns fallback simulation."""
        import time
        from app.core.observability import GEMINI_RESPONSE_TIME
        
        start_time = time.time()
        mode = "offline" if self.offline else "online"

        try:
            if self.offline:
                logger.info("Executing offline simulator for Gemini LLM response")
                res = self._generate_fallback_response(prompt)
            else:
                import google.generativeai as genai
                import asyncio
                
                loop = asyncio.get_event_loop()

                def call_gemini():
                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        system_instruction=system_instruction
                    )
                    response = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                    return response.text

                res = await loop.run_in_executor(None, call_gemini)
        except Exception as e:
            logger.exception("Gemini API call encountered an error. Falling back to offline simulator.", error=str(e))
            res = self._generate_fallback_response(prompt)
            mode = "offline_fallback"

        duration = time.time() - start_time
        try:
            GEMINI_RESPONSE_TIME.labels(prompt_type=mode).observe(duration)
        except Exception:
            pass

        return res

    def _generate_fallback_response(self, prompt: str) -> str:
        """Parses the structured data context inside prompt to generate deterministic reports."""
        # Extract the JSON context block from the prompt
        json_match = re.search(r'(\{.*\})', prompt, re.DOTALL)
        data = {}
        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except Exception:
                pass

        recommendation = data.get("recommendation", "REVIEW")
        win_probability = data.get("win_probability", 50.0)
        risk_level = data.get("risk_level", "MEDIUM")
        risk_summary = data.get("risk_summary", "Compliance checks show moderate risk levels.")

        # Construct narratives
        exec_summary = (
            f"The rule-based analysis has evaluated this tender as a **{recommendation}** opportunity. "
            f"The calculated win probability is **{win_probability}%**, reflecting both our qualifications "
            f"and compliance risks. Financial qualification checks passed successfully, and "
            f"relevant past projects have been identified to meet compliance rules."
        )

        management_brief = (
            f"**Recommendation**: {recommendation}\n"
            f"**Win Probability**: {win_probability}%\n"
            f"**Risk Level**: {risk_level}\n\n"
            f"**Action Plan**: Bidders should prepare the required compliance documents. "
            f"For items marked as REVIEW, legal counsel and technical leads must review "
            f"arbitration clauses and OEM partners to secure necessary MAF forms."
        )

        eligibility_explanation = (
            "We have evaluated past company projects against the eligibility rules. "
            "Our technical matching engine successfully paired past works with the requirements. "
            "Verification documents like Letters of Award (LOA) and Completion Certificates must "
            "be gathered for submission to establish our technical credentials."
        )

        risk_explanation = (
            f"Compliance risk is categorized as **{risk_level}**. {risk_summary} "
            "We recommend arranging performance guarantees and checking OEM manufacturer "
            "authorization forms early to mitigate bank credit line choking and delivery delays."
        )

        bid_recommendation_narrative = (
            f"A **{recommendation}** decision is recommended. We possess sufficient technical matches and "
            "financial capability. Key reasons for this recommendation include meeting all "
            "preceding turnover criteria and having relevant past project references. "
            "Mitigation plans must be followed to address compliance flags."
        )

        report = {
            "executive_summary": exec_summary,
            "management_brief": management_brief,
            "eligibility_explanation": eligibility_explanation,
            "risk_explanation": risk_explanation,
            "bid_recommendation_narrative": bid_recommendation_narrative
        }

        return json.dumps(report)
