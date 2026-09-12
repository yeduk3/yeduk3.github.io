---
title: Projective Dynamics를 실제로 돌려보면 - SVD 20배, 대칭 밴드의 locking, 크기에 따라 뒤집히는 병목
date: 2026.09
tag: Simulation
draft: true
math: true
---

논문에서 PD는 깔끔하다. Local step은 병렬, global step은 상수 행렬의 back-substitution, 5~10 iteration이면 된다. ysim에 spring PD, strain PD, cotangent bending, 접촉까지 넣고 돌려보니 깔끔함은 그대로였지만 시간이 어디로 가는지와 옷감이 왜 옷감처럼 안 보이는지는 논문이 말해주지 않았다. 감사(audit) 한 번과 프로파일 몇 번에서 나온 것들이다.

## 구현이 논문과 같은가부터

먼저 구현을 Liu 2013(mass-spring PD)과 Bouaziz 2014에 대조했다. 관성 예측 $\mathbf s=\mathbf x+h\mathbf v+h^2\mathbf M^{-1}\mathbf f_{\text{ext}}$, Hooke spring의 local projection $\mathbf d_e=r_e\,(\mathbf q_a-\mathbf q_b)/\|\mathbf q_a-\mathbf q_b\|$, 상수 Laplacian 조립, sparse LDLT 사전 분해, local/global 반복은 논문과 일치했다. 어긋난 곳은 셋. Cloth-cloth 접촉을 정확한 4-vertex constraint가 아니라 네 개의 독립 대각 위치 constraint로 근사한 것, FastGrid 옷감 모델의 shear와 방향별 rest length를 무시한 것, 길이 0 spring에서 local projection이 constraint set 밖의 $\mathbf d=0$을 고른 것. 앞의 하나는 의도된 근사고 뒤의 둘은 결함이다. "논문식 PD가 완전히 구현됐다"가 아니라 "TriangularCloth용 실용적 spring PD"가 정확한 표현이었다.

## 발견 1: local step의 96%가 SVD 하나였다

441 정점 옷감에서 프로파일을 쪼개니 `pd_local` 5.63ms 중 strain projection이 5.41ms였다. Strain projection은 deformation gradient $\mathbf F\in\mathbb R^{3\times2}$의 특이값을 밴드 $[\sigma_{\min},\sigma_{\max}]$로 clamp하는 것인데, Eigen의 `JacobiSVD<3x2>`를 쓰고 있었다. 3 substep × 10 iteration × 800 삼각형 = 24,000회/프레임, 마이크로벤치 201.5ns/call.

$\mathbf F^T\mathbf F$는 2×2 대칭이라 고윳값이 닫힌 형태로 나온다. 거기서 $\mathbf V$, $\boldsymbol\Sigma$를 얻고 $\mathbf U=\mathbf F\mathbf V\boldsymbol\Sigma^{-1}$. 10.0ns/call, 20배. JacobiSVD와의 차이는 $10^{-14}$ 수준이었고, rank-deficient($\sigma_1\approx0$)면 $\mathbf U$의 둘째 열이 임의 방향이라 clamp가 임의 방향 팽창을 만드니 그 경우만 이전 값을 유지하는 fallback으로 뒀다.

| | 441 verts | 10,201 verts |
|---|---|---|
| frame (ms) | 18.31 → 13.34 (1.37×) | 281.99 → 225.44 (1.25×) |
| pd_local | 6.26 → 0.89 (7.0×) | 54.92 → 13.73 (4.0×) |
| pd_global | 3.16 → 3.25 (무변화) | 110.13 → 100.50 |

Global이 무변화인 것이 이 수정의 검증이다. 앞선 측정에서 보였던 global "회귀"는 연속 A/B가 아니라 cross-run drift였다.

## 발견 2: 병목은 정점 수에 따라 뒤집힌다

441 정점에서는 local이 우세했고 SVD가 96%였다. 10,201 정점에서는 `pd_factorize` 97ms + `pd_global` 100ms로 프레임의 87%가 global 쪽이고 local은 6%다. 접촉 가중치가 바뀌는 epoch마다 새 행렬을 만들어 substep당 약 32ms의 LDLT 재분해가 돈다. 그리고 back-substitution은 직렬이라 GPU가 도와주지 못한다.

작은 씬에서 잰 우선순위는 큰 씬에서 틀린다. 병렬화 게이트도 같은 문제였다. `kParallelMinVerts = 1024`라 441 정점 씬은 전부 serial 경로였는데, 강제로 켜면 strain은 1.97배 이득이지만 spring(0.012 → 0.072ms)과 bend(0.196 → 0.424ms)는 dispatch 오버헤드로 손해였다. 정점 수가 아니라 pass별 element 수로 게이트를 걸어야 한다.

## 발견 3: 옷감이 판이 된 이유는 bending이 아니었다

PD 옷감이 camel 위에서 옷감이 아니라 휘어지는 판처럼 얹혔다. 처음 의심한 건 bending이었는데, cotangent mean-curvature bending은 이미 논문 Eq. 21 그대로 들어 있었고 자체 테스트도 통과한 상태였다.

원인은 strain 밴드가 대칭이라는 것이었다. `projectStrain`이 $\sigma$를 $[\sigma_{\min},\sigma_{\max}]$로 clamp하니 $\sigma<\sigma_{\min}$이면 위로 밀어 올린다. 인장을 막는 것과 같은 $w_s=k_{\text{stretch}}=10^5$로. 실제 옷감은 압축 강성이 거의 0이라 좌굴해서 주름이 생기는데, 이 모델은 압축을 인장만큼 세게 막는다. Membrane locking이다. 주름이 안 생기는 건 굽힘이 막혀서가 아니라 굽힘을 유발할 면내 압축이 애초에 안 생기기 때문이었다.

그러면 밴드를 넓히면 되나? GUI 범위 최대 $[0.01, 2.0]$으로 넓혔더니 $\sigma$가 항상 밴드 안에 들어가 clamp가 no-op이 되고 $\mathbf P=\mathbf F$, 잔차 0, 면내 복원력 0. 좌변의 $w_s\mathbf A$는 남아 있으니 복원력 없이 강성만 있는 평활 막이 된다. 그리고 면내 저항이 없으니 한 substep에 두께를 넘어가 관통했다. 밴드를 $[0.95,1.05]$로 되돌리자 broad pair가 3428 → 7108(+107%), narrow contact가 668 → 1687(+152%)로 옷감이 camel을 감싸기 시작했고, `pd_global`/`pd_local`/`pd_factorize`는 소수점까지 불변이었다. 단일 변수 검증이다.

즉 넓히면 뚫리고 좁히면 판이다. 이 축의 양끝이 지금 겪는 두 증상이다. 밴드 폭 $\epsilon$은 free play라서 지지점 간격 $L$ 사이에서 정점이 $L\sqrt{2\epsilon}/2$만큼 공짜로 처지고(PD-5 테스트: $\epsilon=0.05$ falls through, $0.001$ rests), 비대칭 밴드로 압축을 풀면 주름을 사고 관통을 되판다. 노브로는 못 빠져나온다. 필요한 건 $\sigma<1$ 분기에만 낮은 가중치를 주는 2-분기 strain element다. Free play(무저항)가 아니라 저강성이라 처짐이 유계가 된다.

## 발견 4: 접촉 가중치는 두세 자릿수 약했다

접촉 강성 8을 16으로 올려도 관통이 안 잡혔고 iteration 16 → 8도 시각 차이가 없었다. 수렴 문제가 아니라는 뜻이다. 접촉 가중치가 $w=\text{scale}\cdot m_i/h^2=8\times2.27\times10^{-4}\times9\times10^4\approx163$인데 탄성 대각은 코드 주석대로 $10^5\sim10^6$이다. 두세 decade 차이라 scale을 두 배 올려봐야 decade가 안 바뀐다. 진단은 scale 100~1000으로 한 번 때려보는 것이고, GUI 상한이 막고 있으면 상한부터 올려야 한다.

## 발견 5: bending 강성 단위

씬 기본값이 $k_{\text{stretch}}=10^5$, $k_{\text{bend}}=2\times10^5$로 bending이 stretch보다 셌다. 실제 옷감은 굽힘이 인장보다 몇 decade 아래다. 그리고 $k_{\text{bend}}$는 원래 opposite-vertex 거리 spring용 [N/m]인데 그 에너지는 곡률에 quartic이고(굽은 quad의 chord는 $\kappa^2$처럼 짧아진다) PD의 Eq. 21 bending은 곡률에 quadratic이다. $w_b=k_{\text{bend}}\bar A$ 변환은 대각 크기만 맞췄지 작은 곡률에서의 응답 형태는 못 맞춘다. 주름은 정확히 작은 곡률 영역이다.

> 확인 필요: bend 슬라이더를 2e5 → 2e2로 내리는 단일 변수 실험을 계획했으나 결과를 기록하지 못했다. 주름이 생기면 발견 5가 주범, 1e2까지 내려도 판이면 발견 3이 주범.

## 정리

- 프로파일은 크기를 바꿔서 다시 잰다. 441과 10k에서 병목이 뒤집혔다.
- 노브로 못 빠져나오는 증상은 노브 문제가 아니라 element 문제다. 대칭 밴드는 옷감의 압축 거동을 표현할 수 없다.
- 관통을 접촉 강성으로 잡으려 하기 전에 접촉 항과 탄성 항의 크기 자릿수를 나란히 놓는다.
- 그리고 "이미 구현돼 있다"를 먼저 확인한다. Bending을 새로 만들 뻔했다.

> 수치 출처: SVD A/B는 ysim PR #10(`pd_cloth`, `pd_cloth_10k`, InFrame 연속 A/B), 밴드/접촉 수치는 `profiles/system-bottleneck-2026-08-09`, 구현 대조는 `PD_SYSTEM_AUDIT.md`(commit c035149 기준).
