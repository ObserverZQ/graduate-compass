"""Deterministic published-requirement assessment tool."""

from apps.api.schemas.agent_tools import (
    AssessRequirementsInput,
    AssessRequirementsOutput,
    EvidenceConfidence,
    RequirementAssessment,
)


def assess_requirements(
    payload: AssessRequirementsInput,
) -> AssessRequirementsOutput:
    """Compare reviewed evidence with published requirements, without filtering.

    This tool reports readiness evidence only; it does not estimate admission
    probability and does not remove programs from the candidate set.
    """

    assessments: list[RequirementAssessment] = []
    for program in payload.programs:
        strengths: list[str] = []
        gaps: list[str] = []
        uncertainties: list[str] = []
        comparable_requirements = 0

        if (
            payload.applicant.gpa is not None
            and payload.applicant.gpa_base is not None
            and program.min_gpa is not None
        ):
            comparable_requirements += 1
            normalized_gpa = (
                payload.applicant.gpa / payload.applicant.gpa_base * 4
            )
            if normalized_gpa >= program.min_gpa:
                strengths.append(
                    f"Normalized GPA {normalized_gpa:.2f} meets the published "
                    f"minimum {program.min_gpa:.2f}."
                )
            else:
                gaps.append(
                    f"Normalized GPA {normalized_gpa:.2f} is below the published "
                    f"minimum {program.min_gpa:.2f}."
                )
        elif program.min_gpa is None:
            uncertainties.append("The program does not publish a minimum GPA.")
        else:
            uncertainties.append("The applicant profile lacks a comparable GPA.")

        language_comparisons: list[tuple[str, float, float]] = []
        if (
            payload.applicant.toefl_scale_120 is not None
            and program.min_toefl is not None
        ):
            language_comparisons.append(
                (
                    "TOEFL",
                    float(payload.applicant.toefl_scale_120),
                    float(program.min_toefl),
                )
            )
        if payload.applicant.ielts is not None and program.min_ielts is not None:
            language_comparisons.append(
                ("IELTS", payload.applicant.ielts, program.min_ielts)
            )

        if language_comparisons:
            comparable_requirements += 1
            # TOEFL and IELTS are normally alternative proofs. Meeting either
            # available comparison therefore counts as positive evidence.
            passing = next(
                (
                    comparison
                    for comparison in language_comparisons
                    if comparison[1] >= comparison[2]
                ),
                None,
            )
            if passing:
                label, score, minimum = passing
                strengths.append(
                    f"{label} {score:g} meets the published minimum {minimum:g}."
                )
            else:
                gaps.append(
                    "; ".join(
                        f"{label} {score:g} is below {minimum:g}"
                        for label, score, minimum in language_comparisons
                    )
                    + "."
                )
        else:
            uncertainties.append(
                "No applicant language score can be compared with a published minimum."
            )

        if program.gre_required:
            # The current reviewed profile has no GRE field, so a published GRE
            # requirement cannot honestly be classified as met or missing.
            uncertainties.append(
                "The program requires the GRE, but the reviewed profile does not capture it."
            )

        confidence = (
            EvidenceConfidence.HIGH
            if comparable_requirements >= 2
            else EvidenceConfidence.MEDIUM
            if comparable_requirements == 1
            else EvidenceConfidence.LOW
        )
        assessments.append(
            RequirementAssessment(
                program_id=program.program_id,
                strengths=strengths,
                gaps=gaps,
                uncertainties=uncertainties,
                evidence_confidence=confidence,
            )
        )

    return AssessRequirementsOutput(assessments=assessments)
