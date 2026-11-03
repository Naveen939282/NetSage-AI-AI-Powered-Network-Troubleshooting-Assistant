from __future__ import annotations

from review.review_logger import append_review


def submit_review(decision, case_id, ai_root, corrected_root, note,
                  edited_osi_layer="", edited_confidence="",
                  edited_next_command="", edited_fix_steps="",
                  correlation_status="", correlation_confidence="",
                  ai_support_level="", rule_support_level="",
                  recommended_review_action="", conflicts=""):
    """Persist a human review decision.

    decision: ACCEPT | REJECT | EDIT
    For EDIT, the edited_osi_layer / edited_confidence / edited_next_command /
    edited_fix_steps kwargs carry the modified diagnosis fields.
    The correlation_* kwargs carry the deterministic correlation result that
    was shown to the reviewer first (status, confidence, support levels,
    recommendation, and any conflicts).
    """
    row = {
        "case_id": case_id,
        "ai_root_cause": ai_root,
        "human_decision": decision,
        "corrected_root_cause": corrected_root,
        "reason_for_correction": note,
        "reviewer_note": note,
        "edited_osi_layer": edited_osi_layer,
        "edited_confidence": edited_confidence,
        "edited_next_command": edited_next_command,
        "edited_fix_steps": edited_fix_steps,
        "correlation_status": correlation_status,
        "correlation_confidence": correlation_confidence,
        "ai_support_level": ai_support_level,
        "rule_support_level": rule_support_level,
        "recommended_review_action": recommended_review_action,
        "conflicts": conflicts,
    }
    append_review(row)
