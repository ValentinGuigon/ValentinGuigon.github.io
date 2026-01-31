---
layout: page
permalink: /publications/
title: publications
description: Publications in reversed chronological order.
nav: true
nav_order: 1
toc:
  sidebar: right
---

<!-- _pages/publications.md -->
<div class="publications">

<h3>Published & In Press</h3>
{% bibliography --query @*[status=in_press] %}
{% bibliography --query @*[status=published] %}

<h3>Pre-prints</h3>
{% bibliography --query @*[status=preprint] %}

<h3>In preparation</h3>
{% bibliography --query @*[status=in_preparation] --group_by none %}

</div>
