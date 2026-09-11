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

지난 여름, 랩에서 Position Based Dynamics(이하 PBD)와 Projective Dynamics를 묶어 위치 기반 역학을 주제로 발표했다. 이후 개인적으로 eXtended PBD(이하 XPBD)까지 읽으면서 위치 기반 계열 시뮬레이션들이 물리적 정확성과 제어성, 안정성을 어떻게 trade-off하는지 정리해보고자 한다.

> 참고 문헌:
>
> - Position Based Dynamics, Müller et al., VRIPHYS, 2006
> - XPBD: Position-Based Simulation of Compliant Constrained Dynamics, Macklin et al., MIG, 2016
> - Projective Dynamics: Fusing Constraint Projections for Fast Simulation, Bouaziz et al., ACM ToG 2014
> - Primal Extended Position Based Dynamics for Hyperelasticity, Chen et al., MIG 2023

## 기존 force-based dynamics나 impulse-based dynamics의 문제점

Force-based dynamics는 힘이나 퍼텐셜을 모델링하고 여기서 가속도 -> 속도 -> 위치의 순서로 적분하여 답을 얻는 계열의 시스템의 갖는다. 그러나 이들의 문제는 우리가 얻어야 하는 위치 정보들이 안정적으로 얻어지는 지 쉽게 알기 어렵다. 예를 들면, Baraff and Witkin의 Large Steps in Cloth Simulation(SIGGRAPH, 1998)에서 모델링한 방식처럼 옷감의 internal energy가 force로 통합되면서 속도 변화량에 대한 식을 풀면, 이 속도가 안정적으로 계산되었는지는 별도로 검사해야 한다. 즉, 구해지는 답의 안정성이 보장되지 않는다. 또한 시뮬레이션을 조작하고자 하면 초기값을 적절히 튜닝해야 하므로 고역이 아닐 수가 없다.

Impulse-based dynamics는 충격량을 통해 직접적인 속도의 변화량을 알 수 있어 위치의 변화량을 아는 것과 크게 다르지 않게 설계할 수 있다. 그러나 이는 주로 강체의 시뮬레이션에서 사용된다.

즉, 변형체의 시뮬레이션에서 안정성이나 제어성을 얻는 것은 위의 방법론으로는 어려움이 있다. Position-based dynamics는 이러한 문제를 해결할 수 있다. Müller의 2006년 PBD 논문 이전에도 유사한 방법들은 존재했으나 이들은 모두 특정 경우에 한정되는 특징을 가졌다. Müller는 이를 보다 확장시켜 여러 경우에 위치 기반의 역학을 적용할 수 있도록 기반을 닦은 연구를 발표했다.

## PBD

옷감의 예시를 보자. 옷감은 대표적인 변형체로 변형되면서 발생하는 internal force를 모델링해야 시뮬레이션할 수 있다. PBD에서는 이러한 internal force를 파티클 간 위치 관계에 대한 제약 조건(constraint)으로 모델링하였다. 이로써 옷감 내부에 존재하는 internal force를 적절한 constraint의 형태로 두면 옷감을 시뮬레이션할 수 있다.

위치 $\mathbf x$, 속도 $\mathbf v$, 질량 $\mathbf M$의 inverse $\mathbf W=\mathbf M^{-1}$이라 할 때, $\Delta t$의 timestep으로 시뮬레이션하면, 알고리즘은 아래와 같다.

1. $\mathbf v \gets \mathbf v + \Delta t \mathbf {Wf}_{\text{ext}}(\mathbf x)$.
2. Damp $\mathbf{v}$.
3. $\mathbf{p}\gets \mathbf{x}+\Delta t \mathbf{v}$.
4. Generate collision constraints on $\mathbf{x}\to \mathbf{p}$.
5. For loop,
   1. Project constraints.
      $\Delta \mathbf{p}=-s\mathbf{W}\nabla_{\mathbf{p}}C_{j}(\mathbf{p})$
      where $j$ is constraint index and $s=C_{j}(\mathbf{p})/(\nabla_{\mathbf{p}}C_{j}(\mathbf{p})\mathbf{W}\nabla_{\mathbf{p}}C_{j}(\mathbf{p})^T)$
   2. $\mathbf{p}\gets\mathbf{p}+\Delta \mathbf{p}$
6. $\mathbf{v}\gets(\mathbf{p}-\mathbf{x})/\Delta t$.
7. $\mathbf{x}\gets\mathbf{p}$.

즉, 외력으로 속도를 계산해 내력이 고려되지 않은 후보 위치 $\mathbf p$를 만들고, 이 위치가 내력을 만족하도록 내력의 constraints를 차례로 해소(Gauss-Seidel method)시켜 다음 위치를 업데이트한다. 이 때 constraint projection을 통한 위치의 변화 $\Delta \mathbf p$는 아래와 같다.

$$
\Delta\mathbf{p}=-\frac{C_{j}(\mathbf{p})}{\nabla C_{j}(\mathbf{p})\mathbf{W}\nabla C_{j}(\mathbf{p})^T}\mathbf{W}\nabla C_{j}(\mathbf{p})^T
$$

이렇게 계산된 것은, projection되는 변위 $\Delta \mathbf p$가 $\nabla C_{\mathbf p}$에 평행해야 linear momentum과 angular momentum이 보장된다는 내용에서 살펴볼 수 있다.

이렇게 위치의 변화를 직접 구해낸다는 점과 이 과정이 무조건 안정된다는 점에서 소기의 목표를 달성했다.

## XPBD
