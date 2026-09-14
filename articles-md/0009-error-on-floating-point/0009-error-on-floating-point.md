---
title: 컴퓨터에서 실수형 표현에 따른 error
date: 2026.09.14
tag: Simulation
draft: false
math: true
# syndication: dev.to, Hashnode
# slug: custom-url-slug
# scripts: /static/js/demo-bvh.js
# styles: /static/css/demo-bvh.css
---

Justin Solomon 교수님의 Numerical Algorithms 교재를 보며 error를 공부해본다.

## Floating Point

컴퓨터에서 실수는 IEEE 754에서의 규칙을 따라 구현하게 된다.
`double`형은 sign 1 bit + mantissa 54 bit + exponent 11 bit를 사용한다.
`float`형은 mantissa만 22 bit로 줄여 사용한다.
이 때, 이 floating point로 저장된 값들의 연산을 수행할 때 이 비트에 담기지 못하는 부분은 error가 되어 연산 과정에서 지속적으로 누적된다.

이러한 실수형 사이의 연산에서 error의 scale에 영향을 주는 부분은 exponent의 크기이다.
작은 floating point를 예로 들어보자.
어떤 floating point가 mantissa 2 bit + exponent 2 bit로 구성된다고 하면 아래의 형태를 생각해볼 수 있다.

$$
1.\square\square_{(2)}\times 2^{\square_{\text{sign}}\square}
$$

여기서 나올 수 있는 가능한 수의 범위를 간단히 생각해보면,

| mantissa \ exponent | $\times {2^{-1}}_{(10)}$ | $\times {2^{0}}_{(10)}$ | $\times {2^{1}}_{(10)}$ |
| ------------------- | ------------------------ | ----------------------- | ----------------------- |
| $1.00_{(10)}$       | 0.50                     | 1.00                    | 2.00                    |
| $1.25_{(10)}$       | 0.625                    | 1.25                    | 2.50                    |
| $1.50_{(10)}$       | 0.75                     | 1.50                    | 3.00                    |
| $1.75_{(10)}$       | 0.875                    | 1.75                    | 3.5                     |

Exponent가 커질수록 mantissa에 따른 값 사이 거리가 커진다.
즉, 큰 exponent의 값들을 다루면 연산의 정확도가 떨어질 수 있다는 것이다.

<!-- 어떤 실수 $x, y$의 에러를 $\epsilon_x,\epsilon_y$라고 하자.
이 실수를 에러와 함께 $(x, \epsilon_x)$라고 표현할 때, 각 연산에 대해 아래처럼 정의된다.

- $(x,\epsilon_x)+(y,\epsilon_y)=(x+y,\epsilon_x+\epsilon_y+\epsilon_{x+y})$
- $(x,\epsilon_x)-(y,\epsilon_y)=(x-y,\epsilon_x+\epsilon_y+\epsilon_{x-y})$
- $(x,\epsilon_x)\times(y,\epsilon_y)=(x\times y,|y|\epsilon_x+|x|\epsilon_y+\epsilon_x\epsilon_y+\epsilon_{x\times y})$ -->

### Translate to Origin

하나의 사례를 보자.
Point cloud를 입력으로 받았는데 이 입력 위치가 원점에서 멀리 떨어져있다고 하자.
이 값들은 exponent가 클 것이다.
이 상태에서 연산을 하는 것보다 이 point cloud들을 원점으로 이동시키는 것이 exponent를 줄여 error를 줄일 수 있을 것이다.

### Scale the data

또 하나의 사례를 보자.
간격이 큰 sparse point cloud를 입력으로 받았다고 하자.
이 점들은 원점 중심으로 위치해있다고 해도 point 사이의 벡터를 구하는 등의 연산을 취하면 이 벡터 역시 exponent가 큰 값으로 나오므로 error가 큰 벡터가 될 것이다.

따라서 point cloud를 받으면 원점 중심에 적절한 스케일 값을 가지고 있어야 error를 최대한 적게 연산을 할 수 있을 것이다.
