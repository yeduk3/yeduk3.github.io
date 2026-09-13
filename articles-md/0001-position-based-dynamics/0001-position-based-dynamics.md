---
title: 힘이 아닌 위치에 기반한 역학 - PBD, PD, XPBD
date: 2026.09.13
tag: Simulation
draft: false
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

## 기존 force-based dynamics나 impulse-based dynamics의 문제점

Force-based dynamics는 힘이나 퍼텐셜을 모델링하고 여기서 가속도 -> 속도 -> 위치의 순서로 적분하여 답을 얻는 계열의 시스템의 갖는다.
그러나 이들의 문제는 우리가 얻어야 하는 위치 정보들이 안정적으로 얻어지는 지 쉽게 알기 어렵다.
예를 들면, Baraff and Witkin의 Large Steps in Cloth Simulation(SIGGRAPH, 1998)에서 모델링한 방식처럼 옷감의 internal energy가 force로 통합되면서 속도 변화량에 대한 식을 풀면, 이 속도가 안정적으로 계산되었는지는 별도로 검사해야 한다.
즉, 구해지는 답의 안정성이 보장되지 않는다.
또한 시뮬레이션을 조작하고자 하면 초기값을 적절히 튜닝해야 하므로 고역이 아닐 수가 없다.

Impulse-based dynamics는 충격량을 통해 직접적인 속도의 변화량을 알 수 있어 위치의 변화량을 아는 것과 크게 다르지 않게 설계할 수 있다. 그러나 이는 주로 강체의 시뮬레이션에서 사용된다.

즉, 변형체의 시뮬레이션에서 안정성이나 제어성을 얻는 것은 위의 방법론으로는 어려움이 있다. Position-based dynamics는 이러한 문제를 해결할 수 있다. Müller의 2006년 PBD 논문 이전에도 유사한 방법들은 존재했으나 이들은 모두 특정 경우에 한정되는 특징을 가졌다. Müller는 이를 보다 확장시켜 여러 경우에 위치 기반의 역학을 적용할 수 있도록 기반을 닦은 연구를 발표했다.

## PBD

옷감의 예시를 보자.
옷감은 대표적인 변형체로 변형되면서 발생하는 internal force를 모델링해야 시뮬레이션할 수 있다.
PBD에서는 이러한 internal force를 파티클 간 위치 관계에 대한 제약 조건(constraint)으로 모델링하였다.
이로써 옷감 내부에 존재하는 internal force를 적절한 constraint의 형태로 두어 이를 최대한 만족하도록 하면 옷감을 시뮬레이션할 수 있다.

예를 들어, 옷감 메시에서 edge로 연결된 두 파티클 $\mathbf x_1, \mathbf x_2$가 있다고 하자.
해당 두 파티클 사이에 존재하는 stretch constraint $C(\mathbf x_1,\mathbf x_2)$는 현재 시점에서 두 파티클 사이 거리가 초기 상태(rest state)에서의 거리 $l_0$로부터 얼마나 변했는지로 모델링할 수 있다.

$$
C(\mathbf x_1,\mathbf x_2)=\|\mathbf x_1-\mathbf x_2\|_2-l_0
$$

즉, 기존 force-based 방법론에서는 potential energy로 모델링되어 force로 편입되던 항들이 이제는 제약조건으로 들어가게 되는 것이다.
여기서 외력은 이런 제약 조건으로 들어가지 못한다.
따라서 PBD 논문에서는 외력을 속도에 편입시켜 외력만을 고려한 후보 위치 $\mathbf p$를 도입하게 된다.
이렇게 했을 때, CCD(Continuous Collision Detection)해야 하는 path도 $\mathbf x\to\mathbf p$로 두어 계산해볼 수 있다.
물론 constraint projection을 하는 과정에서 최초에 생성한 충돌 후보 쌍이 얼마나 robust할 지는 의문이다.

Constraint projection은 한 $j$-th constraint $C_j(\mathbf p)=0$을 만족시키는 $\mathbf p$를 구하는 과정이다.
이 때 internal constraints는 물체의 linear/angular momentum을 변화시키지 않는 $\Delta\mathbf p$를 구해야 한다.
그런데 이 조건은 constraint의 설계에서 자연스럽게 만족될 수 있다.
만약 어떤 constraint $C_j(\mathbf p)$가 rigid body mode(translation and rotation)에 invariant하게 설계되었다면, $\nabla C_j(\mathbf p)$는 rigid body mode에 수직인 방향이 된다.
그리고 rigid body mode에 수직이면 momentum을 변화시키지 않는다.
근데 이 constraint 값을 가장 빠르게 줄일 수 있는 방향도 gradient 방향과 평행하기 때문에 $\Delta\mathbf p$가 $\nabla C_j(\mathbf p)$에 평행하도록 설계하지 않을 이유가 없다.

구체적인 유도는 $C_j(\mathbf p+\Delta\mathbf p)\approx C_j(\mathbf p)+\Delta \mathbf p\cdot\nabla C_j(\mathbf p)=0$와 $\Delta \mathbf p=\lambda\nabla C_j(\mathbf p)$를 연립하면 구할 수 있다.
여기에 파티클 별 질량을 고려하여 아래의 식을 얻는다.

$$
\Delta\mathbf{p}=-\frac{C_{j}(\mathbf{p})}{\nabla C_{j}(\mathbf{p})\mathbf{W}\nabla C_{j}(\mathbf{p})^T}\mathbf{W}\nabla C_{j}(\mathbf{p})^T
$$

이렇게 위치의 변화를 직접 구해낸다는 점과 이 과정이 무조건 안정된다는 점에서 소기의 목표를 달성할 수 있다.

### PBD에서 생각할 거리

Constraint projection이 위치의 직접 조작을 정당화하는 근거는 결국 internal constraint는 설계를 rigid mode invariant하게 한다면 projection이 momentum을 유지시킨다는 데에 있다.
Collision이나 attachment는 운동량이 외부에서 들어오므로 momentum을 유지할 필요가 없다.
다만 cloth self collision은 같은 물체 안의 상호작용이므로 internal로 취급한다.

문제는 stiffness다.
PBD는 $\Delta \mathbf p$에 $k\in[0,1]$을 곱해 제약조건의 stiffness를 조절하는데, 이 $k$는 물리 단위가 없다.
한 제약조건의 오차를 $k$배 줄이므로 $n$번의 iteration을 반복하면 남는 오차는 $(1-k)^n$ 만큼이 된다.
같은 $k$라도 iteration 수 $n$을 늘리면 오차가 exponential하게 줄어 옷감이 더 뻣뻣해진다.
또한 $k$는 오차를 줄이는 상대적 비율이므로 timestep을 바꾸면 $\Delta\mathbf p$ 자체가 스케일이 달라져 역시 재질이 바뀔 수 있다.
논문은 $k' = 1-(1-k)^{1/n}$으로 iteration 수를 보정하지만, 이건 iteration 수에 대해서만 재질 변화가 해소되고 $\Delta t$에 대해서는 아니다.
재질이 solver의 설정값에 의존적이라는 뜻이다.

실제로 직접 개발한 시뮬레이션 엔진 ysim에서 PBD를 구현했는데, iteration 수가 8인 옷감 씬에서 substep을 5에서 60으로 올리자 프레임당 오차가 $(1-k)^{40}$에서 $(1-k)^{480}$으로 확 줄어들면서 옷감이 휘어지는 철판처럼 변했다.
이러한 문제는 다음 절의 XPBD에서 해결된다.

<figure class="compare">
  <video src="0001-01-substeps5.mp4" autoplay muted loop playsinline></video>
  <video src="0001-02-substeps60.mp4" autoplay muted loop playsinline></video>
  <figcaption>같은 씬, iteration 8. 왼쪽 substep 5, 오른쪽 substep 60.</figcaption>
</figure>

또 하나는 순서 의존이다.
Gauss-Seidel은 constraint를 하나씩 순차로 풀기 때문에 이미 바뀐 위치가 즉시 반영되어 변화가 한 sweep 안에서 멀리 전파된다.
대신 constraint 순서를 고정하지 않으면 결과가 진동할 수 있고, 순서에 따라 다른 답으로 수렴한다.
이 지점은 뒤의 PD가 정면으로 다룬다.

## XPBD

XPBD는 PBD의 projection이 물리적으로 어떤 의미를 가지는 지를 보여준다.
Constraint를 potential로 쓰면, compliance $\alpha$(stiffness의 역수)에 대해

$$
U(\mathbf x)=\frac12 \mathbf C(\mathbf x)^T\boldsymbol\alpha^{-1}\mathbf C(\mathbf x),\qquad
\mathbf f=-\nabla U^T=-\nabla\mathbf C^T\boldsymbol\alpha^{-1}\mathbf C.
$$

여기에 backward Euler를 적용하고 Lagrange multiplier $\boldsymbol\lambda=-\tilde{\boldsymbol\alpha}^{-1}\mathbf C$, $\tilde{\boldsymbol\alpha}=\boldsymbol\alpha/\Delta t^2$을 도입하면 한 스텝의 조건은 두 식으로 정리된다.

$$
\begin{aligned}
\mathbf g(\mathbf x^{n+1},\boldsymbol{\lambda}^{n+1}) &=\mathbf M(\mathbf x^{n+1}-\tilde{\mathbf x})-\nabla\mathbf C(\mathbf x^{n+1})^T\boldsymbol\lambda^{n+1}&=\mathbf 0  \\
\mathbf h(\mathbf x^{n+1},\boldsymbol{\lambda}^{n+1}) &= \mathbf C(\mathbf x^{n+1})+\tilde{\boldsymbol\alpha}\boldsymbol\lambda^{n+1}&=\mathbf 0
\end{aligned}
$$

여기서 $\tilde{\mathbf x}=2\mathbf x^n-\mathbf x^{n-1}=\mathbf x^n+\Delta t\mathbf v^n$로 예측된 위치를 나타낸다.
첫 줄은 운동량, 둘째 줄은 constraint에 compliance가 붙은 것이다.
이 식에 $\Delta \mathbf x$와 $\Delta \boldsymbol\lambda$로 $\mathbf x^{n+1}$과 $\boldsymbol\lambda^{n+1}$를 구성하면서 linearize하면, 아래의 equation을 얻는다.

$$
\begin{bmatrix}
\mathbf K & -\nabla\mathbf C^T \\
\nabla\mathbf C & \tilde{\boldsymbol\alpha}
\end{bmatrix}
\begin{bmatrix}
\Delta\mathbf x\\ \Delta\boldsymbol{\lambda}
\end{bmatrix}
=
-\begin{bmatrix}
\mathbf g(\mathbf x^{n},\boldsymbol{\lambda}^{n}) \\
\mathbf h(\mathbf x^{n},\boldsymbol{\lambda}^{n})
\end{bmatrix}
$$

$$
\mathbf x^{n+1}\gets \mathbf x^n+\Delta\mathbf x, \quad
\boldsymbol \lambda^{n+1}\gets \boldsymbol \lambda^n+\Delta\boldsymbol \lambda
$$

여기서 이 식을 풀기 위한 중요한 두 가지 가정이 들어간다.
첫 째, $\mathbf K\approx\mathbf M$이다. 위 식의 행렬 $\mathbf K=\nabla_{\mathbf x^n}\mathbf g$는 운동량 항의 위치 미분과 constraint의 Hessian을 더한 항으로 구성된다.
그러나 이 공격적인 근사로 인해 운동량의 변화가 위치에 대한 상수(=질량)로, constraints는 위치에 대해 선형적인 무언가로 가정된다.
둘 쨰, $\mathbf g(\mathbf x^n,\boldsymbol\lambda^n)=\mathbf 0$이다. 이는 최초의 Newton step이 $\mathbf x_0=\tilde{\mathbf x},\boldsymbol{\lambda}_0=\mathbf 0$으로 초기화하는 것으로 정당화될 수 있다.
그러면 초기 $\mathbf g$는 $\mathbf 0$이고, 이 momentum 항이 변화가 적다면 아주 작은 값을 가질 것이라 영향이 적다고 저자들은 주장한다.

이 비선형계를 Gauss-Seidel처럼 constraint $j$ 하나만 보고 Newton 한 스텝을 밟되, $\nabla C_j$를 고정하고 현재 오차를 대입하면

$$
\Delta\lambda_j=\frac{-C_j-\tilde\alpha_j\lambda_j}{\nabla C_j\mathbf W\nabla C_j^T+\tilde\alpha_j},\qquad
\Delta\mathbf x=\mathbf W\nabla C_j^T\Delta\lambda_j,\qquad
\lambda_j\gets\lambda_j+\Delta\lambda_j.
$$

$\tilde\alpha_j\to 0$이면 분자는 $-C_j$, 분모는 $\nabla C_j\mathbf W\nabla C_j^T$가 되어 정확히 PBD의 projection이 나온다.
PBD는 XPBD에서 potential의 계수가 무한히 큰 경우의 특수해였다.
Potential의 계수가 무한히 크다는 것은, potential이 줄어들기 위해서는 $C\to0$가 될 수밖에 없는 것을 의미한다.
그래서 constraint가 0이 되도록 projection할 수 있는 것이었고 이 정도를 조절하기 위한 정체불명의 파라미터 $k$를 두게 된 것이었다.

Stretch constraint의 예로 감을 잡아보자. 두 파티클의 질량이 1이고 초기 거리가 1, 현재 거리 1.2라 하면 $C=0.2$, $\nabla C\mathbf W\nabla C^T=w_1+w_2=2$다.

- $\tilde\alpha=0$: $\Delta\lambda=-0.1$, 두 입자가 각각 0.1씩 다가가 $C=0$. PBD와 동일하다.
- $\tilde\alpha=0.1$, 첫 iteration($\lambda=0$): $\Delta\lambda=-0.2/2.1\approx-0.0952$, 남는 $C\approx0.0095$. Iteration을 더 돌려도 $\lambda$가 누적되므로 $C=-\tilde\alpha\lambda$를 만족하는 상태로 constraint violation이 유지된다.

(영상 첨부 예정)

이것이 iteration 독립성의 메커니즘이다. PBD는 매 iteration 오차의 일부를 지우기만 하니 무한히 돌리면 무한 강성으로 간다. (PBD에서 첨부한 영상처럼.)
XPBD는 constraint마다 총 multiplier $\lambda$를 누적하면서 그 constraint가 "지금까지 얼마나 constraint를 해소했는지"를 알고, compliance가 정한 평형에서 멈춘다.
PBD에서 constraint당 스칼라 하나씩만 더 추가하여 문제를 해결한 것이다.

그러나 저자들은 stiffness만 iteration에서 독립이지 수렴성은 여전히 iteration 수에 종속이라고 말한다.
Gauss-Seidel이나 Jacobi같은 iterative methods의 수렴성을 분석해보는 글은 별도로 뺐다.
그리고 이후 연구인 Small Steps in Physical Simulation(Macklin et al. 2019)에서는 "iteration을 늘리기보다 substep을 잘게 쪼개고 iteration은 1번"이 낫다고 뒤집는다.
Predict 단계의 위치 오차가 $\Delta t^2$에 비례하니 substep을 반으로 쪼개면 오차가 1/4로 주는 반면 iteration은 잔차를 선형으로만 줄이기 때문이다.

## Projective Dynamics

PD는 XPBD보다 2년 앞선 논문인데, PBD를 다른 식으로 해석한다.
Implicit Euler를 최적화 문제로 쓰면

$$

\min_{\mathbf q}\ \frac{1}{2h^2}\left\|\mathbf M^{1/2}(\mathbf q-\mathbf s)\right\|^2+\sum_i W_i(\mathbf q),\qquad
\mathbf s=\mathbf x+h\mathbf v+h^2\mathbf M^{-1}\mathbf f_{\text{ext}}


$$

가 된다.
이걸 Newton으로 풀면 Hessian이 iteration마다 바뀌어 비싸다.
논문의 관찰은 탄성 퍼텐셜이 담은 두 가지, 즉 어떤 상태가 안정인가(constraint manifold)와 현재 상태가 거기서 얼마나 떨어졌는가(distance)를 분리할 수 있다는 것이다.
비선형성은 manifold가 이미 담고 있으니 거리 쪽은 단순하게 만들고자 quadratic으로 둬도 된다.

$$
W_i(\mathbf q)=\min_{\mathbf p_i\in\mathcal M_i}\frac{w_i}{2}\left\|\mathbf A_i\mathbf q-\mathbf B_i\mathbf p_i\right\|^2
$$

그러면 두 step을 번갈아 푸는 것으로 충분하다.

- **Local step**: constraint마다 manifold 위의 목표점 $\mathbf p_i$를 구한다. Constraint끼리 독립이라 완전히 병렬이다.
- **Global step**: $\mathbf p_i$들을 고정하고 전체 위치를 선형계 한 번으로 정한다. $(\mathbf M/h^2+\sum_i w_i\mathbf A_i^T\mathbf A_i)\mathbf q=\mathbf M\mathbf s/h^2+\sum_i w_i\mathbf A_i^T\mathbf B_i\mathbf p_i$. 좌변 행렬은 constraint가 바뀌지 않는 한 상수이므로 sparse Cholesky로 한 번 분해해 두고 back-substitution만 반복한다.

Objective function은 제곱 norm의 합이라 항상 0 이상이고, 두 step 모두 값을 (약하게) 감소시킨다.
Constraint set이 non-convex이어도 그렇다.
단조 감소에 하한이 있으니 목적함수 값은 수렴한다.
전역 최소로의 수렴은 아니다.
실사용은 5~10 iteration이다.

PBD와의 관계는 여기서 드러난다.
$\mathbf A_i=\mathbf B_i=\mathbf M^{1/2}$로 두면 local step의 목적함수를 Gauss-Seidel로 풀면 PBD와 같다.
즉 PBD의 constraint projection은 potential energy에 대한 Gauss-Seidel type minimization만 진행하고 global step을 생략하여 물리적 정확성을 잃은 것이다.
PD는 global step에 더해 local step에서 Jacobi style을 택한다.
순서 의존과 진동을 피하고 local step의 병렬성을 얻는 대신, 각 constraint를 정확히 만족하는 점이 아니라 여러 constraint의 절충점으로 수렴시키기 위함이다.

$\mathbf A_i$를 절대 위치가 아니라 상대 위치로 만드는 differential coordinate matrix로 두는 이유도 두 가지다.
첫 째는 수렴성이 더 좋기 때문이다.
절대 위치를 쓰면 변화가 iteration당 1-ring씩만 퍼져서 mesh가 조밀할수록 더 많이 돌아야 한다.
둘 째는 linear momentum의 보존이 유도되기 때문이다.
$\mathbf A_i\mathbf 1=\mathbf 0$이면 global step 양변에 $\mathbf 1^T$를 곱했을 때 constraint 항이 통째로 사라져 $\sum_i m_i\mathbf q_i=\sum_i m_i\mathbf s_i$만 남는다.
즉, local step이 낸 $\mathbf p_i$가 무엇이든 총 linear momentum은 관성 예측만 있을 때의 linear momentum과 같다.
그러나 각운동량은 그렇지 않다.
회전 불변성은 비선형 대칭이라 같은 논법이 통하지 않고, 결국 implicit Euler라는 적분기 자체가 각운동량 보존형이 아니라고 한다.
탄성 퍼텐셜의 rigid motion invariance는 탄성력이 만드는 토크를 지워 줄 뿐이다.

논문이 명시한 한계는 셋이다.
Implicit Euler에서 오는 numerical damping, mesh resolution에 의존하는 iteration 수, 그리고 hard constraint를 다룰 수 없다는 것.
모든 constraint가 soft이므로 충돌도 hard하게 보장되지 않고 weight에 따라 관통한다.
Constraint가 동적으로 바뀌는 경우(tearing 등)에는 factorization을 다시 만들지 않고 rank update/downdate로 갱신한다.

## PBD, XPBD, PD의 비교

|                      | PBD                            | XPBD                        | PD                                                |
| -------------------- | ------------------------------ | --------------------------- | ------------------------------------------------- |
| integrator           | approximated implicit Euler    | approximated implicit Euler | implicit Euler                                    |
| stiffness            | $k\in[0,1]$                    | compliance $\alpha$         | 탄성 에너지 weight                                |
| 적분기와 물성 의존성 | iterations와 $\Delta t$에 의존 | $\Delta t$에 의존           | 정해진 물리적 weight에 따름                       |
| 제어성               | 직관적                         | PBD와 비슷                  | weight 튜닝 필요                                  |
| 안정성               | 무조건 안정                    | 무조건 안정                 | 목적함수 단조 감소                                |
| 계산 구조            | Gauss-Seidel (or Jacobi)       | PBD와 동일 + $\lambda$ 하나 | local 병렬(Jacobi), global 직렬 back-substitution |
| hard constraint      | $k=1$                          | $\alpha=0$                  | 불가(soft만 가능)                                 |
| 순서 의존            | Gauss-Seidel이면 있음          | PBD와 동일                  | 없음(Jacobi)                                      |

정리하면 이렇다.
PBD는 constraint를 위치 projection으로 푼다는 한 가지 아이디어로 안정성과 제어성을 동시에 얻었지만, 그 대가로 강성이 solver 설정에 의존적인 값이 되면서 물성을 조절하기가 역으로 어려워졌다.
XPBD는 compliance로 강성에 물리 단위를 돌려주되 계산 구조는 PBD 그대로 유지했다.
PD는 반대편에서 내려와 implicit Euler를 local/global로 쪼개 병렬성과 상수 행렬을 얻었고, 그 과정에서 PBD가 global step을 생략해 물리적 성질을 잃었음을 보였다.

세 방법 모두 "constraint projection"이라는 같은 동작을 하고 있고, 갈리는 것은 그 동작을 어떤 목적함수의 어떤 solver로 해석하느냐다.
