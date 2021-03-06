# Vault Pre-Run Report Generator

Generates a report on a project directory saying what Vault will delete when run on that project.

Provide the absolute path to the project directory of interest.

NB: Only /lustre paths are currently supported, and you must use the "real"
path, not a symlink path. eg.:
`python report.py $(realpath /lustre/scratch123/projects/foo)`

`run.sh` does this realpath conversion for you.

---

To change the soft-deletion threshold, `report.py` must be edited:

```python
DELETION_THRESHOLD = 10  # Days
```

Ensure the `glob` search is also looking for the correct volume:

```python
wrstat_reports = glob.glob(...)
```

---

Run as a `bsub` job using `run.sh`, providing the project directory.

That script also specifies the output file, with `%J` being the job number.

The output is valid markdown (`.md`), and ends up in /nfs/hgi/vault/pre_reports.
You should manually clean up this directory once you're done with your report.

Note that it currently incorrectly reports that empty directories and symlinks
will be deleted, regardless of their age.

---

To run the test script:

```
python3 -m unittest discover
```
