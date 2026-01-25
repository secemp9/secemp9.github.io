---
layout: blog
title: All Posts
permalink: /posts/
---

<div class="section-header">
  <div class="section-title">> All Posts</div>
</div>

{% assign sorted_posts = site.posts | sort: 'date' | reverse %}

<div class="blog-list">
  {% for post in sorted_posts %}
    <div class="blog-card">
      <a class="card-link" href="{{ post.url | relative_url }}">
        <div class="card-content">
          <div class="card-date">{{ post.date | date: "%Y-%m-%d" }}</div>
          <div class="card-title">{{ post.title }}</div>
          <div class="card-excerpt">{{ post.excerpt | strip_html | truncate: 140 }}</div>
          {% if post.tags and post.tags.size > 0 %}
          <div class="card-tags">
            {% for tag in post.tags %}<span class="card-tag">{{ tag }}</span>{% endfor %}
          </div>
          {% endif %}
        </div>
      </a>
    </div>
  {% endfor %}
</div> 