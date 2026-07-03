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
  - id: peer-reviewed
    label: peer-reviewed
  - id: under-review
    label: under review
  - id: in-preparation
    label: in preparation
---

<!-- _pages/publications.md -->
<div class="publications">

<h3 id="peer-reviewed">Peer-Reviewed</h3>
{% bibliography --query @*[status=in_press || status=published || status=accepted] %}

<h3 id="under-review">Under Review</h3>
{% bibliography --query @*[status=under_review] --group_by none %}

<h3 id="in-preparation">In preparation</h3>
{% bibliography --query @*[status=in_preparation] --group_by none %}

</div>
