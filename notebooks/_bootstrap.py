# Databricks notebook source
"""Shared Databricks notebook bootstrap for job_watch.

Run from notebooks with:

# MAGIC %run ./_bootstrap

It makes `src/job_watch` importable and creates the shared `DB` object.
"""

# COMMAND ----------

import os
import sys


def add_project_src_to_path() -> None:
    """Make src/job_watch importable in Databricks Repos/Workspace and local runs."""
    roots = []

    def add_root(path):
        if path and path not in roots:
            roots.append(path)

    add_root(os.getcwd())
    if "__file__" in globals():
        add_root(os.path.dirname(os.path.abspath(__file__)))

    try:
        notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
        add_root(os.path.dirname("/Workspace" + notebook_path))
    except Exception:
        pass

    for root in list(roots):
        add_root(os.path.dirname(root))
        if os.path.basename(root) == "notebooks":
            add_root(os.path.dirname(root))

    for root in roots:
        candidate = os.path.abspath(os.path.join(root, "src"))
        if candidate not in sys.path and os.path.exists(os.path.join(candidate, "job_watch")):
            sys.path.insert(0, candidate)
            return


add_project_src_to_path()

from job_watch.database import JobWatchDatabase

DB = JobWatchDatabase()
