---
layout: default
permalink: /posts/
title: posts
description: A place for non-academic writing.
nav: true
nav_order: 2
pagination:
  enabled: true
  collection: posts
  permalink: /page/:num/
  per_page: 25
  sort_field: date
  sort_reverse: true
  trail:
    before: 1
    after: 3
toc:
  sidebar: right
---

<div class="post">
  <header class="post-header">
    <h1 class="post-title">{{ page.title }}</h1>
    <p class="post-description">{{ page.description }}</p>
  </header>

{% assign featured_posts = site.posts | where: "featured", "true" %}
{% if featured_posts.size > 0 %}
<br>

<div class="container featured-posts">
{% assign is_even = featured_posts.size | modulo: 2 %}
<div class="row row-cols-{% if featured_posts.size <= 2 or is_even == 0 %}2{% else %}3{% endif %}">
{% for post in featured_posts %}
<div class="col mb-4">
<a href="{% if post.external_url and post.external_source == 'medium' or post.external_url and post.external_source == 'substack' %}{{ post.external_url }}{% else %}{{ post.url | relative_url }}{% endif %}" {% if post.external_url and post.external_source == 'medium' or post.external_url and post.external_source == 'substack' %}target="_blank"{% endif %}>
<div class="card hoverable">
<div class="row g-0">
<div class="col-md-12">
<div class="card-body">
<div class="float-right">
<i class="fa-solid fa-thumbtack fa-xs"></i>
</div>
<h3 class="card-title text-lowercase" data-toc-skip>{{ post.title }}</h3>
<p class="card-text">{{ post.description }}</p>
{% if post.external_source == blank %}
{% assign read_time = post.content | number_of_words | divided_by: 180 | plus: 1 %}
{% else %}
{% assign read_time = post.feed_content | strip_html | number_of_words | divided_by: 180 | plus: 1 %}
{% endif %}
{% assign year = post.date | date: "%Y" %}
<p class="post-meta">
Created in {{ post.date | date: '%B %d, %Y' }}
{% if post.last_updated %}, last updated in {{ post.last_updated | date: '%B %d, %Y' }}{% endif %}
{% if post.starting_date %}, Starting date: {{ post.starting_date | date: '%B %d, %Y' }}{% endif %}
{% if post.update_date %}, Updated on: {{ post.update_date | date: '%B %d, %Y' }}{% endif %}
{% if post.status %}, Status: {{ post.status }}{% endif %}
{% if post.confidence %}, Confidence: {{ post.confidence }}{% endif %}
{% if post.effort %}, Effort: {{ post.effort }}{% endif %}
<br>
{{ read_time }} min read &nbsp; &middot; &nbsp;
<a href="{{ year | prepend: '/posts/' | prepend: site.baseurl}}">
<i class="fa-solid fa-calendar fa-sm"></i> {{ year }}
</a>
{% if post.external_source and post.external_url %}
&nbsp; &middot; &nbsp; {{ post.external_source | capitalize }}
{% endif %}
</p>
</div>
</div>
</div>
</div>
</a>
</div>
{% endfor %}
</div>
</div>
<hr>
{% endif %}

{% assign postlist = site.posts %}
{% assign posts_by_year = postlist | group_by_exp: "post", "post.date | date: '%Y'" | sort: "name" | reverse %}

{% for year_group in posts_by_year %}

<h2 id="{{ year_group.name }}" class="year-heading" style="margin-top: 1.5rem;">{{ year_group.name }}</h2>
<ul class="post-list">
{% for post in year_group.items %}
{% if post.external_source == blank %}
{% assign read_time = post.content | number_of_words | divided_by: 180 | plus: 1 %}
{% else %}
{% assign read_time = post.feed_content | strip_html | number_of_words | divided_by: 180 | plus: 1 %}
{% endif %}
{% assign year = post.date | date: "%Y" %}

<li>
{% if post.thumbnail %}
<div class="row">
<div class="col-sm-9">
{% endif %}
<h3 data-toc-skip>
{% if post.external_url and post.external_source == 'medium' or post.external_url and post.external_source == 'substack' %}
<a class="post-title" href="{{ post.external_url }}" target="_blank">{{ post.title }}</a>
<svg width="2rem" height="2rem" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
<path d="M17 13.5v6H5v-12h6m3-3h6v6m0-6-9 9" class="icon_svg-stroke" stroke="#999" stroke-width="1.5" fill="none" fill-rule="evenodd" stroke-linecap="round" stroke-linejoin="round"></path>
</svg>
{% elsif post.redirect == blank %}
<a class="post-title" href="{{ post.url | relative_url }}">{{ post.title }}</a>
{% elsif post.redirect contains '://' %}
<a class="post-title" href="{{ post.redirect }}" target="_blank">{{ post.title }}</a>
<svg width="2rem" height="2rem" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
<path d="M17 13.5v6H5v-12h6m3-3h6v6m0-6-9 9" class="icon_svg-stroke" stroke="#999" stroke-width="1.5" fill="none" fill-rule="evenodd" stroke-linecap="round" stroke-linejoin="round"></path>
</svg>
{% else %}
<a class="post-title" href="{{ post.redirect | relative_url }}">{{ post.title }}</a>
{% endif %}
</h3>

{% assign preview = "" %}
{% if post.feed_content and post.feed_content != "" %}
{% assign preview = post.feed_content | strip_html | truncatewords: 50 %}
{% elsif post.description and post.description != "" %}
{% assign preview = post.description %}
{% elsif post.content and post.content != "" %}
{% assign preview = post.content | strip_html | truncatewords: 50 %}
{% endif %}
{% if preview != "" %}

<p>{{ preview }}</p>
{% endif %}

<p class="post-meta">
{{ post.date | date: '%B %d, %Y' }}
{% if post.last_updated %}, last updated in {{ post.last_updated | date: '%B %d, %Y' }}{% endif %}
{% if post.status %}, Status: {{ post.status }}{% endif %}
{% if post.confidence %}, Confidence: {{ post.confidence }}{% endif %}
{% if post.effort %}, Effort: {{ post.effort }}{% endif %}
&nbsp; &middot; &nbsp; {{ read_time }} min read
{% if post.external_source and post.external_url %}
&nbsp; &middot; &nbsp; {{ post.external_source | capitalize }}
{% endif %}
</p>

{% if post.thumbnail %}

</div>
<div class="col-sm-3">
<img class="card-img" src="{{ post.thumbnail | relative_url }}" style="object-fit: cover; height: 90%" alt="image">
</div>
</div>
{% endif %}
</li>
{% endfor %}
</ul>
{% endfor %}

</div>
