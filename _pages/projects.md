---
layout: page
title: projects
permalink: /projects/
description: Selected research, technical and personal projects.
nav: true
nav_order: 1
neuro_background: dense
toc:
  sidebar: right
wide_toc_content: true
custom_toc:
  - label: Research projects
    id: research-projects
  - label: Methods, software, and lab infrastructure
    id: methods-software-and-lab-infrastructure
  - label: Personal and research tools, AI experiments, and technical projects
    id: personal-and-research-tools-ai-experiments-and-technical-projects
---

{% assign project_sections = "Research projects|Methods, software, and lab infrastructure|Personal and research tools, AI experiments, and technical projects" | split: "|" %}

<div class="projects projects-page">

{% if site.projects.size > 0 %}

{% for section_name in project_sections %}
{% assign section_projects = site.projects | where: "section", section_name %}
{% if section_projects.size > 0 %}
<h2 id="{{ section_name | slugify }}" class="year-heading">{{ section_name }}</h2>

{% assign projects_by_year = section_projects | group_by_exp: "project", "project.sort_year" | sort: "name" | reverse %}
<div class="project-list">
{% for year_group in projects_by_year %}
{% assign sorted_projects = year_group.items | sort: "sort_rank" %}
{% for project in sorted_projects %}
{% include project_card_long.liquid project=project %}
{% endfor %}
{% endfor %}
</div>
{% endif %}
{% endfor %}
{% else %}
<p>No projects published yet.</p>
{% endif %}

</div>
