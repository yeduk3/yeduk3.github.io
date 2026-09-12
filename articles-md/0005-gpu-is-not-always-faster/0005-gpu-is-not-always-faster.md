---
title: GPU라고 다 빠르지 않다 - dispatch 고정비, sync floor, 그리고 직렬 구간
date: 2026.09
tag: Performance
draft: true
math: true
---

"이거 GPU로 올리면 빨라지나?"에 대한 내 답은 점점 "일량에서 고정비를 뺀 것이 양수인가"로 수렴하고 있다. 고정비는 세 종류다. Dispatch 한 번의 launch 비용, CPU가 GPU를 기다리는 sync 왕복, 그리고 알고리즘 안에 남아 있는 직렬 구간. 셋 중 하나라도 일량을 넘으면 GPU는 CPU보다 느리다. 몇 번 데인 사례를 모아 둔다.

## 사례 1: 0.44ms 아래는 보내지 마라

Gauss-Newton solver의 $\mathbf H=\mathbf J^T\mathbf J$ GEMM을 Eigen(NEON), Accelerate(AMX), MPS, 직접 짠 Metal 커널 2종으로 바꿔가며 $(m,n)$을 스윕했다. $m$은 residual 수(reduction 깊이), $n$은 파라미터 수(출력 $n\times n$)다.

Dispatch당 고정 비용이 약 0.44ms였다. $m=4096$에서는 GPU Jacobian이 CPU보다 느리다(0.24ms 대 0.02ms). 실작업이 1ms 미만이면 GPU로 보내지 말라는 뜻이다.

더 재미있는 건 shape였다. Poly 문제, $m=65536$:

| $n$ | Eigen GFLOP/s | Accelerate GFLOP/s | MPS GPU ms | simdgroup GPU ms | MPS/simd |
|---|---|---|---|---|---|
| 16 | 60 | 229 | 9.24 | 0.23 | 40.2× |
| 64 | 81 | 667 | 10.85 | 0.72 | 15.0× |
| 256 | 99 | 1696 | 14.85 | 7.06 | 2.1× |
| 1024 | 111 | 2105 | 79.23 | 100.41 | 0.8× |

MPS는 tall-skinny Gram matrix에서 무너진다. 출력 타일 단위로 병렬화하니 $16\times16$ 출력엔 타일이 하나뿐이고 threadgroup 하나가 길이 $m$짜리 reduction을 통째로 처리한다. 하드웨어가 아니라 스케줄링 문제다. 같은 GEMM을 reduction을 쪼갠 simdgroup 커널이 40배 빠르게, 그리고 더 정확하게 처리했다. $n=1024$에선 MPS가 1.3배 빠르니 shape로 디스패치해야 한다.

두 가지 교훈이 더 있었다. 하나, **비교 기준은 Eigen이 아니라 Accelerate다.** 단일 스레드 Eigen을 기준으로 재면 Metal이 실제보다 한 자릿수 좋아 보인다. $n=1024$에서 둘은 19배 차이다. 둘, **정확도 게이트가 먼저다.** 서로 다른 답을 내는 백엔드끼리 시간을 재는 건 비교가 아니다. fp64 레퍼런스로 채점하니 가장 빠른 Accelerate가 가장 부정확했고(worst 1.1e-4), 손으로 짠 Metal 커널이 가장 정확했다. 그리고 초기 split-K 커널은 $n\ge256$에서 정수 나눗셈으로 chunk 수가 1이 되어 스레드 하나가 최대 262,144항을 단일 fp32 running sum으로 누적했다. 최악 shape에서 11% 편차. GPU도 atomic도 아니고 누산 체인 길이가 원인이었다. 블록 누산(체인 64항 이하)과 결정적 combine으로 고쳤다.

## 사례 2: sync floor

Metal LBVH refit의 비용을 정점 수별로 쟀더니 1,024 정점에서 36ms, 499,849 정점에서 354ms였다. 일량은 500배인데 시간은 10배. 1,024 정점의 box union은 마이크로초 단위 작업이니 36ms는 거의 전부 refit 끝의 `commitAndWait`가 직전 dispatch들을 flush하며 기다리는 stall이다. 커널을 아무리 고쳐도 이 floor 밑으로는 못 내려간다. 고칠 것은 커널이 아니라 sync 위치였다. 자세한 건 BVH 글에 있다.

같은 함정이 CG에도 있다. Conjugate gradient는 SpMV + axpy + dot으로 구성돼 GPU 친화적으로 보이는데, dot product 두 개가 iteration마다 있다. Naive하게 결과를 CPU로 읽어 수렴 판정을 하면 iteration마다 sync가 걸리고, 0.1~0.3ms × 30 iteration이면 GPU가 더 느리다. CG 루프 전체를 GPU에 상주시켜야 한다. Reduction도 GPU 커널로, 수렴 판정은 고정 iteration 후 1회 sync이거나 indirect command buffer로 GPU 쪽에서 early-out. 이걸 못 하면 가속이 없다.

## 사례 3: 병목이라고 믿은 곳이 병목이 아니었다

"Large Steps(implicit Euler)와 PD의 sparse 연산을 Metal로 가속할 수 있나"라는 질문에 처음엔 "LS의 PCG는 가능, PD의 global step은 불가"라고 답했다. 후자는 맞았고 전자는 우선순위가 틀렸다.

먼저 잰 것이 맞았다. 옷감 정점 400에서 10,000까지 스윕한 결과(hang 씬, 콜라이더 없음):

| V | LS frame (ms) | LS assemble | LS PCG | PD frame | PD local | PD global |
|---|---|---|---|---|---|---|
| 400 | 18.8 | 11.4 | 2.4 | 15.6 | 6.1 | 3.2 |
| 2,025 | 82.3 | 61.9 | 14.3 | 29.0 | 10.6 | 12.1 |
| 10,000 | 386.4 | **318.1** | 59.5 | 137.8 | 41.4 | **88.7** |

LS의 지배 비용은 PCG가 아니라 **행렬 조립**이었다(82%). 매 substep 삼각형 19,602개 × 9×9 블록 → 160만 triplet → 정렬/합산 → sparse-sparse 3항 연산, 전부 단일 스레드 Eigen. 그런데 희소 패턴은 topology의 순수 함수라 매 substep 동일하다. 패턴을 mesh lifetime당 1회 만들고 값만 덮어쓰게 바꾸니 조립이 11~13배, 프레임이 2.0~5.8배 줄었다. GPU 코드 0줄. CG 반복수는 14케이스 전부 0.1 이내로 동일했으니 같은 연산자를 다르게 조립했을 뿐이라는 가장 강한 증거다. **그러고 나서야** PCG가 지배 비용이 됐고(70%), 이제 GPU 포팅 타겟이 CG가 됐다.

PD는 반대다. Global step이 prefactored LDLT의 삼각 back-substitution인데 이건 본질적으로 순차다. Level-set 스케줄링을 해도 병렬도가 얕고, Metal에는 sparse solver 라이브러리 자체가 없다(MPS는 dense만, Accelerate Sparse는 CPU). GPU 이득을 보려면 직접해법을 버리고 Chebyshev semi-iterative Jacobi 같은 반복법으로 가야 하는데, 그러면 지금 코드의 핵심 자산인 factorization 재사용 구조가 통째로 무의미해진다. 투자 대비 최악이다. Local step은 31%인데 이미 CPU 멀티코어라 GPU로 옮겨도 상한 1.45배다.

## 사례 4: CPU에서도 같은 원리다

Strategy pattern(가상 함수)과 template specialization의 오버헤드를 쟀더니 결과가 루프 모양에 따라 갈렸다. 원소끼리 독립인 throughput-bound 루프에선 5.6배 차이, $s=f(s,x_i)$처럼 직렬 의존 체인이면 1.00배. 가상 호출 자체는 싸고, 진짜 비용은 인라인과 벡터화를 막는 것이었다. Dispatch 비용이 FP latency 그늘에 숨으면 공짜다. GPU의 dispatch 고정비와 같은 구조다. 비용은 호출이 아니라 호출이 막는 것에서 나온다.

## 규칙으로

1. 실작업이 1ms 미만이면 GPU로 보내지 않는다. Dispatch 고정비가 0.4ms 안팎이다.
2. 커널 시간을 재기 전에 sync 위치부터 센다. Substep마다 sync가 있으면 그게 floor다.
3. 알고리즘에 직렬 구간이 있으면(삼각 solve, 순차 GS) 포팅이 아니라 알고리즘 교체가 선행이다.
4. 비교 기준은 최선의 CPU 구현이다. 단일 스레드 Eigen을 이기는 건 자랑이 아니다.
5. 정확도 게이트를 먼저 통과시킨다. 빠른데 틀린 백엔드는 비교 대상이 아니다.
6. Shape에 따라 디스패치한다. 같은 GEMM도 tall-skinny와 square는 다른 커널이다.
7. 그리고 무엇보다, 병목이라고 믿는 곳을 먼저 잰다. 조립이 82%인 시스템에서 CG를 GPU로 올려봐야 18% 안에서 노는 것이다.

> 수치 출처: GEMM은 `performance-test/03-eigen-vs-metal-gemm`(Apple M3), refit은 ysim `profiles/experiment/bvh-refit-2026-05-12`, LS/PD 스윕은 ysim `feat/large-steps-system` 브랜치 InFrame 계측, strategy/template은 `performance-test/01`.
