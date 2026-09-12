---
title: Gauss-Seidel과 Jacobi의 수렴성 판단 - XPBD
date: 2026.09
tag: Simulation
draft: true
math: true
# syndication: dev.to, Hashnode
# slug: custom-url-slug
# scripts: /static/js/demo-bvh.js
# styles: /static/css/demo-bvh.css
---

지난 여름 랩실에서 Position Based Dynamics(이하 PBD)와 Projective Dynamics를 발표하고 개인적으로 eXtended PBD(이하 XPBD)까지 읽으면서 한 가지가 계속 걸렸다. PBD의 한 iteration은 constraint를 하나씩 순차로 푸는 Gauss-Seidel이다. 그런데 GPU에 올리려면 한 정점을 여러 constraint가 동시에 건드리는 race가 생기고, 흔한 해법은 Jacobi로 바꿔서 $\Delta\mathbf x$를 평균내는 것이다. 이게 언제 수렴하고 언제 발산하는가? 감으로는 "cloth에서 Jacobi는 튄다"고들 하는데, 그걸 숫자로 보고 싶었다.

## XPBD의 한 iteration은 어떤 선형계의 한 sweep인가

XPBD의 constraint $j$에 대한 갱신은

$$
\Delta\lambda_j=\frac{-C_j-\tilde\alpha_j\lambda_j}{\nabla C_j\mathbf W\nabla C_j^T+\tilde\alpha_j},\qquad
\Delta\mathbf x=\mathbf W\nabla C_j^T\Delta\lambda_j
$$

이고 $\tilde\alpha=0$이면 PBD다. 모든 constraint의 gradient를 쌓아 $\mathbf J=\nabla\mathbf C\in\mathbb R^{m\times n}$이라 두고 한 substep 안에서 $\mathbf J$를 상수로 취급하면(iteration당 한 번 선형화), 위 갱신은 다음 선형계를 푸는 것이다.

$$
\underbrace{\left[\mathbf J\mathbf W\mathbf J^T+\tilde{\boldsymbol\alpha}\right]}_{=:\mathbf A}\Delta\boldsymbol\lambda=-\mathbf C-\tilde{\boldsymbol\alpha}\boldsymbol\lambda,\qquad
\Delta\mathbf x=\mathbf W\mathbf J^T\Delta\boldsymbol\lambda.
$$

$\mathbf A$는 $m\times m$ 대칭이고, $\mathbf J\mathbf W\mathbf J^T=(\mathbf W^{1/2}\mathbf J^T)^T(\mathbf W^{1/2}\mathbf J^T)$라 positive semi-definite다. 대각 원소는

$$
D_i=\nabla C_i\mathbf W\nabla C_i^T+\tilde\alpha_i
$$

인데, 이게 정확히 XPBD $\Delta\lambda_i$의 분모다. Constraint $i$를 "혼자" 풀 때 나누는 값이 곧 시스템 행렬의 대각이라는 뜻이다. Constraint $i$의 입자가 전부 pinned가 아니면 $D_i>0$이고, XPBD 구현은 이미 그 케이스를 skip한다.

"Constraint를 하나씩 순차로 푼다"는 것은 $\mathbf A$를 대각·하삼각·상삼각으로 쪼개 앞의 constraint 결과를 즉시 반영하는 것이니 Gauss-Seidel이고, "전부 동시에 풀고 합친다"는 Jacobi다. 그러니 질문은 정확히 선형대수의 질문이 된다.

## 반복법의 수렴: Ostrowski-Reich와 Householder-John

$\mathbf A=\mathbf D-\mathbf L-\mathbf L^T$로 두자($\mathbf L$은 순수 하삼각). 반복법을 $\mathbf Q\mathbf x^{k+1}=(\mathbf Q-\mathbf A)\mathbf x^k+\mathbf b$ 꼴로 쓰면

- Gauss-Seidel: $\mathbf Q=\mathbf D-\mathbf L$
- Jacobi: $\mathbf Q=\mathbf D$
- SOR: $\mathbf Q=\mathbf D/w-\mathbf L$
- JOR(damped Jacobi): $\mathbf Q=\mathbf D/w$

이고 오차는 $\mathbf e^{k+1}=\mathbf G\mathbf e^k$, $\mathbf G=\mathbf I-\mathbf Q^{-1}\mathbf A$로 전파된다. 수렴 조건은 spectral radius $\rho(\mathbf G)<1$이다.

$\mathbf G$의 고윳값을 직접 구하지 않고도 판정하는 정리가 있다. $\mathbf G\mathbf v=\lambda\mathbf v$에서 출발하면 $(1-\lambda)\mathbf Q\mathbf v=\mathbf A\mathbf v$이고, $\mathbf A$가 SPD면 $\lambda\ne1$이므로 $\mathbf Q\mathbf v=(1-\lambda)^{-1}\mathbf A\mathbf v$다. 양변에 $\mathbf v^*$를 곱하고 $a=\mathbf v^*\mathbf A\mathbf v>0$이라 두면

$$
\mathbf v^*(\mathbf Q+\mathbf Q^*-\mathbf A)\mathbf v
=\left(\frac{1}{1-\lambda}+\frac{1}{1-\bar\lambda}-1\right)a
=\frac{1-|\lambda|^2}{|1-\lambda|^2}\,a.
$$

따라서 **$\mathbf Q+\mathbf Q^T-\mathbf A$가 SPD면 모든 $|\lambda|<1$**이다(Householder-John). 각 방법에 대입하면:

| 방법 | $\mathbf Q+\mathbf Q^T-\mathbf A$ | 수렴 조건 |
|---|---|---|
| Gauss-Seidel | $\mathbf D$ | $\mathbf A$가 SPD면 **항상** 수렴 (Ostrowski-Reich) |
| SOR | $(2/w-1)\mathbf D$ | $0<w<2$ |
| Jacobi | $2\mathbf D-\mathbf A$ | $2\mathbf D-\mathbf A\succ0$, 즉 $\lambda_{\max}(\mathbf D^{-1/2}\mathbf A\mathbf D^{-1/2})<2$ |
| JOR | $(2/w)\mathbf D-\mathbf A$ | $w<2/\lambda_{\max}(\mathbf D^{-1/2}\mathbf A\mathbf D^{-1/2})$ |

핵심은 비대칭이다. Gauss-Seidel은 $\mathbf A$가 SPD이기만 하면 끝이다. Jacobi는 SPD로는 부족하고 정규화된 행렬의 최대 고윳값이 2 미만이어야 한다. $\mathbf A$가 SPD면 $\lambda_{\min}>0$은 자동이라 위쪽 bound만 문제다.

처음 이 문제를 노트에 정리할 때는 $-\mathbf L^{-1}\mathbf U$를 미리 계산하기 어렵다는 데서 막혔는데, 이 정리 덕분에 그럴 필요가 없다는 걸 알게 됐다. $\mathbf D$만 계산하면 된다.

## XPBD에 대입

**$\mathbf A$가 SPD인 조건.** $\tilde\alpha_i>0$이 전부 성립하면 $\mathbf A=\mathbf J\mathbf W\mathbf J^T+\tilde{\boldsymbol\alpha}$는 PSD + PD = PD다. 즉 compliant constraint만 있는 XPBD에서 **Gauss-Seidel은 항상 수렴**한다. $\tilde{\boldsymbol\alpha}=0$(PBD)이면 $\mathbf W^{1/2}\mathbf J^T$가 full column rank, 즉 redundant constraint가 없어야 SPD다.

**Singular한 경우.** PBD에 redundant constraint가 있으면 $\mathbf A$가 singular하고 iteration matrix에 고윳값 1이 $\ker\mathbf A$ 위에 생긴다. 그런데

$$
\mathbf v^T\mathbf A\mathbf v=\|\mathbf W^{1/2}\mathbf J^T\mathbf v\|^2+\|\tilde{\boldsymbol\alpha}^{1/2}\mathbf v\|^2=0\ \Rightarrow\ \mathbf W\mathbf J^T\mathbf v=\mathbf 0
$$

이므로 $\ker\mathbf A\subseteq\ker(\mathbf W\mathbf J^T)$다. $\Delta\boldsymbol\lambda$의 null 성분은 $\Delta\mathbf x=\mathbf W\mathbf J^T\Delta\boldsymbol\lambda$를 안 움직인다. 위치는 수렴하고 $\lambda$만 non-unique한 것이다. Constraint가 서로 모순이어도 $\lambda$가 null 방향으로 선형 drift할 뿐 위치는 수렴한다. 수치로 확인하면 400 iteration 후 $\|\boldsymbol\lambda\|=606$인데 position step은 0이었다. 그리고 평평한 cloth(edge + diagonal distance constraint)는 $\tilde{\boldsymbol\alpha}=0$에서 항상 singular하다. 모든 gradient가 in-plane이라 $\text{rank}\,\mathbf A=2n-3$이고, 12×12 grid에서 rank 285/385였다.

> 확인 필요: singular consistent system의 semi-convergence 정리 출처. Keller 1965로 기억하나 미확인.

**Jacobi.** 같은 입자를 공유하는 두 constraint $i,j$의 off-diagonal은 $A_{ij}=\nabla C_i\mathbf W\nabla C_j^T$이고 Cauchy-Schwarz로 $|A_{ij}|/\sqrt{D_iD_j}\le1$이다. Gershgorin을 쓰면 $\lambda_{\max}\le1+\deg_{\max}$, 여기서 $\deg_{\max}$는 constraint graph의 최대 차수다. 그러니 JOR의 안전 범위는 $w<2/(1+\deg_{\max})$이고, 이게 흔히 쓰는 "정점당 constraint 수로 $\Delta\mathbf x$를 평균낸다"에 대략 대응한다.

발산의 최소 예는 간단하다. 같은 입자를 같은 방향으로 당기는 constraint 두 개면 정규화 off-diagonal이 정확히 1이라 $\lambda_{\max}=2$, $\rho_J=1$. 고전적인 2배 overshoot이다.

**Compliance의 효과.** $\tilde\alpha_i$는 $D_i$만 키우고 off-diagonal은 건드리지 않는다. 정규화 off-diagonal이 줄어드니 Jacobi에 유리하다. $\tilde{\boldsymbol\alpha}\to\infty$면 한 sweep에 exact다. 즉 **무를수록 Jacobi가 안전**해지고, PBD(무한 강성)가 Jacobi에 가장 불리한 극한이다.

## 숫자로

Unit mass, unit rest length, $D_i=2+\tilde\alpha$인 설정에서 $\mathbf A$를 조립해 spectral radius를 직접 계산했다(계산 스크립트 `xpbd_splitting.py`, rope 케이스는 아래 Young 이론과 $10^{-9}$ 이내로 일치하는지 self-check 포함).

| system | $\tilde\alpha$ | $\lambda_{\max}$ | $\rho_J$ | $\rho_{GS}$ |
|---|---|---|---|---|
| rope $m=49$ | 0 | 1.998 | 0.998 | 0.996 |
| rope $m=49$ | 0.5 | 1.80 | 0.80 | 0.64 |
| rope $m=49$ | 2 | 1.50 | 0.50 | 0.25 |
| cloth 12×12 flat, $m=385$ | 0 | 3.34 | **2.34 발산** | 0.976 |
| cloth 12×12 flat | 0.5 | 2.87 | **1.87 발산** | 0.77 |
| cloth 12×12 flat | 2 | 2.17 | **1.17 발산** | 0.42 |
| cloth 12×12 non-flat | 0 | 3.25 | **2.25 발산** | 0.9997 |

읽히는 것 세 가지.

1. **Cloth에서 순수 Jacobi($w=1$)는 발산한다.** $\tilde\alpha=D_i$ 수준으로 물러도($\tilde\alpha=2$) 여전히 발산. Gershgorin bound가 말해주듯 차수가 높은 mesh에서 정규화 off-diagonal의 합이 1을 넘기 때문이다. JOR $w=1/6$은 수렴하지만 $\rho=0.998$이라 사실상 안 움직인다.
2. **Gauss-Seidel은 수렴하지만 non-flat cloth에서 $\rho\approx1$이다.** $\lambda_{\min}=1.6\times10^{-4}$짜리 bending mode 때문이다. 수렴은 하는데 그 mode는 영원히 안 굳는다.
3. **Compliance는 두 방법 모두에 좋다.** Rope에서 $\tilde\alpha$ 0 → 2로 $\rho_{GS}$가 0.996 → 0.25. 재질을 무르게 하는 게 곧 solver를 좋게 한다.

## Rope는 Young의 정리 그대로

Straight rope는 $\mathbf A$가 tridiagonal이라 consistently ordered이고 $\mathbf D^{-1}\mathbf A=\text{tridiag}(-\tfrac12,1,-\tfrac12)$다. 고전 이론이 그대로 적용된다.

$$
\rho_J=\cos\frac{\pi}{m+1},\qquad
\rho_{GS}=\rho_J^2,\qquad
w_{\text{opt}}=\frac{2}{1+\sin\frac{\pi}{m+1}},\qquad
\rho_{SOR}=w_{\text{opt}}-1.
$$

오차를 $10^{-3}$으로 줄이는 데 필요한 iteration 수를 세어보면 $m=50$에서 GS 1819회, SOR 56회. $m=200$에서 GS 28276회, SOR 221회. GS는 $O(m^2)$, SOR은 $O(m)$이다. "긴 chain은 PBD가 못 굳힌다"는 경험칙의 정량화가 이것이다. 정보가 iteration당 1-ring씩만 퍼지니 길이 $m$인 chain을 굳히려면 $m^2$ 차수의 sweep이 필요하다.

## 그래서 실무에서는

- GPU에서 PBD/XPBD를 "Jacobi로 바꾸고 평균"하는 것은 사실 JOR $w\approx1/\deg$이고, cloth에서 수렴은 하되 $\rho\approx0.998$이라 iteration을 아무리 돌려도 굳지 않는다. Graph coloring Gauss-Seidel이 색깔 수만큼 dispatch를 내는 대가를 치르는 이유가 여기 있다.
- Compliance를 주면 두 방법 모두 좋아진다. $\tilde\alpha=\alpha/\Delta t^2$이므로 **substep을 잘게 쪼개는 것은 같은 $\alpha$에서 $\tilde\alpha$를 키우는 것**이고, 이것이 Small Steps(Macklin et al. 2019)가 "iteration보다 substep"이라고 말하는 것의 선형대수적 얼굴이다.
- Iteration으로 $O(m^2)$를 이길 수는 없다. Chain이 길면 SOR/Chebyshev 가속이나 multigrid처럼 spectral radius 자체를 낮추는 장치가 필요하다.

> 이 글의 수렴 조건 유도는 표준 교재(Ostrowski-Reich, Householder-John)를 XPBD 행렬에 대입한 것이고, 수치는 위 설정에서 직접 계산한 값이다. 실제 solver의 $\mathbf J$는 iteration마다 바뀌므로 여기서의 결론은 "한 substep 안에서 선형화한 문제"에 대한 것이다.
