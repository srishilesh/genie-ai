from langsmith import traceable

from src.schemas.report import ResearchReport


@traceable(name="scorer")
def score(report: ResearchReport) -> tuple[ResearchReport, float, str]:
    points = 0.0
    reasons = []

    if len(report.sources_used) >= 3:
        points += 0.3
        reasons.append(f"{len(report.sources_used)} sources cited")
    elif report.sources_used:
        points += 0.15
        reasons.append(f"only {len(report.sources_used)} source(s) cited")

    comparisons_with_data = [
        c for c in report.comparisons if c.agreement or c.conflicts
    ]
    if comparisons_with_data:
        ratio = len(comparisons_with_data) / max(len(report.comparisons), 1)
        points += 0.3 * ratio
        reasons.append(f"{len(comparisons_with_data)}/{len(report.comparisons)} comparisons supported")

    if report.findings:
        points += min(0.2, 0.05 * len(report.findings))
        reasons.append(f"{len(report.findings)} findings")

    if report.open_questions:
        penalty = min(0.1, 0.02 * len(report.open_questions))
        points -= penalty
        reasons.append(f"-{penalty:.2f} for {len(report.open_questions)} open questions")

    if report.recommendation:
        points += 0.1
        reasons.append("recommendation present")

    if report.citations:
        points += 0.1
        reasons.append("citations present")

    confidence = round(max(0.0, min(1.0, points)), 3)
    rationale = "; ".join(reasons)
    return report, confidence, rationale
