import anthropic
import json
import uuid
import structlog
from app.schemas.ai import InvestigationReport, InvestigateResponse
from app.config import get_settings

logger = structlog.get_logger()

SYSTEM_PROMPT = """
You are SentinelGraph's case investigation assistant. You explain fraud/abuse
risk cases to a human analyst using ONLY the structured evidence provided to
you or retrieved via your tools. Rules:
1. Never state a fact that is not present in the case data, evidence records,
   SHAP feature contributions, or graph/network statistics you retrieved.
2. Every item in "key_evidence" must be an evidence_id that exists in the
   case's evidence records — never a paraphrase without an id.
3. You do not make the final decision. Provide a "recommended_action" from
   {MONITOR, ESCALATE, CONFIRMED_ABUSE, FALSE_POSITIVE} but the human decides.
4. Output strict JSON matching the provided schema. No prose outside JSON.
5. If evidence is insufficient to support a conclusion, say so explicitly
   rather than speculating.
"""

class AIInvestigator:
    def __init__(self):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = 'claude-3-sonnet-20240229'  # Update to matching actual models
    
    async def investigate(self, case_id: uuid.UUID, case_data: dict,
                          evidence: list[dict], shap_features: list[dict] = None,
                          graph_stats: dict = None, timeline: list[dict] = None,
                          follow_up_question: str = None) -> InvestigateResponse:
        """Run the full investigation pipeline."""
        context = self._build_context(case_data, evidence, shap_features, graph_stats, timeline, follow_up_question)
        valid_evidence_ids = {str(e['evidence_id']) for e in evidence}
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}]
            )
            raw_output = response.content[0].text
            report = self._validate_and_ground(raw_output, valid_evidence_ids)
            if report:
                return InvestigateResponse(case_id=case_id, report=report)
            
            # Retry once
            retry_prompt = f"Your previous output failed validation. Please ensure it is strict JSON matching the schema, and all key_evidence IDs are valid.\n\nContext:\n{context}"
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": retry_prompt}]
            )
            raw_output = response.content[0].text
            report = self._validate_and_ground(raw_output, valid_evidence_ids)
            if report:
                return InvestigateResponse(case_id=case_id, report=report)
                
            return InvestigateResponse(
                case_id=case_id, 
                fallback_message="AI failed to generate a valid and grounded report.",
                grounded=False
            )
            
        except Exception as e:
            logger.error("ai_investigator_error", error=str(e))
            return InvestigateResponse(
                case_id=case_id,
                fallback_message="An error occurred during AI investigation.",
                grounded=False
            )
    
    def _build_context(self, case_data, evidence, shap_features, graph_stats, timeline, question) -> str:
        """Build the context injection following template."""
        context = f"CASE: {case_data['case_id']}\n"
        context += f"SCORES: overall={case_data['overall_risk_score']}, transaction={case_data['transaction_risk_score']},\n"
        context += f"        network={case_data['network_risk_score']}, temporal={case_data['temporal_risk_score']}\n"
        context += "EVIDENCE:\n"
        for e in evidence:
            context += f"  - id={e['evidence_id']}, type={e['evidence_type']}, severity={e['severity']}, description={e['description']}\n"
        if shap_features:
            context += f"TOP SHAP FEATURES: {json.dumps(shap_features)}\n"
        if graph_stats:
            context += f"GRAPH STATS: {json.dumps(graph_stats)}\n"
        if timeline:
            context += f"TIMELINE: {json.dumps(timeline, default=str)}\n"
        if question:
            context += f"ANALYST QUESTION: {question}\n"
        return context
    
    def _validate_and_ground(self, raw_output: str, valid_evidence_ids: set) -> InvestigationReport | None:
        """Parse JSON, validate schema, check all key_evidence IDs exist."""
        try:
            # Try to extract JSON from the output in case there's markdown wrapping
            if "```json" in raw_output:
                raw_output = raw_output.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_output:
                raw_output = raw_output.split("```")[1].split("```")[0].strip()
                
            data = json.loads(raw_output)
            report = InvestigationReport(**data)
            # Grounding check: every evidence ID must exist
            for eid in report.key_evidence:
                if str(eid) not in valid_evidence_ids:
                    logger.warning('ungrounded_evidence', evidence_id=eid)
                    return None
            return report
        except Exception as e:
            logger.warning('ai_output_validation_failed', error=str(e), output=raw_output)
            return None
