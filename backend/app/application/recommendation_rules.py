import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from app.schemas.recommendation import BidRecommendation
from app.schemas.risk import RiskCategory, RiskSeverity

logger = logging.getLogger(__name__)


class RecommendationRulesEngine:
    """Evaluates final tender bid recommendation using the exact specified decision rules."""

    def evaluate_recommendation(
        self,
        tender_id: Any,
        metadata: Any,
        boq_summary: Dict[str, Any],
        qualification_result: Dict[str, Any],
        matching_results: List[Dict[str, Any]],
        risk_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Runs decision rules to produce GO/REVIEW/NO_BID and explainable report metrics."""
        
        pros = []
        cons = []
        
        # 1. Resolve Financial Status
        financial_passed = qualification_result.get("qualified", False)
        financial_qualification_info = {
            "qualified": financial_passed,
            "summary_reasoning": qualification_result.get("summary_reasoning", "No qualification details available.")
        }
        if financial_passed:
            pros.append(f"Financial qualification passes: {qualification_result.get('summary_reasoning')}")
        else:
            cons.append(f"Financial qualification fails: {qualification_result.get('summary_reasoning')}")

        # 2. Resolve Best Matching Project & Matching Score
        best_match_project_info = None
        best_matching_score = 0.0
        matching_satisfied = True
        
        # Iterate over all matched eligibility rules to find the absolute best match
        all_eligible_matches = []
        for rule_res in matching_results:
            rule_text = rule_res.get("rule", "")
            matches = rule_res.get("matches", [])
            
            # The first match is the highest scoring one
            best_rule_match = matches[0] if matches else None
            
            if best_rule_match and best_rule_match.get("eligible"):
                score = best_rule_match.get("score", 0.0)
                all_eligible_matches.append((score, best_rule_match))
                pros.append(f"Found eligible project match for '{rule_text}': '{best_rule_match['project']['project_name']}' (Similarity: {score*100:.1f}%)")
            else:
                matching_satisfied = False
                if best_rule_match:
                    reasons = best_rule_match.get("reasons", [])
                    reasons_str = "; ".join(reasons) if reasons else "incompatible project parameters"
                    cons.append(f"Matching project for '{rule_text}' is ineligible: {reasons_str}")
                else:
                    cons.append(f"No matching project found for eligibility rule: '{rule_text}'")

        if all_eligible_matches:
            # Sort by score descending to find absolute highest eligible match
            all_eligible_matches.sort(key=lambda x: x[0], reverse=True)
            best_score, best_match = all_eligible_matches[0]
            best_matching_score = best_score
            best_match_project_info = best_match.get("project")
        
        # 3. Resolve Compliance Risk
        risk_score = risk_result.get("overall_risk_score", 0.0)
        risk_level = risk_result.get("overall_risk_category", RiskCategory.LOW)
        
        # Risk summary description
        risk_detections = [r for r in risk_result.get("risks_detected", []) if r.get("severity") != RiskSeverity.NONE]
        risk_names = [r.get("risk_name") for r in risk_detections]
        if risk_names:
            risk_summary = f"Risk Score is {risk_score:.2f}/10 (Level: {risk_level}). Risks detected: {', '.join(risk_names)}."
        else:
            risk_summary = f"Risk Score is {risk_score:.2f}/10 (Level: {risk_level}). No specific compliance risks detected."

        if risk_level == RiskCategory.HIGH or risk_score > 8.0:
            cons.append(f"High compliance risk detected (Risk Score: {risk_score:.2f})")
        else:
            pros.append(f"Acceptable compliance risk (Risk Score: {risk_score:.2f})")

        # Compile details from individual risks
        for r in risk_detections:
            severity = r.get("severity")
            name = r.get("risk_name", "")
            evidence = r.get("evidence", "")
            if severity == RiskSeverity.HIGH:
                cons.append(f"High risk in {name}: {evidence}")
            elif severity == RiskSeverity.MEDIUM:
                cons.append(f"Medium risk in {name}: {evidence}")

        # Check for uncertainties in Metadata
        has_uncertainties = False
        if not metadata or metadata.completion_period == "UNKNOWN":
            cons.append("Tender completion period is UNKNOWN, introducing timeline uncertainty.")
            has_uncertainties = True
        if not metadata or metadata.emd is None:
            cons.append("EMD value is not parsed/UNKNOWN, introducing cash flow uncertainty.")
            has_uncertainties = True

        # 4. Apply Final Decision Rules
        # Rule 1: If financial qualification fails
        if not financial_passed:
            recommendation = BidRecommendation.NO_BID
            decision_explanation = (
                f"Bidding is not recommended (NO_BID) because the bidder failed to meet "
                f"the financial qualification criteria: {qualification_result.get('summary_reasoning')}"
            )
        # Rule 2: If risk score > 80 (i.e. risk_score > 8.0 on a 10.0 scale)
        elif risk_score > 8.0:
            recommendation = BidRecommendation.REVIEW
            decision_explanation = (
                f"Bidding requires manual review (REVIEW) because the tender compliance risk score "
                f"({risk_score:.2f}) exceeds the acceptable threshold of 8.0 (80%)."
            )
        # Rule 3: If matching score > 85 and qualification passes
        elif best_matching_score > 0.85 and financial_passed:
            recommendation = BidRecommendation.GO
            project_name = best_match_project_info.get("project_name") if best_match_project_info else "UNKNOWN"
            decision_explanation = (
                f"Bidding is highly recommended (GO) because the bidder is financially qualified, "
                f"compliance risks are low, and the past project '{project_name}' provides a strong "
                f"technical match with {best_matching_score*100:.1f}% similarity (> 85%)."
            )
        # Rule 4: Fallback / Explainable reasoning
        else:
            # If we checked matching rules but best match is below 0.85
            if len(matching_results) > 0:
                if best_matching_score >= 0.4:
                    recommendation = BidRecommendation.REVIEW
                    project_name = best_match_project_info.get("project_name") if best_match_project_info else "UNKNOWN"
                    decision_explanation = (
                        f"Bidding is marked as REVIEW because the best matching project '{project_name}' "
                        f"has a similarity score of {best_matching_score*100:.1f}%, which is marginal "
                        f"(between 40% and 85%)."
                    )
                else:
                    recommendation = BidRecommendation.NO_BID
                    decision_explanation = (
                        "Bidding is not recommended (NO_BID) because the bidder does not meet the "
                        "mandatory technical eligibility rules (no past project matched with similarity above 40%)."
                    )
            else:
                # If no matching rules were provided to check against, and financials and risk pass
                recommendation = BidRecommendation.GO
                decision_explanation = (
                    "Bidding is recommended (GO) because the bidder is financially qualified, compliance "
                    "risks are low, and no technical eligibility constraints were specified."
                )

        # 5. Calculate Confidence Score (0.0 to 1.0)
        confidence = 1.0
        if metadata:
            if metadata.completion_period == "UNKNOWN":
                confidence -= 0.1
            if metadata.emd is None:
                confidence -= 0.1
            if metadata.tender_value is None:
                confidence -= 0.1
            
            field_confs = [
                metadata.tender_value_confidence,
                metadata.emd_confidence,
                metadata.completion_period_confidence
            ]
            valid_confs = [c for c in field_confs if c is not None]
            if valid_confs:
                avg_conf = sum(valid_confs) / len(valid_confs)
                confidence = min(confidence, avg_conf)
                
        confidence_score = round(max(0.1, min(1.0, confidence)), 2)

        # 6. Calculate Win Probability (0% to 100%)
        if recommendation == BidRecommendation.NO_BID:
            win_probability = 0.0
        else:
            prob = 70.0
            # Adjust based on project matching similarity
            if best_matching_score > 0.0:
                if best_matching_score > 0.75:
                    prob += 15.0
                elif best_matching_score < 0.55:
                    prob -= 20.0
                else:
                    prob += (best_matching_score - 0.65) * 50.0
            
            # Risk penalty: up to -30%
            prob -= (risk_score * 3.0)
            
            # Turnover capability bonus
            tender_val = Decimal(str(metadata.tender_value)) if metadata and metadata.tender_value else Decimal("0")
            turnovers_list = qualification_result.get("results", [])
            turnover_rule_res = next((r for r in turnovers_list if r.get("rule_name") == "TURNOVER_RULE"), None)
            if turnover_rule_res and turnover_rule_res.get("passed") and tender_val > 0:
                actual_avg_turnover = Decimal(str(turnover_rule_res.get("actual_value", "0")))
                if actual_avg_turnover > (Decimal("3") * tender_val):
                    prob += 10.0
                    pros.append("Capability Bonus: Average annual turnover is over 3x the tender value, indicating high project capacity buffer.")

            # Net worth bonus
            nw_rule_res = next((r for r in turnovers_list if r.get("rule_name") == "NET_WORTH_PERCENT_RULE" or r.get("rule_name") == "NET_WORTH_RULE"), None)
            if nw_rule_res and nw_rule_res.get("passed") and tender_val > 0:
                actual_nw = Decimal(str(nw_rule_res.get("actual_value", "0")))
                if actual_nw > (Decimal("0.3") * tender_val):
                    prob += 5.0
                    pros.append("Capability Bonus: Net worth is over 30% of tender value, indicating strong balance sheet backup.")

            win_probability = round(max(10.0, min(95.0, prob)), 2)

        # 7. Generate Checklist of Required Documents
        required_docs = ["Tender Document / Bid Form (signed & stamped)", "Company Registration / PAN Card"]
        
        # Financial documents
        for r in qualification_result.get("results", []):
            rule_name = r.get("rule_name", "")
            if "TURNOVER" in rule_name:
                required_docs.append("Turnover Certificate signed by Chartered Accountant")
            if "NET_WORTH" in rule_name:
                required_docs.append("Net Worth Certificate from statutory auditor")
                required_docs.append("Audited Balance Sheets for the last 3 financial years")

        # EMD documents
        if metadata and metadata.emd and metadata.emd > 0:
            required_docs.append("EMD Bank Guarantee or Demand Draft")
        else:
            required_docs.append("EMD Exemption Certificate (MSME / NSIC registration, if applicable)")

        # Performance guarantee PBG
        pg_risk = next((r for r in risk_result.get("risks_detected", []) if r.get("risk_name") == "PERFORMANCE_GUARANTEE"), None)
        if pg_risk and pg_risk.get("severity") != RiskSeverity.NONE:
            required_docs.append("Performance Bank Guarantee compliance agreement")

        # OEM documents
        oem_risk = next((r for r in risk_result.get("risks_detected", []) if r.get("risk_name") == "OEM_DEPENDENCY"), None)
        if oem_risk and oem_risk.get("severity") != RiskSeverity.NONE:
            required_docs.append("Manufacturer's Authorization Form (MAF) from OEM partners")

        # Technical matching documents
        for rule_res in matching_results:
            matches = rule_res.get("matches", [])
            best_rule_match = matches[0] if matches else None
            if best_rule_match and best_rule_match.get("eligible"):
                proj_name = best_rule_match.get("project", {}).get("project_name", "UNKNOWN")
                required_docs.append(f"LOA / Work Order for '{proj_name}'")
                required_docs.append(f"Completion Certificate for '{proj_name}'")

        # Deduplicate while preserving order
        seen = set()
        deduped_docs = []
        for doc in required_docs:
            if doc not in seen:
                seen.add(doc)
                deduped_docs.append(doc)

        key_reasons = pros + cons

        return {
            "recommendation": recommendation,
            "confidence_score": confidence_score,
            "win_probability": win_probability,
            "financial_qualification": financial_qualification_info,
            "best_matching_project": best_match_project_info,
            "risk_level": risk_level,
            "risk_summary": risk_summary,
            "required_documents": deduped_docs,
            "key_reasons": key_reasons,
            "decision_explanation": decision_explanation
        }
