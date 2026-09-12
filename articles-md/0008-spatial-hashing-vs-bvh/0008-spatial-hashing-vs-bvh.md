---
title: Spatial hashing은 언제 BVH를 이기나 - 문헌 40편과 한 번의 정직한 후퇴
date: 2026.09
tag: Collision Detection
draft: true
math: true
---

대학원 연구 과목에서 "GPU에서 BVH를 이기는 spatial hashing broad phase"를 목표로 한 학기를 썼다. 문헌 40편을 훑고, 설계안을 하나 만들고, ysim에 LBVH baseline과 하이브리드를 구현해 재봤다. 결론은 "이긴다"가 아니라 "어느 사분면에서 이기는지 알게 됐다"이고, 그 사분면은 처음 생각보다 훨씬 좁았다. 이 글은 그 좁아지는 과정이다.

## 둘은 같은 일을 다르게 한다

BVH든 spatial hashing이든 결국 삼각형을 어떤 proxy geometry로 근사하고 어떻게 배치해서 충돌 아닌 쌍을 빨리 버리는 방법이다.

| | BVH | Spatial hashing |
|---|---|---|
| proxy geometry | 최소 AABB | 셀과 그 이웃(단일 레벨이면 3×3×3) |
| 결합 | tree, 계층적 overlap 허용 | grid, 셀 단위 |
| incremental | BVTT 같은 추가 구조와 메모리 필요 | 자연스러움(셀 드나든 것만 갱신) |
| 크기 편차 | tree가 흡수 | teapot-in-a-stadium 문제 |

그러니 발전 여지도 둘이다. Proxy geometry를 더 좋게 하거나, 결합 방식을 더 좋게 하거나(multi-level, hybrid). 내 두 설계 축이 정확히 이것이었다. Incremental 유지(temporal coherence로 저비용 갱신)와 multi-level(크기 편차를 다중 해상도로).

## 문헌이 그린 지형

40편을 놓고 보니 지형은 이랬다.

**두 축을 동시에 다룬 GPU 선행이 거의 없다.** Mirtich 1997(multi-resolution hash + coherence incremental, close-counter로 활성 쌍 유지 → from-scratch 대비 6~7배)과 Schornbaum 2009(hierarchical hash grid + boundary-crossing 갱신)가 둘 다 다룬 거의 유일한 사례인데 둘 다 CPU 직렬 설계다. GPU에서 가장 근접한 건 Fan et al. 2011(2-level grid + deferred update)인데 진짜 hash table이 아니라 grid고 레벨이 둘뿐이다. 여기가 gap이었다.

**이겨야 할 상대는 소프트웨어 BVH가 아니라 RT-core BVH다.** Mochi(2024)가 RT-core BVH로 Taichi의 uniform grid와 hash map을 둘 다 이겼다. "hashing이 BVH를 이긴다"를 말하려면 RT-core 대비 우위 논거가 있어야 하고, 그 우위는 거의 확실히 incremental 갱신 비용과 크기 편차 robustness다. RT-BVH가 약한 바로 그 두 축.

**정전(正典)은 정해져 있다.** Multi-level은 Mirtich → Eitz & Gu 2007(무한 계층, 파라미터 free) → Schornbaum 2009, GPU판 Fan 2011. Incremental은 SAP 계열(I-COLLIDE)과 coherence hashing(Mirtich). Hash 함수는 Teschner 2003의 $h=(x\cdot p_1\oplus y\cdot p_2\oplus z\cdot p_3)\bmod n$, $p=(73856093, 19349663, 83492791)$을 다들 재사용한다. 벤치마크 하니스는 Broadmark 2020이 있는데 단일 해상도 grid + 균일 박스라 크기 편차 시나리오는 직접 추가해야 한다.

## 설계, 그리고 정직한 후퇴 두 번

설계안(HACE-Grid)은 영속적인 multi-resolution sort-based hash를 dirty-region 편집으로 유지하는 것이었다. 4개의 후보 설계를 병렬로 만들고 심사해 합성한 뒤, 6개 관점의 적대적 검증을 돌렸다. 검증이 헤드라인 주장 두 개를 무너뜨렸고, 그게 이 설계에서 가장 값진 결과였다.

**후퇴 1: "incremental이 저비용 GPU rebuild를 이긴다"는 일반 주장 → 좁은 사분면으로 강등.** Karras-class GPU rebuild(radix sort + $O(N)$ scan)는 100만 객체에 약 430μs로 이미 운동과 무관하게 거의 최적이다. Incremental의 프레임당 고정 바닥(classify $O(N)$ + 커널 launch)이 rebuild의 약 0.37배라 break-even dirty fraction이 $f^*\approx0.6$이고, 진짜 배수 이득은 $f\ll0.1$에서만 난다. 즉 "거의 아무것도 안 움직이는" 씬에서만이다. 전체 시스템을 짓기 전에 Phase 0 실험으로 이걸 먼저 증명해야 하고, 실패하면 multi-level 단독으로 pivot해야 한다.

**후퇴 2: "RT-core BVH를 이긴다" → 철회.** RT refit 자체가 하드웨어 coherence 활용이고(불투명해서 갱신 불가라는 전제가 틀렸다), Mochi가 이미 proxy-sphere + symmetry로 크기 편차를 해결해 120:1에서 이겼다. 정직한 타깃은 compute-core 소프트웨어 baseline(LBVH, gProximity, BVH-OR)과 RT-core 없는 하드웨어다.

그래서 재정의된 기여는 이렇다. 프로그래머블하고 디버깅 가능하며, dirtying이 증명상 보존적이고(over-dirty, never under-dirty), 어디서나 compute rebuild의 약 1배로 bounded되며, flat proxy-sphere grid가 구조적으로 못 하는 cross-scale 도달성을 주는 broad phase. 이기는 사분면은 high-coherence + bimodal-size + no RT core다. 그리고 $N<10^5$면 그냥 rebuild가 낫고, 밀집 씬이면 영속 pair-set은 atomic hot-spot으로 자멸하니 stateless 재생성으로 가야 한다는 게이트가 설계의 최외곽에 붙었다.

## ysim에서 재본 것

설계는 설계고, ysim에는 LBVH baseline 위에 하이브리드를 둘 얹어 봤다.

**Sub-object BVH.** Mesh를 $k=4^s$개 그룹으로 나눠 그룹마다 bottom-up을 돌리고, 그 위는 tree가 아니라 flat cull이다(CPU sweep-and-prune 또는 GPU brute). 트리 깊이가 줄어 refit과 query가 싸질 거라 기대했는데, detect 시간은 $s$에 대해 U자였다.

| detect ms | single | s2 (16) | s3 (64) | s4 (256) | s5 (1024) | s6 (4096) | s7 (16384) |
|---|---|---|---|---|---|---|---|
| camel | 78.5 | 124.3 | 68.4 | 53.6 | **41.8** | 83.3 | 159.9 |
| human | 26.6 | 87.7 | 51.2 | 36.6 | **28.5** | 30.0 | — |

왼쪽 가지(s2가 최악)는 그룹 box가 크고 loose해서 cull이 약한 것이고, 오른쪽 가지(s7이 baseline의 2배)는 정확히 "top-level 탐색으로 흡수된 비용"이 지배로 넘어간 것이다. 깊이는 계속 얕아지는데 detect가 폭증한다. 그 비용이 CPU SAP의 직렬 스캔인지 (point, group) 후보쌍 폭증인지는 타이머가 하나로 뭉쳐 있어 데이터로 못 가른다. 타이머를 쪼개는 게 다음 일이다.

그리고 절대 ms를 그대로 비교하면 안 된다는 경고가 하나 나왔다. Human-c100 케이스에서 single은 broad pair 7.49M, sub-object는 18.0M이었다. Atomic append 순서가 궤적을 분기시켜(카오스) 워크로드 자체가 달라진 것이다. Pair당으로 정규화하면 sub-object가 살짝 이긴다. 절대 시간으로는 4배 나쁜데.

**Cluster + uniform grid.** 면 dual graph를 k-way로 클러스터링하고(Lloyd 6회), 클러스터 AABB를 uniform grid 셀에 CSR로 넣은 뒤 매 substep GPU에서 클러스터 쌍을 뽑아 짝지어진 subtree만 내려간다. 이게 ysim 안에서 "spatial subdivision이 tree 위에 얹힌" 유일한 경로다. Grid가 top level, BVH가 bottom level인 hybrid.

**Multi-level spatial hash.** 별도 경로로 존재하고 데모 씬 하나가 이걸 broad phase로 쓴다. 이 씬에서 BVH refit 슬라이더가 안 먹어서 한참 헤맸는데, 원인은 MLSH 경로의 `refit()`이 no-op이라서였다(grid는 매 detect마다 rebuild하니까). 노브가 죽어 있는 것과 안 먹는 것은 다른데 GUI는 구분해 주지 않았다.

## 그래서 언제 이기나

- $N$이 작으면($<10^5$) 이기지 못한다. Rebuild 고정비가 작아서.
- 밀집이면 이기지 못한다. 영속 구조가 atomic hot-spot으로 자멸한다.
- RT core가 있으면 이기지 못한다. Refit이 하드웨어다.
- 크기 편차가 크고 coherence가 높고 RT core가 없으면, 그리고 dirty fraction이 0.1 아래면 이긴다. 그리고 그 경우에도 "rebuild의 1배 이내"를 보장하는 게이트가 있어야 최악을 막는다.

문헌 조사가 준 가장 큰 것은 이 사분면의 경계였고, 설계 검증이 준 가장 큰 것은 그 경계가 내가 바라던 것보다 좁다는 사실이었다. 둘 다 코드를 짜기 전에 알아야 하는 것이었다.

> 확인 필요: 최종 보고서의 실험 1~4(refit vs rebuild, CPU vs GPU refit, atomic vs segmented broad phase, single vs multi-root) 수치는 이 글에 넣지 않았다. 보고서 PDF에서 옮겨올 것. 문헌 인용은 조사 노트(`문헌조사_GPU_Spatial_Hashing_충돌검출.md`) 기준이라 원문 재확인이 필요한 항목이 있을 수 있다.
