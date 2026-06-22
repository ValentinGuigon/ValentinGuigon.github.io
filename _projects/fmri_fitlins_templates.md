---
title: FitLINS-based fMRI analysis package
date_range: 2025-2026
context: UMD SLD Lab
section: Methods, software, and lab infrastructure
sort_year: 2025
sort_rank: 3
tags:
  - fMRI
  - FitLINS
  - Nilearn
  - SLURM
kind: methods
description_paragraphs:
  - I created a Python-based fMRI analysis package that wraps FitLINS, Nilearn, and SLURM into a more usable workflow for the lab. The package runs GLM analyses from fMRIPrep outputs, manages model configuration, patches reports, generates statistical maps, builds PDF summaries, and indexes analyses by task group.
  - The goal is to make fMRI modeling easier for RAs and collaborators without losing traceability. Each analysis remains linked to its model files, contrasts, execution logs, statistical outputs, and reports.
links:
  - label: Github
    url: https://github.com/ValentinGuigon/Py_fMRI_pipeline_template
---
