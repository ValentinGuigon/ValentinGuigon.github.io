---
layout: default
permalink: /posts/
title: posts
nav: true
nav_order: 1
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
---

<div class="post">

{% assign blog_name_size = site.blog_name | size %}
{% assign blog_description_size = site.blog_description | size %}

{% if blog_name_size > 0 or blog_description_size > 0 %}

<div class="header-bar">
<h1>{{ site.blog_name }}</h1>
<h2>{{ site.blog_description | markdownify }}</h2>
</div>
{% endif %}

  <div class="tag-category-container" style="text-align: center; margin: 1rem 0;">
    {% if site.tags.size > 0 %}
      <div class="tag-list" style="margin-bottom: 1rem;">
        {% assign sorted_tags = site.tags | sort %}
        {% for tag in sorted_tags %}
          <a href="{{ tag[0] | slugify | prepend: '/posts/tag/' | relative_url }}">
            <i class="fa-solid fa-hashtag fa-sm"></i> {{ tag[0] }}
          </a>
          {% unless forloop.last %}
            &nbsp;&middot;&nbsp;
          {% endunless %}
        {% endfor %}
      </div>
    {% endif %}

    <!-- Line Separator -->
    {% if site.tags.size > 0 and site.categories.size > 0 %}
      <hr style="margin: 1rem auto; width: 80%;">
    {% endif %}

    {% if site.categories.size > 0 %}
      <div class="category-list" style="margin-top: 1rem;">
        {% assign sorted_categories = site.categories | sort %}
        {% for category in sorted_categories %}
          <a href="{{ category[0] | slugify | prepend: '/posts/category/' | relative_url }}">
            <i class="fa-solid fa-tag fa-sm"></i> {{ category[0] }}
          </a>
          {% unless forloop.last %}
            &nbsp;&middot;&nbsp;
          {% endunless %}
        {% endfor %}
      </div>
    {% endif %}

  </div>

{% assign featured_posts = site.posts | where: "featured", "true" %}
{% if featured_posts.size > 0 %}
<br>

<div class="container featured-posts">
{% assign is_even = featured_posts.size | modulo: 2 %}
<div class="row row-cols-{% if featured_posts.size <= 2 or is_even == 0 %}2{% else %}3{% endif %}">
{% for post in featured_posts %}
<div class="col mb-4">
<a href="{% if (post.external_source == 'medium' or post.external_source == 'substack') and post.external_url %}{{ post.external_url }}{% else %}{{ post.url | relative_url }}{% endif %}" {% if (post.external_source == 'medium' or post.external_source == 'substack') and post.external_url %}target="_blank"{% endif %}>
<div class="card hoverable">
<div class="row g-0">
<div class="col-md-12">
<div class="card-body">
<div class="float-right">
<i class="fa-solid fa-thumbtack fa-xs"></i>
</div>
<h3 class="card-title text-lowercase">{{ post.title }}</h3>
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

  <ul class="post-list">
    {% if page.pagination.enabled %}
      {% assign postlist = paginator.posts %}
    {% else %}
      {% assign postlist = site.posts %}
    {% endif %}

    {% for post in postlist %}
      {% if post.external_source == blank %}
        {% assign read_time = post.content | number_of_words | divided_by: 180 | plus: 1 %}
      {% else %}
        {% assign read_time = post.feed_content | strip_html | number_of_words | divided_by: 180 | plus: 1 %}
      {% endif %}
      {% assign year = post.date | date: "%Y" %}
      {% assign tags = post.tags | join: "" %}
      {% assign categories = post.categories | join: "" %}

      <li>
        {% if post.thumbnail %}
          <div class="row">
            <div class="col-sm-9">
        {% endif %}
        <h3>
          {% if (post.external_source == 'medium' or post.external_source == 'substack') and post.external_url %}

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
<p>{{ post.description }}</p>
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
{{ post.date | date: '%B %d, %Y' }}
{% if post.external_source and post.external_url %}
  &nbsp; &middot; &nbsp; {{ post.external_source | capitalize }}
{% endif %}
</p>
<p class="post-tags">
<a href="{{ year | prepend: '/posts/' | prepend: site.baseurl}}">
<i class="fa-solid fa-calendar fa-sm"></i> {{ year }}
</a>

          {% if tags != "" %}
            &nbsp; &middot; &nbsp;
            {% for tag in post.tags %}
              <a href="{{ tag | slugify | prepend: '/posts/tag/' | prepend: site.baseurl}}">
                <i class="fa-solid fa-hashtag fa-sm"></i> {{ tag }}</a>
              {% unless forloop.last %}
                &nbsp;
              {% endunless %}
            {% endfor %}
          {% endif %}

          {% if categories != "" %}
            &nbsp; &middot; &nbsp;
            {% for category in post.categories %}
              <a href="{{ category | slugify | prepend: '/posts/category/' | prepend: site.baseurl}}">
                <i class="fa-solid fa-tag fa-sm"></i> {{ category }}</a>
              {% unless forloop.last %}
                &nbsp;
              {% endunless %}
            {% endfor %}
          {% endif %}
        </p>

        {% if post.thumbnail %}
            </div>
            <div class="col-sm-3">
              <img class="card-img" src="{{post.thumbnail | relative_url}}" style="object-fit: cover; height: 90%" alt="image">
            </div>
          </div>
        {% endif %}
      </li>
    {% endfor %}

  </ul>

{% if page.pagination.enabled %}
{% include pagination.liquid %}
{% endif %}

</div>
