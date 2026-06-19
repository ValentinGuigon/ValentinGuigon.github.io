---
layout: page
title: projects
permalink: /projects/
description: Selected research and personal projects.
nav: true
nav_order: 1
neuro_background: dense
---

{% assign projects_by_year = site.projects | group_by_exp: "project", "project.date_range | split: '-' | first | strip" | sort: "name" | reverse %}

<div class="projects projects-page">

{% if site.projects.size > 0 %}

{% for year_group in projects_by_year %}

<h2 id="{{ year_group.name }}" class="year-heading">{{ year_group.name }}</h2>

{% assign sorted_projects = year_group.items | sort: "title" %}

<div class="project-list">
{% for project in sorted_projects %}
{% include project_card_long.liquid project=project %}
{% endfor %}
</div>
{% endfor %}
{% else %}
<p>No projects published yet.</p>
{% endif %}

</div>
