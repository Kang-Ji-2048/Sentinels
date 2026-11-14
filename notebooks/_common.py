# Databricks notebook source
# Shared setup, pulled into other notebooks with %run ./_common
import os, sys
repo_root = os.path.dirname(os.getcwd())  # notebooks/ lives one level below the repo root
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

CATALOG, SCHEMA = "workspace", "sentinels"
T = lambda name: f"{CATALOG}.{SCHEMA}.{name}"
