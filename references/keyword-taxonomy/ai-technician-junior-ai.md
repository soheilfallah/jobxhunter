# Keyword taxonomy — AI / ML technician & junior AI engineer (UK, entry–mid)

Use this as a KEYWORD PALETTE: match JD terms to profile evidence; flag missing must-haves as gaps.
The AI/ML field over-rewards buzzwords, so a framework or model name with no project behind it is
the first thing an interviewer probes.

**Weighting:** `W3` TITLE-MATCH · `W2` MUST-HAVE · `W1` NICE-TO-HAVE · `[KO]` common KNOCKOUT.

### CRITICAL: junior vs senior vocabulary split
Reach for the JUNIOR tier at entry/mid level. The senior tier below is for READING senior JDs and
recognising the ceiling — do NOT project senior terms onto a junior candidate's CV unless the
profile genuinely evidences them.
- **JUNIOR / entry–mid core:** Python, scikit-learn, pandas, NumPy, SQL, Jupyter notebooks,
  Matplotlib, dashboards (Tableau/Power BI), TensorFlow/PyTorch/Keras basics, regression &
  classification, data cleaning. A quantitative Master's is often the gate.
- **SENIOR ceiling (recognise, don't reach):** MLOps, CI/CD for models, containerisation
  (Docker/Kubernetes), cloud-native (AWS/GCP/Azure), model serving/monitoring/real-time
  inference, GenAI/agentic (LangChain/LangGraph, RAG, vector DBs, prompt engineering,
  multi-agent), HPC, C/C++, Ray/Polars/Dagster/Prefect.

---

## HARD SKILLS
### Junior / entry–mid (reach here)
- `W2` Machine learning (ML) — supervised: regression, classification
- `W2` Data cleaning / transformation / wrangling of large datasets
- `W2` Model training, testing & evaluation — train/test split, cross-validation, metrics
- `W2` Feature engineering
- `W2` SQL querying & optimisation on relational databases
- `W1` Statistics & probability; linear algebra (strong maths/stats background)
- `W1` Data pipelines (basic ETL — Extract, Transform, Load)
- `W1` NLP (Natural Language Processing) — text classification basics
- `W1` Computer vision (CV) — image classification basics
- `W1` Reinforcement learning (RL) — awareness/basics
- `W1` Dashboarding & data visualisation
- `W1` Model deployment (basic) — packaging a model behind an API

### Senior ceiling (recognise only)
- `W1` MLOps (Machine Learning Operations) — CI/CD for models, testing, monitoring, deployment
- `W1` Full ML lifecycle & production model serving; real-time / low-latency inference
- `W1` GenAI (Generative AI) / agentic systems — autonomous agents, tool-use, memory architectures
- `W1` RAG (Retrieval-Augmented Generation); vector databases; prompt engineering; multi-agent
- `W1` LLM (Large Language Model) pipelines & fine-tuning
- `W1` Responsible AI — guardrails, hallucination mitigation
- `W1` Distributed / big-data processing; HPC (High-Performance Computing)

## TOOLS / TECH
### Junior (reach here)
- `W2` Python — universal must-have across the whole family
- `W2` scikit-learn — classical ML
- `W2` pandas — dataframes; `W2` NumPy — numerical arrays
- `W2` SQL (Structured Query Language) — and NoSQL awareness
- `W1` Jupyter notebooks
- `W1` PyTorch · TensorFlow · Keras — deep-learning frameworks (basics)
- `W1` Matplotlib — plotting; `W1` Tableau · Power BI — dashboards
- `W1` Git / GitHub — version control
- `W1` Big-data familiarity — Hadoop, Spark, Kafka (named in entry JDs as "familiarity")
### Senior ceiling (recognise only)
- `W1` Docker · Kubernetes (K8s) — containerisation/orchestration
- `W1` AWS · GCP (Google Cloud Platform) · Azure — incl. Azure OpenAI, Azure ML, Cognitive Services
- `W1` LangChain · LangGraph · Hugging Face — LLM/agent frameworks
- `W1` Vector DBs (Pinecone, FAISS, Weaviate, Chroma)
- `W1` Ray · Polars · Dagster · Prefect · SciPy · Plotly/Dash — advanced Python ML stack
- `W1` Linux; CI/CD tooling; MLflow / Weights & Biases (experiment tracking)

## CERTIFICATIONS / LICENCES
- `W2 [KO]` Degree gate — Master's (or strong Bachelor's) in Data Science, Statistics, Computer
  Science, Maths, or related quantitative field. One live entry role states Master's as a "MUST".
  Bootcamp accepted "or equivalent" in some posts.
- `W1` Cloud/vendor certs — AWS Certified ML, Azure AI Engineer Associate, GCP ML Engineer,
  TensorFlow Developer, Databricks (mostly senior differentiators, not junior gates).
- `W1` Open-source ML contributions — a preferred signal at entry level.
- `W2 [KO]` UK right-to-work / UK-based — visa status routinely asked; "no sponsorship" common.
- `W1 [KO]` Immediate start — stated in some entry postings.

## GENUINE SOFT SKILLS
(Include only when JD-named and profile-evidenced.)
- `W2` Communication to non-technical stakeholders — explaining models/results
- `W2` Problem-solving — analytical, structured
- `W1` Independent + collaborative working; partnering with engineering/product teams
- `W1` Continuous learning — keeping current with the field
- `W1` Curiosity / initiative — thrives in greenfield (startup register)

## TITLE VARIANTS
`W3` on title match:
- Junior Machine Learning Engineer / ML Engineer / Machine Learning Engineer
- Junior AI Engineer / AI Engineer
- Junior Data Scientist / Data Scientist (early-career)
- ML Ops Engineer (junior) — if genuinely evidenced
- AI/ML Developer / Applied ML Engineer (junior)
- NLP Engineer (junior) / Computer Vision Engineer (junior)
- AI Technician / ML Research Assistant
- Data Science Intern / Graduate Data Scientist

---

## Junior-vs-senior decision cues (which tier to reach for)
Reach JUNIOR when the JD shows any of: "junior/graduate/trainee", "assist/support building",
"training provided", a taught-Master's as the main gate, a stack of scikit-learn/pandas/SQL/
notebooks with no deployment ownership, "0–2 years". Reach SENIOR-ceiling ONLY when the JD
demands ownership: "design/own the architecture", "productionise", MLOps/CI-CD for models,
cloud-native serving, agentic/RAG systems built from scratch, "mentor engineers", "5+ years",
"staff/lead/principal". If the profile is junior but the JD is senior, flag likely out-of-scope
in jd-analysis (`eval_eligible: false`) rather than stretching thin evidence to senior terms.

Common junior trap: an entry JD LISTS senior tools as "nice to have" (e.g. Docker/Kubernetes on a
junior ML role). Treat these as `W1` desirables — include only if genuinely evidenced; their
absence must never block the match.

## Notes for the tailorer
- Detect the JD's level FIRST (see jd-analysis.md §2). If entry/mid, build the CV from the junior
  tier; if the JD is senior (MLOps/cloud/agentic ownership, "5+ years", "lead/staff"), flag it as
  likely out of scope rather than stretching a junior profile to fit.
- Python is non-negotiable — surface it prominently whenever present.
- Agency posts over-title and duplicate paragraphs; judge level by the actual stack, not the title.
- Always pair acronyms: ML (machine learning), NLP (natural language processing), CV (computer
  vision), RAG (retrieval-augmented generation), MLOps, LLM (large language model), GCP (Google
  Cloud Platform in this family — NOT Good Clinical Practice), ETL (extract-transform-load).

## Sources
- Live JDs: `kb-build/live-jds/ai-ml.md` (Junior ML Engineer — Python/TensorFlow/PyTorch/
  scikit-learn/SQL/Tableau/Power BI, Master's MUST; AI Engineer — LangChain/HF/PyTorch/vector DBs/
  agentic; senior Longshot & Capital One roles = taxonomy-ceiling evidence only).
- O*NET 15-2051.00 Data Scientists; 15-1252.00 Software Developers: https://www.onetonline.org
- ESCO — "data scientist", "machine learning" skills cluster: https://esco.ec.europa.eu
- LinkedIn skills taxonomy (ML/AI cluster): Python, scikit-learn, PyTorch, TensorFlow, NLP, deep
  learning, MLOps, LangChain.
