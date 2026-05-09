import os
import pickle
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple, Optional

import pandas as pd
from django.conf import settings
from django.core.management import call_command


MODELS_DIR = os.path.join(settings.BASE_DIR, "static", "models")


@dataclass(frozen=True)
class RecommenderArtifacts:
    jobs: pd.DataFrame
    similarity: object
    id_to_index: Dict[int, int]


def _artifact_paths() -> Tuple[str, str]:
    return (
        os.path.join(MODELS_DIR, "jobs.pkl"),
        os.path.join(MODELS_DIR, "similarity.pkl"),
    )


@lru_cache(maxsize=1)
def load_artifacts() -> RecommenderArtifacts:
    jobs_path, sim_path = _artifact_paths()
    if not os.path.exists(jobs_path) or not os.path.exists(sim_path):
        # Portfolio-friendly behavior: auto-build artifacts on first run.
        # Uses demo seed only if the DB has no jobs.
        try:
            call_command("build_recommender_models", demo=True)
        except Exception as e:
            raise RuntimeError(
                "Missing recommender artifacts and auto-build failed.\n"
                "Try running:\n"
                "  python manage.py build_recommender_models --demo\n"
                "Or if you have a dataset:\n"
                "  python manage.py build_recommender_models --csv \"path/to/jobs.csv\"\n"
                f"Expected files:\n  {jobs_path}\n  {sim_path}\n\n"
                f"Original error: {e}"
            ) from e

    with open(jobs_path, "rb") as f:
        jobs = pickle.load(f)
    with open(sim_path, "rb") as f:
        similarity = pickle.load(f)

    if not isinstance(jobs, pd.DataFrame) or "Title" not in jobs.columns or "id" not in jobs.columns:
        raise RuntimeError(
            "Invalid jobs.pkl format. Rebuild with:\n"
            "  python manage.py build_recommender_models"
        )

    id_to_index: Dict[int, int] = {}
    for i, jid in enumerate(jobs["id"].tolist()):
        try:
            id_to_index[int(jid)] = i
        except Exception:
            continue

    return RecommenderArtifacts(jobs=jobs, similarity=similarity, id_to_index=id_to_index)


def resolve_title_to_index(artifacts: RecommenderArtifacts, title: str) -> Optional[int]:
    q = (title or "").strip()
    if not q:
        return None
    titles = artifacts.jobs["Title"].fillna("").astype(str).tolist()
    # Normalize with casefold for better matching.
    titles_norm = [t.casefold() for t in titles]
    qn = q.casefold()
    try:
        idx = titles_norm.index(qn)
        return idx
    except ValueError:
        pass

    # Fuzzy fallback: difflib on normalized titles.
    import difflib

    matches = difflib.get_close_matches(qn, titles_norm, n=1, cutoff=0.55)
    if not matches:
        return None
    return titles_norm.index(matches[0])


def recommend_job_ids_by_index(artifacts: RecommenderArtifacts, job_index: int, top_n: int = 5) -> list[int]:
    similarity = artifacts.similarity
    sim_scores = list(enumerate(similarity[job_index]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1 : top_n + 1]
    rec_indices = [i for i, _ in sim_scores]
    rec_ids = artifacts.jobs.iloc[rec_indices]["id"].tolist()
    return [int(x) for x in rec_ids if pd.notna(x)]


def recommend_by_index(job_index: int, top_n: int = 5) -> pd.DataFrame:
    artifacts = load_artifacts()
    rec_ids = recommend_job_ids_by_index(artifacts, job_index=job_index, top_n=top_n)
    return artifacts.jobs[artifacts.jobs["id"].isin(rec_ids)]

