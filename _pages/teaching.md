---
layout: page
title: teaching
permalink: /teaching/
description: Materials for courses taught.
nav: true
nav_order: 6
display_years: [2025, 2023]
display_categories: ["UCBL1", "Summer school Cortecs", "UMD"]
horizontal: false
---

<div class="projects">

{% assign all_teaching = site.teaching %}

{% for y in page.display_years %}
<a id="{{ y }}" href=".#{{ y }}">
<h2 class="category">{{ y }}</h2>
</a>

{% assign teaching_in_year = all_teaching | where: "year", y %}

{% if site.enable_project_categories and page.display_categories %}
{% for c in page.display_categories %}
{% assign teaching_in_cat = teaching_in_year | where: "category", c %}
{% assign sorted_teaching = teaching_in_cat | sort: "importance" %}

      {% if sorted_teaching and sorted_teaching.size > 0 %}
        <a id="{{ y }}-{{ c | slugify }}" href=".#{{ y }}-{{ c | slugify }}">
          <h3 class="category">{{ c }}</h3>
        </a>

        {% if page.horizontal %}
          <div class="container">
            <div class="row row-cols-1 row-cols-md-2">
              {% for item in sorted_teaching %}
                {% include teaching_horizontal.liquid item=item %}
              {% endfor %}
            </div>
          </div>
        {% else %}
          <div class="row row-cols-1 row-cols-md-3">
            {% for item in sorted_teaching %}
              {% include teaching.liquid item=item %}
            {% endfor %}
          </div>
        {% endif %}
      {% endif %}
    {% endfor %}

{% else %}
{% assign sorted_teaching = teaching_in_year | sort: "importance" %}
<div class="row row-cols-1 row-cols-md-3">
{% for item in sorted_teaching %}
{% include teaching.liquid item=item %}
{% endfor %}
</div>
{% endif %}

{% endfor %}

</div>
