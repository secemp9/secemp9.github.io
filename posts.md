---
layout: blog
title: All Posts
permalink: /posts/
---

<ul class="all-posts-list">
{% assign sorted_posts = site.posts | sort: 'date' | reverse %}
{% for post in sorted_posts %}
  <li>
    {{ post.date | date: "%Y-%m-%d" }} - <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
  </li>
{% endfor %}
</ul> 