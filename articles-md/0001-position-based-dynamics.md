---
title: 힘이 아닌 위치에 기반한 역학 - PBD, PD, XPBD
date: 2026.09
tag: Simulation
draft: true
math: true
# syndication: dev.to, Hashnode
# slug: custom-url-slug
# scripts: /static/js/demo-bvh.js
# styles: /static/css/demo-bvh.css
---

지난 여름, 랩에서 Position Based Dynamics(이하 PBD)와 Projective Dynamics를 묶어 위치 기반 역학을 주제로 발표했다. 이후 개인적으로 eXtended PBD(이하 XPBD)까지 읽으면서 위치 기반의 계열들이 물리적이지 않다거나 정확하지 않다는 선입견을 해소할 수 있었다. 본 글에서는 이러한 내 생각을 정리한다.

## XPBD
