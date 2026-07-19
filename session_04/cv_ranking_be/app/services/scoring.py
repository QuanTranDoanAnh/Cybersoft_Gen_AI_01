from __future__ import annotations

import re
from datetime import datetime

from app.models import (
    CandidateScore,
    CriterionScore,
    JobProfile,
    RankingResponse,
    Recommendation,
    RequirementCheck,
    RubricCriterion,
)
from app.services.parser import guess_person_name


KNOWN_SKILLS = [
    "python",
    "fastapi",
    "django",
    "flask",
    "java",
    "spring",
    "node.js",
    "nodejs",
    "typescript",
    "javascript",
    "react",
    "next.js",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "ci/cd",
    "github actions",
    "gitlab ci",
    "rest api",
    "graphql",
    "kafka",
    "rabbitmq",
    "microservices",
    "unit test",
    "pytest",
    "monitoring",
    "observability",
    "machine learning",
    "langchain",
    "langgraph",
    "llm",
    "n8n",
    "data pipeline",
    "pandas",
    "scikit-learn",
    "tensorflow",
    "pytorch",
]

DOMAIN_TERMS = [
    "ecommerce",
    "e-commerce",
    "fintech",
    "banking",
    "healthcare",
    "edtech",
    "saas",
    "crm",
    "retail",
    "logistics",
    "payment",
    "insurance",
    "education",
    "hr",
    "recruitment",
]

REQUIREMENT_SECTION_MARKERS = [
    "requirements",
    "required qualifications",
    "minimum qualifications",
    "qualifications",
    "must have",
    "required skills",
    "skills required",
    "yêu cầu",
    "yêu cầu công việc",
    "yêu cầu ứng viên",
    "kỹ năng bắt buộc",
]

RESPONSIBILITY_SECTION_MARKERS = [
    "responsibilities",
    "what you will do",
    "role overview",
    "job description",
    "mô tả",
    "trách nhiệm",
    "nhiệm vụ",
]

NICE_TO_HAVE_MARKERS = [
    "nice to have",
    "preferred",
    "bonus",
    "plus",
    "is a plus",
    "advantage",
    "optional",
    "desirable",
    "ưu tiên",
    "lợi thế",
    "điểm cộng",
]

SECTION_STOP_MARKERS = [
    "benefits",
    "about",
    "company",
    "compensation",
    "application",
    "quyền lợi",
    "phúc lợi",
    "về chúng tôi",
]

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "you",
    "your",
    "và",
    "của",
    "cho",
    "có",
    "là",
    "trong",
    "với",
    "các",
    "một",
    "những",
    "ứng",
    "viên",
    "công",
    "việc",
}


def default_rubric() -> list[RubricCriterion]:
    return [
        RubricCriterion(
            name="Required skills",
            description="Core hard skills explicitly required by the JD.",
            weight=30,
            scoring_guide="Full score when the CV shows clear evidence for most required skills.",
        ),
        RubricCriterion(
            name="Relevant experience",
            description="Years and relevance of experience compared with the role.",
            weight=20,
            scoring_guide="Prioritize comparable work, not only years.",
        ),
        RubricCriterion(
            name="Responsibilities fit",
            description="Overlap between JD responsibilities and candidate work history.",
            weight=20,
            scoring_guide="Score based on demonstrated ownership of similar responsibilities.",
        ),
        RubricCriterion(
            name="Project impact",
            description="Production projects, quantified results, ownership, and business impact.",
            weight=10,
            scoring_guide="Reward measurable impact and production delivery.",
        ),
        RubricCriterion(
            name="Domain fit",
            description="Industry or product-context overlap.",
            weight=10,
            scoring_guide="Score similar business/domain context higher.",
        ),
        RubricCriterion(
            name="Nice-to-have",
            description="Preferred skills or bonuses from the JD.",
            weight=5,
            scoring_guide="Do not let nice-to-have skills dominate must-have requirements.",
        ),
        RubricCriterion(
            name="Education and certifications",
            description="Relevant education, certificates, or formal training.",
            weight=5,
            scoring_guide="Score only role-relevant credentials.",
            evidence_required=False,
        ),
    ]


def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("node js", "node.js").replace("next js", "next.js")
    return re.sub(r"\s+", " ", text).strip()


def clean_line(line: str) -> str:
    line = re.sub(r"^\s*[-*•·]\s*", "", line or "").strip()
    line = re.sub(r"^\s*\d+[.)]\s*", "", line).strip()
    line = re.sub(r"\s+", " ", line)
    return line.strip(" ;")


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-ZÀ-ỹ0-9.+/#-]+", normalize_text(text))
        if len(token) > 2 and token not in STOPWORDS
    }


def extract_known_terms(text: str, vocabulary: list[str]) -> list[str]:
    normalized = normalize_text(text)
    return sorted({term for term in vocabulary if term in normalized})


def extract_years(text: str) -> int | None:
    matches = re.findall(r"(\d+)\s*\+?\s*(?:years?|yrs?|năm)", normalize_text(text))
    if not matches:
        return None
    return max(int(value) for value in matches)


def is_optional(line: str) -> bool:
    normalized = normalize_text(line)
    return any(marker in normalized for marker in NICE_TO_HAVE_MARKERS)


def marker_in_line(line: str, markers: list[str]) -> bool:
    normalized = normalize_text(clean_line(line).rstrip(":"))
    return any(marker in normalized for marker in markers)


def is_heading_like(line: str) -> bool:
    cleaned = clean_line(line)
    starts_with_bullet = bool(re.match(r"^\s*[-*•·]", line or ""))
    return bool(cleaned) and not starts_with_bullet and len(cleaned) <= 80 and not cleaned.endswith(".")


def first_non_empty_line(text: str, fallback: str) -> str:
    for line in text.splitlines():
        cleaned = clean_line(line)
        if cleaned:
            return cleaned[:90]
    return fallback


def split_jd_sections(jd_text: str) -> dict[str, list[str]]:
    sections = {"requirements": [], "responsibilities": [], "nice_to_have": []}
    current: str | None = None

    for raw_line in jd_text.splitlines():
        cleaned = clean_line(raw_line)
        if not cleaned:
            continue

        if is_heading_like(raw_line) and marker_in_line(raw_line, NICE_TO_HAVE_MARKERS):
            current = "nice_to_have"
            continue
        if is_heading_like(raw_line) and marker_in_line(raw_line, REQUIREMENT_SECTION_MARKERS):
            current = "requirements"
            continue
        if is_heading_like(raw_line) and marker_in_line(raw_line, RESPONSIBILITY_SECTION_MARKERS):
            current = "responsibilities"
            continue
        if is_heading_like(raw_line) and marker_in_line(raw_line, SECTION_STOP_MARKERS):
            current = None
            continue

        if current:
            if current == "requirements" and is_optional(cleaned):
                sections["nice_to_have"].append(cleaned)
            else:
                sections[current].append(cleaned)

    return sections


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_items: list[str] = []
    for item in items:
        key = normalize_text(item)
        if key and key not in seen:
            seen.add(key)
            unique_items.append(item)
    return unique_items


def analyze_job(jd_text: str) -> JobProfile:
    sections = split_jd_sections(jd_text)
    requirements = sections["requirements"]
    must_have = [item for item in requirements if not is_optional(item)]
    nice_to_have = sections["nice_to_have"] + [item for item in requirements if is_optional(item)]

    if not must_have:
        years_required = extract_years(jd_text)
        if years_required:
            must_have.append(f"{years_required}+ years of relevant experience")
        must_have.extend(extract_known_terms(jd_text, KNOWN_SKILLS)[:8])

    required_skills = extract_known_terms("\n".join(must_have), KNOWN_SKILLS)
    if not required_skills:
        required_skills = extract_known_terms(jd_text, KNOWN_SKILLS)

    return JobProfile(
        title=first_non_empty_line(jd_text, "Untitled role"),
        must_have_requirements=dedupe(must_have)[:12],
        nice_to_have_requirements=dedupe(nice_to_have)[:12],
        responsibilities=dedupe(sections["responsibilities"])[:16],
        required_skills=required_skills,
        domain_terms=extract_known_terms(jd_text, DOMAIN_TERMS),
        years_required=extract_years("\n".join(must_have)) or extract_years(jd_text),
    )


def find_evidence(text: str, terms: list[str], limit: int = 3) -> list[str]:
    if not terms:
        return []
    chunks = [chunk.strip(" -•\t") for chunk in re.split(r"[\n.;]+", text) if chunk.strip(" -•\t")]
    evidence: list[str] = []
    for chunk in chunks:
        normalized = normalize_text(chunk)
        if any(term in normalized for term in terms):
            evidence.append(chunk)
        if len(evidence) >= limit:
            break
    return evidence


def requirement_status(requirement: str, cv_text: str) -> RequirementCheck:
    req_norm = normalize_text(requirement)
    cv_norm = normalize_text(cv_text)

    required_years = extract_years(requirement)
    candidate_years = extract_years(cv_text)
    if required_years:
        if candidate_years and candidate_years >= required_years:
            return RequirementCheck(
                requirement=requirement,
                status="met",
                evidence=f"CV mentions {candidate_years} years of relevant experience.",
            )
        if candidate_years:
            return RequirementCheck(
                requirement=requirement,
                status="partial",
                evidence=f"CV mentions {candidate_years} years; JD asks for {required_years}.",
            )

    expected_skills = extract_known_terms(requirement, KNOWN_SKILLS)
    if expected_skills:
        matched_skills = extract_known_terms(cv_text, expected_skills)
        required_count = 1 if (" or " in req_norm or "/" in requirement) else len(expected_skills)
        evidence = find_evidence(cv_text, matched_skills, limit=1)
        if len(matched_skills) >= required_count:
            return RequirementCheck(
                requirement=requirement,
                status="met",
                evidence=evidence[0] if evidence else f"Matched skills: {', '.join(matched_skills)}.",
            )
        if matched_skills:
            return RequirementCheck(
                requirement=requirement,
                status="partial",
                evidence=evidence[0] if evidence else f"Matched skills: {', '.join(matched_skills)}.",
            )

    if req_norm and req_norm in cv_norm:
        evidence = find_evidence(cv_text, [req_norm], limit=1)
        return RequirementCheck(requirement=requirement, status="met", evidence=evidence[0] if evidence else requirement)

    req_tokens = tokenize(requirement)
    cv_tokens = tokenize(cv_text)
    coverage = len(req_tokens & cv_tokens) / len(req_tokens) if req_tokens else 0
    evidence = find_evidence(cv_text, list(req_tokens & cv_tokens), limit=1)
    if coverage >= 0.7:
        return RequirementCheck(requirement=requirement, status="met", evidence=evidence[0] if evidence else "")
    if coverage >= 0.35:
        return RequirementCheck(requirement=requirement, status="partial", evidence=evidence[0] if evidence else "")
    return RequirementCheck(requirement=requirement, status="missing")


def score_required_skills(job: JobProfile, cv_text: str, weight: int) -> CriterionScore:
    expected = job.required_skills
    matched = extract_known_terms(cv_text, expected)
    ratio = len(matched) / len(expected) if expected else 0.5
    return CriterionScore(
        name="Required skills",
        max_points=weight,
        awarded_points=round(weight * ratio, 2),
        score_ratio=round(ratio, 2),
        reason=f"Matched {len(matched)}/{len(expected)} required skills.",
        evidence=find_evidence(cv_text, matched),
    )


def score_experience(job: JobProfile, cv_text: str, weight: int) -> CriterionScore:
    candidate_years = extract_years(cv_text) or 0
    if job.years_required:
        ratio = min(candidate_years / job.years_required, 1.0)
        reason = f"CV shows {candidate_years} years; JD expects {job.years_required}."
    else:
        terms = tokenize("\n".join(job.must_have_requirements + job.responsibilities))
        cv_terms = tokenize(cv_text)
        matched = list(terms & cv_terms)
        ratio = min(len(matched) / 12, 1.0) if matched else 0.35
        reason = f"Matched {len(matched)} experience context terms."
    return CriterionScore(
        name="Relevant experience",
        max_points=weight,
        awarded_points=round(weight * ratio, 2),
        score_ratio=round(ratio, 2),
        reason=reason,
        evidence=find_evidence(cv_text, ["experience", "years", "năm"], limit=2),
    )


def score_responsibilities(job: JobProfile, cv_text: str, weight: int) -> CriterionScore:
    terms = sorted(tokenize("\n".join(job.responsibilities)))
    if not terms:
        terms = sorted(tokenize("\n".join(job.must_have_requirements)))
    cv_norm = normalize_text(cv_text)
    matched = [term for term in terms if term in cv_norm]
    ratio = len(matched) / len(terms) if terms else 0.5
    return CriterionScore(
        name="Responsibilities fit",
        max_points=weight,
        awarded_points=round(weight * ratio, 2),
        score_ratio=round(ratio, 2),
        reason=f"Matched {len(matched)}/{len(terms)} responsibility signals.",
        evidence=find_evidence(cv_text, matched[:8]),
    )


def score_project_impact(cv_text: str, weight: int) -> CriterionScore:
    impact_terms = ["reduced", "increased", "improved", "launched", "built", "optimized", "%", "giảm", "tăng", "xây"]
    matched = [term for term in impact_terms if term in normalize_text(cv_text)]
    ratio = min(len(matched) / 4, 1.0)
    return CriterionScore(
        name="Project impact",
        max_points=weight,
        awarded_points=round(weight * ratio, 2),
        score_ratio=round(ratio, 2),
        reason=f"Found {len(matched)} project or impact signals.",
        evidence=find_evidence(cv_text, matched),
    )


def score_domain(job: JobProfile, cv_text: str, weight: int) -> CriterionScore:
    matched = extract_known_terms(cv_text, job.domain_terms)
    ratio = len(matched) / len(job.domain_terms) if job.domain_terms else 0.5
    return CriterionScore(
        name="Domain fit",
        max_points=weight,
        awarded_points=round(weight * ratio, 2),
        score_ratio=round(ratio, 2),
        reason=f"Matched domain terms: {', '.join(matched) or 'not clearly shown'}.",
        evidence=find_evidence(cv_text, matched),
    )


def score_nice_to_have(job: JobProfile, cv_text: str, weight: int) -> CriterionScore:
    expected = extract_known_terms("\n".join(job.nice_to_have_requirements), KNOWN_SKILLS)
    matched = extract_known_terms(cv_text, expected)
    ratio = len(matched) / len(expected) if expected else 0.5
    return CriterionScore(
        name="Nice-to-have",
        max_points=weight,
        awarded_points=round(weight * ratio, 2),
        score_ratio=round(ratio, 2),
        reason=f"Matched {len(matched)}/{len(expected)} preferred skills.",
        evidence=find_evidence(cv_text, matched),
    )


def score_education(cv_text: str, weight: int) -> CriterionScore:
    education_terms = ["b.s", "bachelor", "master", "phd", "degree", "cert", "certification", "đại học", "cử nhân", "thạc sĩ"]
    matched = [term for term in education_terms if term in normalize_text(cv_text)]
    ratio = min(len(matched) / 2, 1.0) if matched else 0.3
    return CriterionScore(
        name="Education and certifications",
        max_points=weight,
        awarded_points=round(weight * ratio, 2),
        score_ratio=round(ratio, 2),
        reason=f"Education/certification evidence: {', '.join(matched) or 'limited'}.",
        evidence=find_evidence(cv_text, matched),
    )


def recommendation_for(score: float, qualified: bool) -> Recommendation:
    if not qualified and score < 60:
        return "not_match"
    if score >= 90:
        return "strong_match"
    if score >= 75:
        return "match"
    if score >= 60:
        return "potential"
    if score >= 40:
        return "weak_match"
    return "not_match"


def score_candidate(file_name: str, cv_text: str, job: JobProfile, rubric: list[RubricCriterion]) -> CandidateScore:
    checks = [requirement_status(requirement, cv_text) for requirement in job.must_have_requirements]
    missing_must_have = [check.requirement for check in checks if check.status == "missing"]
    qualified = not missing_must_have

    score_functions = {
        "Required skills": lambda weight: score_required_skills(job, cv_text, weight),
        "Relevant experience": lambda weight: score_experience(job, cv_text, weight),
        "Responsibilities fit": lambda weight: score_responsibilities(job, cv_text, weight),
        "Project impact": lambda weight: score_project_impact(cv_text, weight),
        "Domain fit": lambda weight: score_domain(job, cv_text, weight),
        "Nice-to-have": lambda weight: score_nice_to_have(job, cv_text, weight),
        "Education and certifications": lambda weight: score_education(cv_text, weight),
    }
    criterion_scores = [score_functions[item.name](item.weight) for item in rubric if item.name in score_functions]
    raw_score = round(sum(item.awarded_points for item in criterion_scores), 2)
    overall_score = min(raw_score, 59.0) if missing_must_have else raw_score

    missing_skills = [skill for skill in job.required_skills if skill not in normalize_text(cv_text)]
    risks: list[str] = []
    if missing_must_have:
        risks.append(f"Missing must-have: {', '.join(missing_must_have[:4])}")
    if missing_skills:
        risks.append(f"Skills not clearly shown: {', '.join(missing_skills[:6])}")
    low_scores = [item.name for item in criterion_scores if item.score_ratio < 0.45]
    if low_scores:
        risks.append(f"Low evidence in: {', '.join(low_scores[:3])}")

    top = sorted(criterion_scores, key=lambda item: item.awarded_points, reverse=True)[:2]
    summary = (
        f"Estimated {overall_score}/100 for {job.title}. "
        f"Strongest areas: {', '.join(item.name for item in top) or 'not enough evidence'}."
    )

    questions = [
        "Walk through the project or role that best matches this JD.",
        "Which requirement from this JD have you handled in production?",
        "What would you need to learn before starting this role?",
    ]
    for skill in missing_skills[:2]:
        questions.append(f"Can you describe your practical experience with {skill}?")

    confidence = min(0.88, 0.5 + min((len(cv_text) + len(job.title)) / 7000, 1.0) * 0.25 + len(checks) * 0.015)

    return CandidateScore(
        file_name=file_name,
        candidate_name=guess_person_name(cv_text, file_name),
        overall_score=round(overall_score, 2),
        recommendation=recommendation_for(overall_score, qualified),
        qualified=qualified,
        confidence_score=round(confidence, 2),
        summary=summary,
        must_have_checks=checks,
        criterion_scores=criterion_scores,
        matched_requirements=[check.requirement for check in checks if check.status in {"met", "partial"}],
        missing_requirements=missing_must_have + missing_skills[:6],
        risks=risks,
        interview_questions=questions[:5],
    )


def rank_candidates(jd_text: str, cv_documents: list[tuple[str, str]]) -> RankingResponse:
    job = analyze_job(jd_text)
    rubric = default_rubric()
    candidates = [score_candidate(file_name, cv_text, job, rubric) for file_name, cv_text in cv_documents]
    candidates.sort(key=lambda item: (item.qualified, item.overall_score, item.confidence_score), reverse=True)
    return RankingResponse(generated_at=datetime.utcnow(), job_profile=job, rubric=rubric, candidates=candidates)
