# Vault Pre-Run Report Generator

Generates a report on a project directory saying what Vault will delete when run on that project.

---

To change project or soft-deletion threshold, the first few lines in `report.py` can be changed.

```python
PROJECT_DIR = "/lustre/scratch114/projects/crohns"
DELETION_THRESHOLD = 10  # Days
```

Ensure the `glob` search is also looking for the correct volume

```python
wrstat_reports = glob.glob(...)
```

---

Run as a `bsub` job using `run.sh`. That script also specifies the output file, with `%J` being the job number. The output is valid markdown (`.md`)