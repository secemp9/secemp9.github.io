---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: blog
title: secemp Blog
---

{% assign N = 5 %}
{% assign sorted_posts = site.posts | sort: 'date' | reverse %}
{% assign featured = sorted_posts[0] %}
{% assign rest = sorted_posts | slice: 1, N %}

{% if featured %}
<div class="featured-post">
  <a class="card-link" href="{{ featured.url | relative_url }}" aria-label="Read featured post: {{ featured.title }}">
    <div class="card-content">
      <div class="card-title">{{ featured.title }}</div>
      <div class="card-date">{{ featured.date | date: "%B %d, %Y" }}</div>
      <div class="card-excerpt">{{ featured.excerpt | strip_html | truncate: 180 }}</div>
      {% if featured.tags and featured.tags.size > 0 %}
      <div class="card-tags">
        {% for tag in featured.tags %}<span class="card-tag">{{ tag }}</span>{% endfor %}
      </div>
      {% endif %}
    </div>
  </a>
</div>
{% endif %}

<div class="blog-list">
  {% for post in rest %}
    <div class="blog-card">
      <a class="card-link" href="{{ post.url | relative_url }}">
        <div class="card-content">
          <div class="card-title">{{ post.title }}</div>
          <div class="card-date">{{ post.date | date: "%B %d, %Y" }}</div>
          <div class="card-excerpt">{{ post.excerpt | strip_html | truncate: 120 }}</div>
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
