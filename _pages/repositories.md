---
layout: page
permalink: /repositories/
title: repositories
description: Research code, methods templates, and scientific software.
nav: true
nav_order: 4
---

This page gathers a selected set of repositories tied to my work in computational neuroscience, computational psychiatry, NeuroAI, reproducible research workflows, fMRI methods, and scientific programming. It is not intended as an exhaustive mirror of my GitHub activity, but as a curated view of the projects most relevant to my research profile.

## Selected repositories

{% if site.data.repositories.github_repos %}

<div class="repositories d-flex flex-wrap flex-md-row flex-column justify-content-between align-items-center">
  {% for repo in site.data.repositories.github_repos %}
    {% include repository/repo.liquid repository=repo %}
  {% endfor %}
</div>

{% endif %}
