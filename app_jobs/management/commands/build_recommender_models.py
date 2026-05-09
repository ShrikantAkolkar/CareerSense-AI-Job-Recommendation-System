import os
import pickle

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from app_jobs.models import Job


class Command(BaseCommand):
    help = "Build jobs.pkl and similarity.pkl for ML recommendations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default="",
            help=(
                "Optional path to jobs CSV. If DB is empty, jobs will be loaded from CSV "
                "and inserted into the DB before building artifacts."
            ),
        )
        parser.add_argument(
            "--demo",
            action="store_true",
            help="If DB is empty and no CSV is provided, seed a small demo dataset first.",
        )
        parser.add_argument(
            "--output-dir",
            default=os.path.join(settings.BASE_DIR, "static", "models"),
            help="Output directory for jobs.pkl and similarity.pkl",
        )
        parser.add_argument(
            "--max-features",
            type=int,
            default=5000,
            help="Max features for TF-IDF vectorizer",
        )

    def handle(self, *args, **options):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "scikit-learn is required. Install with:\n"
                "  pip install scikit-learn"
            ) from e

        output_dir = options["output_dir"]
        max_features = options["max_features"]
        csv_path = (options.get("csv") or "").strip()
        demo = bool(options.get("demo"))

        if not Job.objects.exists():
            if csv_path:
                if not os.path.exists(csv_path):
                    raise RuntimeError(f"CSV not found at: {csv_path}")

                df_csv = pd.read_csv(csv_path)
                required_cols = {
                    "jobpost",
                    "date",
                    "Title",
                    "Company",
                    "Location",
                    "JobDescription",
                    "JobRequirment",
                    "RequiredQual",
                    "Year",
                    "Month",
                    "IT",
                    "tags",
                }
                missing = sorted(required_cols - set(df_csv.columns))
                if missing:
                    raise RuntimeError(f"CSV is missing columns: {missing}")

                objs = []
                for _, row in df_csv.iterrows():
                    objs.append(
                        Job(
                            jobpost=row.get("jobpost", "") or "",
                            date=row.get("date", "") or "",
                            Title=row.get("Title", "") or "",
                            Company=row.get("Company", "") or "",
                            Location=row.get("Location", "") or "",
                            JobDescription=row.get("JobDescription", "") or "",
                            JobRequirment=row.get("JobRequirment", "") or "",
                            RequiredQual=row.get("RequiredQual", "") or "",
                            Year=(
                                None
                                if pd.isna(row.get("Year"))
                                else int(row.get("Year"))
                            ),
                            Month=(
                                None
                                if pd.isna(row.get("Month"))
                                else int(row.get("Month"))
                            ),
                            IT=bool(row.get("IT", False)),
                            tags=row.get("tags", "") or "",
                        )
                    )
                Job.objects.bulk_create(objs, batch_size=1000)
                self.stdout.write(
                    self.style.SUCCESS(f"Imported {len(objs)} jobs from CSV into DB.")
                )
            elif demo:
                demo_jobs = [
                    Job(
                        Title="Data Analyst",
                        Company="ExampleCorp",
                        Location="Remote",
                        JobDescription="Analyze datasets, build dashboards, and deliver insights.",
                        JobRequirment="SQL, Python, data visualization",
                        RequiredQual="Bachelor's degree or equivalent experience",
                        IT=True,
                        tags="data,sql,python,analytics,bi",
                    ),
                    Job(
                        Title="Backend Developer",
                        Company="ExampleCorp",
                        Location="Bangalore",
                        JobDescription="Build APIs, integrate databases, and improve performance.",
                        JobRequirment="Python, Django, REST, PostgreSQL",
                        RequiredQual="Strong programming fundamentals",
                        IT=True,
                        tags="python,django,api,backend,sql",
                    ),
                    Job(
                        Title="HR Specialist",
                        Company="PeopleOps Inc.",
                        Location="Mumbai",
                        JobDescription="Manage recruiting pipeline and employee relations.",
                        JobRequirment="Communication, organization, HR processes",
                        RequiredQual="1+ years HR experience",
                        IT=False,
                        tags="hr,recruitment,peopleops,communication",
                    ),
                    Job(
                        Title="UI/UX Designer",
                        Company="Design Studio",
                        Location="Remote",
                        JobDescription="Design user flows, wireframes, and high-fidelity UI.",
                        JobRequirment="Figma, user research, prototyping",
                        RequiredQual="Portfolio of design work",
                        IT=True,
                        tags="design,ux,ui,figma,prototyping",
                    ),
                    Job(
                        Title="DevOps Engineer",
                        Company="CloudWorks",
                        Location="Hyderabad",
                        JobDescription="Maintain CI/CD pipelines and cloud infrastructure.",
                        JobRequirment="Docker, Kubernetes, CI/CD, AWS",
                        RequiredQual="Experience with cloud operations",
                        IT=True,
                        tags="devops,kubernetes,docker,aws,cicd",
                    ),
                ]
                Job.objects.bulk_create(demo_jobs, batch_size=1000)
                self.stdout.write(
                    self.style.SUCCESS(f"Seeded {len(demo_jobs)} demo jobs.")
                )
            else:
                raise RuntimeError(
                    "No jobs found in the database. Either import jobs first with:\n"
                    "  python manage.py import_jobs_csv\n"
                    "Or provide a CSV path:\n"
                    "  python manage.py build_recommender_models --csv \"data job posts.csv\"\n"
                    "Or generate a small demo dataset:\n"
                    "  python manage.py build_recommender_models --demo"
                )

        qs = Job.objects.order_by("id").values(
            "id",
            "Title",
            "Company",
            "Location",
            "JobDescription",
            "JobRequirment",
            "RequiredQual",
            "tags",
        )
        rows = list(qs)
        if not rows:
            raise RuntimeError(
                "No jobs found in the database. Import jobs first with:\n"
                "  python manage.py import_jobs_csv"
            )

        df = pd.DataFrame(rows)

        text_cols = [
            "Title",
            "Company",
            "Location",
            "JobDescription",
            "JobRequirment",
            "RequiredQual",
            "tags",
        ]
        for c in text_cols:
            if c not in df.columns:
                df[c] = ""
        df[text_cols] = df[text_cols].fillna("")

        df["__text"] = (
            df["Title"].astype(str)
            + " "
            + df["Company"].astype(str)
            + " "
            + df["Location"].astype(str)
            + " "
            + df["JobDescription"].astype(str)
            + " "
            + df["JobRequirment"].astype(str)
            + " "
            + df["RequiredQual"].astype(str)
            + " "
            + df["tags"].astype(str)
        )

        vectorizer = TfidfVectorizer(stop_words="english", max_features=max_features)
        tfidf = vectorizer.fit_transform(df["__text"])
        similarity = cosine_similarity(tfidf)

        os.makedirs(output_dir, exist_ok=True)
        jobs_path = os.path.join(output_dir, "jobs.pkl")
        sim_path = os.path.join(output_dir, "similarity.pkl")

        # Keep the DataFrame aligned with Job IDs (ordered by id).
        jobs_df = df.drop(columns=["__text"])

        with open(jobs_path, "wb") as f:
            pickle.dump(jobs_df, f)
        with open(sim_path, "wb") as f:
            pickle.dump(similarity, f)

        self.stdout.write(self.style.SUCCESS("Built recommender artifacts:"))
        self.stdout.write(self.style.SUCCESS(f"- {jobs_path}"))
        self.stdout.write(self.style.SUCCESS(f"- {sim_path}"))

