---
title: Large Steps 포팅기 - 발산의 범인은 stiffness가 아니었다
date: 2026.09
tag: Simulation
draft: true
math: true
---

Baraff & Witkin의 Large Steps in Cloth Simulation(1998)을 ysim의 네 번째 solver로 옮겼다. Implicit Euler에 stretch/shear/bend condition force, modified PCG, constraint filter까지 논문 그대로다. 참조 구현이 770줄짜리로 있었고 "stiff해서 폭발할 것"이라는 예상을 갖고 시작했는데, 실제로 두 번 폭발했고 두 번 다 원인은 stiffness가 아니었다. 부호였다.

## 뼈대

한 step은 다음 선형계를 푼다.

$$
\left(\mathbf M-h\frac{\partial\mathbf f}{\partial\mathbf v}-h^2\frac{\partial\mathbf f}{\partial\mathbf x}\right)\Delta\mathbf v
=h\left(\mathbf f+h\frac{\partial\mathbf f}{\partial\mathbf x}\mathbf v\right)
$$

힘은 condition $C(\mathbf x)$에 대해 $\mathbf f_i=-k\,C\,\partial C/\partial\mathbf x_i$이고, Jacobian 블록은

$$
\mathbf K_{ij}=-k\left(\frac{\partial C}{\partial\mathbf x_i}\frac{\partial C}{\partial\mathbf x_j}^T+\frac{\partial^2C}{\partial\mathbf x_i\partial\mathbf x_j}\,C\right).
$$

접촉과 pin은 constraint filter $\mathbf S$로 처리한다. 접촉 정점의 법선 방향 자유도를 $\mathbf S_i=\mathbf I-\mathbf n\mathbf n^T$로 지우고, pin은 $\mathbf S_i=\mathbf 0$. PCG 안에서 매 step $\mathbf S$를 곱해 그 방향으로는 속도 변화가 생기지 않게 한다. 분리 속도는 $\mathbf z_i$에 심는다.

게이트는 하나였다. Substep 1(h=1/60)에서 폭발 없이 도는 것. Symplectic 경로는 여기서 발산한다.

## 첫 번째 폭발: bend gradient의 빠진 projection

핀 시트 씬에서 곧바로 1e26으로 날아갔다. Stiffness를 의심했지만 stretch만 남기면 멀쩡했고, bend를 켜면 터졌다.

참조 구현의 bend gradient는 법선 $\mathbf n=\mathbf N/|\mathbf N|$의 미분에서

$$
\frac{\partial\mathbf n}{\partial\mathbf x}=\frac{(\mathbf I-\mathbf n\mathbf n^T)}{|\mathbf N|}\frac{\partial\mathbf N}{\partial\mathbf x}
$$

의 투영 $(\mathbf I-\mathbf n\mathbf n^T)$을 생략하고 있었다. 오차가 $\cos\theta$에 비례해서 얕은 주름에서는 $\partial\theta/\partial\mathbf x$의 부호가 뒤집힌다. 부호가 뒤집힌 gradient로 힘을 주면 bending이 에너지를 빼는 게 아니라 펌프한다. 그러니 stiffness를 낮춰도 방향이 틀린 힘은 여전히 에너지를 넣는다.

투영을 살리자 게이트 네 개가 전부 통과했다. 같은 함수에 부수 결함이 두 개 더 있었다. $\sin\theta$를 1로 clamp해 $1/\sin\theta$ 인자가 사라져 있었고, $\theta=\arccos$라 부호가 없었다. Bend gradient는 중앙차분과 대조하는 self-test(LS-3)를 붙여 두었다.

## 두 번째 폭발: 압축 상태의 부정부호 행렬

씬을 늘려 구 collider 위에 옷감을 떨어뜨리자 다시 발산했다. 이번엔 "유한하고 움직였는가"만 보던 테스트 게이트를 통과한 채로. `ls_cloth_ball`에서 최대 속도 3.0e5, `ls_analytic_sphere`에서 9.4e16이었다. 프레임별로 보면 프레임 20에서 첫 접촉 24건 → 22에서 v=46 → 23에서 2.9e4.

접촉 자체가 아니라 접촉이 만든 압축 상태가 원인이었다. Jacobian의 두 번째 항 $\frac{\partial^2C}{\partial\mathbf x^2}C$는 $C>0$(인장)일 때만 positive semi-definite다. 옷감이 구에 눌려 $C<0$(압축)이 되면 $\mathbf K$에 양의 성분이 생기고, $\mathbf A=\mathbf M-h\,\partial\mathbf f/\partial\mathbf v-h^2\,\partial\mathbf f/\partial\mathbf x$의 대각이 음수가 된다. 그러면 Jacobi 전처리기 $1/\text{diag}(\mathbf A)$의 부호가 뒤집혀 CG가 0~1회 만에 탈출하거나(`cg 1`, `cg 0` 관측), 음의 곡률 방향에서 $\alpha=\delta_{\text{new}}/(\mathbf p^T\mathbf A\mathbf p)$가 폭주한다. `cq > 1e-30` 가드는 너무 약했다. Shear의 $\partial^2C/\partial\mathbf x^2$는 $C$의 부호와 무관하게 부정부호가 될 수 있다.

수정은 Hessian 항을 stretch가 인장일 때만 넣고, shear는 항상 Gauss-Newton(첫 항만)으로 낮추는 것이었다. Bend는 이미 GN이었다. 이렇게 하면 $\mathbf A$가 항상 SPD로 유지된다. 대가는 압축 상태에서의 정확도지만, 옷감은 압축 저항이 거의 없어 좌굴하니 실용적으로는 오히려 맞는 근사다.

## 세 번째 교훈: 테스트 게이트

두 번째 폭발이 테스트를 통과했다는 게 문제였다. "유한하다"는 게이트로는 9.4e16도 통과한다. 게이트를 셋으로 바꿨다. 유한성, 실제로 움직였는가(solver가 씬을 건너뛰면 가만히 있는 천도 통과했다), 그리고 최대 속도 50m/s 미만. 세 번째가 이번 발산을 잡는다.

## 그 외 참조 구현과 달라진 것

- 감쇠 $\dot C$를 condition당 스칼라로.
- 전처리기 $\mathbf P/\mathbf P^{-1}$ 정정.
- Stiffness를 rest 면적으로 나눠 해상도 독립화(참조는 cm 단위에 k=1e3, ysim은 m 단위에 k=1e5라 단위 재보정도 필요했다).
- 접촉 관통 회복 비율에 상한(0.2·(thickness − dist)/h, 최대 1m/s). 작은 h에서 관통이 폭발 분리로 바뀌는 것을 막는다.

## 결과

`--self-test` 실측, LS-1~5 전부 PASS.

| 씬 | minY | peak \|v\| | 접촉 |
|---|---|---|---|
| ls_cloth_hang | 0.6 → −0.137 | 6.49 | 0 |
| ls_cloth | 0.6 → −0.01 | 3.51 | 391 |
| ls_cloth_ball | 0.6 → 0.461 | 8.63 | 32 |
| ls_cloth_flag | 0.7 → 0.7 (핀 열) | 22.7 | 0 |
| ls_analytic_sphere | 1.2 → 0.250 | 4.29 | 223 |

한계도 명확하다. Constraint filter는 정점당 하나의 법선을 지우는 one-sided 장치라 옷감-옷감 양방향 접촉이나 self-collision은 표현이 안 된다. 그건 PD 몫이다. 그래서 `pbd_cloth_stack`/`pbd_cloth_xyfold` 같은 씬은 일부러 복제하지 않았다. 핵심이 빠진 씬을 출하하는 셈이라서.

## 정리

발산을 보면 stiffness를 먼저 의심하게 되는데, 두 번 다 답은 부호였다. 하나는 gradient의 부호, 하나는 행렬의 정부호성. Stiffness는 발산의 속도를 정하지 방향을 정하지 않는다. 방향이 틀렸으면 아무리 무르게 해도 터진다. 그리고 그걸 잡는 테스트는 "유한한가"가 아니라 "물리적으로 말이 되는 범위 안에 있는가"여야 했다.

> 미검증: 인터랙티브 렌더러에서의 시각 확인과 InFrame 성능 측정은 이 시점에 하지 않았다. 성능은 별도 글(네 solver 비교)에 있다. 코드 근거는 ysim `include/sim/large_steps_system.hpp` 헤더 주석과 `docs/design/implicit-euler-system.md`.
