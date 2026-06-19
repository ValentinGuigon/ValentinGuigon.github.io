---
layout: page
permalink: /publications/
title: publications
description: Publications in reversed chronological order.
nav: true
nav_order: 2
neuro_background: sparse
toc:
  sidebar: right
wide_toc_content: true
custom_toc:
  - id: published-in-press
    label: published & in press
  - id: pre-prints
    label: pre-prints
  - id: in-preparation
    label: in preparation
---

<!-- _pages/publications.md -->
<div class="publications">

<h3 id="published-in-press">Published & In Press</h3>
{% bibliography --query @*[status=in_press] %}
{% bibliography --query @*[status=published] %}

<h3 id="pre-prints">Pre-prints</h3>
{% bibliography --query @*[status=preprint] %}

<h3 id="in-preparation">In preparation</h3>
{% bibliography --query @*[status=in_preparation] --group_by none %}

</div>
