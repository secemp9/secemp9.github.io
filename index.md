---
layout: blog
title: secemp Blog
---

<div class="hero">
  <div class="hero-content">
    <div class="hero-greeting">Hi, I'm</div>
    <h1 class="hero-name"><span class="highlight">secemp</span></h1>
    <p class="hero-bio">ML researcher and pragmatic optimist. Writing about ideas and scaling.</p>
    <a href="mailto:secemp9@gmail.com" class="corner-btn">
      <span class="corner tl"></span>
      <span class="corner tr"></span>
      <span class="corner bl"></span>
      <span class="corner br"></span>
      Contact
    </a>
  </div>
</div>

<div class="section-header">
  <div class="section-title">> Latest Posts</div>
  <a href="/posts/" class="section-link">See all posts</a>
</div>

{% assign N = 6 %}
{% assign sorted_posts = site.posts | sort: 'date' | reverse %}
{% assign posts = sorted_posts | slice: 0, N %}

<div class="blog-list">
  {% for post in posts %}
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
