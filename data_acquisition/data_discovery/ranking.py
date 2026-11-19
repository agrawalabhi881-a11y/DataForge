import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatasetRanker:
    """
    Scores and ranks candidate datasets against user dataset requirements
    across domain match, text relevance, record count, schema/label hints,
    format, and access/license eligibility.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "domain": 0.25,
            "relevance": 0.20,
            "record_count": 0.20,
            "features_and_labels": 0.15,
            "format": 0.10,
            "access_and_license": 0.10,
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    def _score_domain(self, candidate: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        target_domain = (requirements.get("domain") or "").strip().lower()
        if not target_domain:
            return 0.5

        candidate_domain = (candidate.get("domain") or "").strip().lower()
        text_blob = " ".join(
            str(candidate.get(k) or "")
            for k in ("name", "title", "description", "task", "area")
        ).lower()

        if candidate_domain == target_domain:
            return 1.0
        if target_domain.replace("_", " ") in text_blob or target_domain in text_blob:
            return 0.75
        return 0.1 if candidate_domain else 0.35

    def _score_relevance(self, candidate: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        query = (requirements.get("query") or requirements.get("description") or "").strip().lower()
        keywords = [
            str(kw).strip().lower()
            for kw in (requirements.get("keywords") or [])
            if str(kw).strip()
        ]
        terms = [t for t in query.split() if len(t) > 2] + keywords
        if not terms:
            return 0.5

        haystack = " ".join(
            str(candidate.get(k) or "")
            for k in ("name", "title", "description", "dataset_id")
        ).lower()
        if not haystack.strip():
            return 0.0

        matched = sum(1 for term in set(terms) if term in haystack)
        return min(1.0, matched / len(set(terms)))

    def _score_record_count(self, candidate: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        min_records = requirements.get("min_records") or requirements.get("record_count")
        if min_records is None:
            return 0.5

        try:
            min_records_int = int(min_records)
        except (TypeError, ValueError):
            return 0.5

        raw_count = candidate.get("record_count")
        if raw_count is None:
            raw_count = candidate.get("num_instances")

        if raw_count is None:
            return 0.25

        try:
            count_int = int(raw_count)
        except (TypeError, ValueError):
            return 0.25

        if min_records_int <= 0:
            return 1.0 if count_int > 0 else 0.2
        if count_int >= min_records_int:
            return 1.0
        return max(0.0, count_int / min_records_int)

    def _score_features_and_labels(self, candidate: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        req_features = [
            str(f).strip().lower()
            for f in (requirements.get("required_features") or requirements.get("features") or [])
            if str(f).strip()
        ]
        req_labels = [
            str(lbl).strip().lower()
            for lbl in (requirements.get("labels") or [])
            if str(lbl).strip()
        ]

        if not req_features and not req_labels:
            return 0.5

        cand_features = [str(f).strip().lower() for f in (candidate.get("features") or [])]
        cand_text = " ".join(
            str(candidate.get(k) or "")
            for k in ("name", "description", "target_col")
        ).lower()

        score = 0.0
        checks = 0

        if req_features:
            checks += 1
            if cand_features:
                feat_hits = sum(
                    1 for rf in req_features if any(rf in cf or cf in rf for cf in cand_features)
                )
                score += feat_hits / len(req_features)
            else:
                text_hits = sum(1 for rf in req_features if rf in cand_text)
                score += 0.5 * (text_hits / len(req_features))

        if req_labels:
            checks += 1
            label_hits = sum(1 for rl in req_labels if rl in cand_text)
            score += label_hits / len(req_labels)

        return score / checks if checks else 0.5

    def _score_format(self, candidate: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        preferred_formats = [
            str(fmt).strip().lower().lstrip(".")
            for fmt in (requirements.get("formats") or ([requirements["format"]] if requirements.get("format") else []))
            if str(fmt).strip()
        ]
        if not preferred_formats:
            return 0.5

        cand_formats: List[str] = []
        if candidate.get("format"):
            cand_formats.append(str(candidate["format"]).strip().lower().lstrip("."))
        for fmt in candidate.get("formats") or []:
            cand_formats.append(str(fmt).strip().lower().lstrip("."))

        if not cand_formats:
            return 0.25

        if any(fmt in preferred_formats for fmt in cand_formats):
            return 1.0
        return 0.2

    def _score_access_and_license(self, candidate: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        access_status = str(candidate.get("access_status") or "").strip().lower()
        if access_status in {"ineligible", "restricted", "blocked"}:
            return 0.0

        require_verified_license = bool(requirements.get("require_verified_license", False))
        license_val = candidate.get("license")
        has_license = bool(
            license_val
            and str(license_val).strip().lower() not in {"unknown", "none", "null", "unverified"}
        )

        if require_verified_license and not has_license:
            return 0.1
        if access_status == "eligible" and has_license:
            return 1.0
        if has_license or access_status == "eligible":
            return 0.8
        return 0.4

    def score_candidate(self, candidate: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        """Computes a weighted relevance score in [0.0, 1.0] for a single candidate."""
        breakdown = {
            "domain": self._score_domain(candidate, requirements),
            "relevance": self._score_relevance(candidate, requirements),
            "record_count": self._score_record_count(candidate, requirements),
            "features_and_labels": self._score_features_and_labels(candidate, requirements),
            "format": self._score_format(candidate, requirements),
            "access_and_license": self._score_access_and_license(candidate, requirements),
        }

        total_weight = sum(self.weights.values()) or 1.0
        weighted_sum = sum(
            breakdown[key] * self.weights.get(key, 0.0) for key in breakdown
        )
        return round(weighted_sum / total_weight, 4)

    def rank_datasets(
        self,
        candidates: List[Dict[str, Any]],
        requirements: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns a new list of candidate dataset dictionaries sorted by descending
        `relevance_score`, attaching `relevance_score` without mutating caller inputs.
        """
        reqs = requirements or {}
        self.logger.info(f"Ranking {len(candidates)} candidate datasets...")

        scored: List[Dict[str, Any]] = []
        for item in candidates:
            entry = dict(item)
            entry["relevance_score"] = self.score_candidate(entry, reqs)
            scored.append(entry)

        scored.sort(key=lambda d: d.get("relevance_score", 0.0), reverse=True)
        return scored