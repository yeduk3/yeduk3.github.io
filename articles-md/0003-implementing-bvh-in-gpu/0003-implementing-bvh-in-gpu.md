---
title: GPU에서 돌아가는 BVH 구현하기
date: 2026.09
tag: Collision Detection
draft: true
math: true
# syndication: dev.to, Hashnode
# slug: custom-url-slug
# scripts: /static/js/demo-bvh.js
# styles: /static/css/demo-bvh.css
---

ysim의 옷감 충돌 broad phase는 Metal compute로 짠 LBVH다. 매 substep마다 정점이 움직이니 box를 다시 채워야 하고(refit), 가끔은 위상까지 다시 짜야 한다(rebuild). 이 글은 그 구현을 Karras 2012와 Apetrei 2014를 따라 어떻게 옮겼는지, 그리고 옮기고 나서 실제로 시간을 먹은 곳이 어디였는지에 대한 기록이다. 미리 말하면, 커널은 문제가 아니었다.

## 파이프라인

기본 경로는 Karras(2012)의 것이다.

1. **Morton code** - 삼각형 centroid를 $[0,1]^3$로 정규화하고 축당 10비트로 양자화해 30비트 코드를 만든다.
2. **Radix sort** - 코드 순으로 정렬. 정렬된 순서가 곧 leaf 순서다.
3. **buildTree** - 정렬된 코드에서 in-place binary radix tree를 만든다. Internal node $i$는 정렬된 key $i$와 $i+1$ 사이를 split하고, 각 thread가 독립적으로 자기 노드의 범위와 split을 결정한다.
4. **bottomUpBoxes** - Leaf에서 root로 올라가며 AABB를 채운다.

1번은 그대로 옮기면 된다. 비트를 3칸씩 벌리는 고전적 magic number 코드다.

```metal
inline uint expandBits(uint v) {
    v = (v * 0x00010001u) & 0xFF0000FFu;
    v = (v * 0x00000101u) & 0x0F00F00Fu;
    v = (v * 0x00000011u) & 0xC30C30C3u;
    v = (v * 0x00000005u) & 0x49249249u;
    return v;
}

inline uint mortonCode(const float3 point) {
    float3 p = min(max(point*1024.f, float3(0.f)), float3(1023.f));
    uint x = expandBits((uint)p.x);
    uint y = expandBits((uint)p.y);
    uint z = expandBits((uint)p.z);
    return x*4 + y*2 + z;
}
```

3번도 논문의 `determineRange`/`findSplit`를 그대로 쓴다. Leaf $i$는 슬롯 $N-1+i$에, internal node는 $0..N-2$에 두고, split 위치에 따라 child가 leaf인지 internal인지 정해 parent 배열을 같이 채운다.

## 심장은 bottomUpBoxes다

4번이 진짜 GPU다운 부분이다. Leaf당 thread 하나가 `treeParent`를 따라 root까지 올라가는데, 각 부모에서 `atomic_fetch_add(visitCount[parent], 1)`을 한다.

- 반환값이 0이면 먼저 도착한 것이다. 형제 box가 아직 없으니 thread를 죽인다.
- 반환값이 1이면 나중 도착이다. 두 자식 box가 모두 준비됐음이 보장되니 min/max를 합쳐 부모 box를 쓰고 조부모로 올라간다.

이러면 노드당 정확히 한 thread가 처리하고, 살아남는 thread가 레벨마다 절반으로 줄어 work $O(N)$, depth $O(\log N)$이 된다. Karras 논문의 두 번째 커널이 정확히 이것이다.

Metal에서 하나 다른 점은 memory ordering이다. MSL의 atomic은 `memory_order_relaxed`만 허용한다. 그래서 publication 경계마다 `atomic_thread_fence`를 두 군데 박아야 한다. 하나는 두 번째 도착이 확인된 직후, 자식 box를 읽기 전(형제 thread의 쓰기를 acquire). 다른 하나는 부모 box를 쓴 직후, 다음 루프의 atomic 전(내 쓰기를 release). `mem_flags::mem_device`에 `thread_scope_device`, `memory_order_seq_cst`로 두면 acquire와 release를 겸한다. 이걸 빼먹으면 대부분의 경우 잘 돌다가 큰 mesh에서 가끔 box가 비는 버그가 나온다.

```metal
// old == 1: sibling arrived first. Acquire its child-AABB writes.
atomic_thread_fence(mem_flags::mem_device, memory_order_seq_cst, thread_scope_device);
float3 lo = min(tree[childA].min, tree[childB].min);
float3 hi = max(tree[childA].max, tree[childB].max);
tree[parent].min = lo; tree[parent].max = hi;
// Release this parent-AABB write before the next atomic at the grandparent.
atomic_thread_fence(mem_flags::mem_device, memory_order_seq_cst, thread_scope_device);
```

Apetrei(2014)는 3번과 4번을 한 커널로 합친다. 노드가 올라가면서 parent를 찾는 동시에 box를 전파하는데, 범위 $[L,R]$인 노드의 parent 규칙은 $\delta(R)<\delta(L-1)$이면 $R$(자신은 childA), 아니면 $L-1$(childB)이다. 여기서 $\delta(i)$는 인접한 정렬 코드의 최상위 다른 비트다. Root가 임의의 슬롯에 떨어지므로 끝나고 슬롯 0으로 옮기는 커널이 하나 더 붙는다. ysim에서는 런타임 토글로 두 경로를 다 갖고 있는데, 얻은 것은 raw 속도보다 launch 수와 코드 단순화 쪽이었다.

## Refit은 rebuild의 절반이 아니라 가장 비싼 절반이다

Refit은 위상을 고정한 채 `buildLeaf`(현재 위치로 leaf box 재계산)와 `bottomUpBoxes`만 돌리는 것이다. Sort와 위상 생성을 아끼니 싸 보인다. 그런데 Karras 논문의 표를 보면 Turbine Blade 1.77M 삼각형에서 위상 생성이 1.28ms, box 채우기가 2.10ms다. Box-fit 커널이 빌드 중 가장 비싼 단일 커널이고, refit은 그걸 그대로 물려받는다.

그리고 실측은 그보다 더 나쁜 얘기를 했다. `--bench-bvh-refit` 하니스로 잰 refit 한 번의 비용이다(`profiles/experiment/bvh-refit-2026-05-12/refit_bench.csv`, 프레임당 10회 평균).

| method | 1,024 vtx | 10,000 vtx | 99,856 vtx | 499,849 vtx |
|---|---|---|---|---|
| FullGPU | 36.2 ms | 42.2 ms | 97.9 ms | 353.8 ms |
| FullCPU (구 경로) | ~37 ms | ~45 ms | ~175 ms | ~725 ms |

1,024 정점에서 36ms는 물리적으로 말이 안 된다. 2,047개 노드의 box union은 GPU에서 수 마이크로초짜리 작업이다. 정점이 500배 늘 때 시간이 10배만 느는 것도 같은 얘기다. 이 36ms는 거의 전부 refit 끝의 `commitAndWait`가 직전 substep의 적분 dispatch들을 flush하느라 기다리는 stall이다. **작은 N에서는 동기화 floor가 지배하고, 커널은 그 밑에 묻혀 있다.**

교훈은 명확했다. GPU BVH의 비용을 잴 때 "커널 시간"을 재고 있는지 "sync 위치까지의 시간"을 재고 있는지 먼저 구분해야 한다. 그리고 refit이 매 substep 한 번씩 sync를 내면 substep 60짜리 explicit 경로에서는 프레임당 60번 stall이다.

## Refit은 접촉과 무관한 고정비다

같은 씬(camel + cloth)에서 solver 네 개를 돌려 substep당 비용으로 정규화하면 refit이 얼마나 "고정"인지 보인다(`profiles/system-bottleneck-2026-08-09`).

| ms/substep | symplectic ×60 | PBD ×60 | PBD ×5 | PD ×5 | Large Steps ×5 |
|---|---|---|---|---|---|
| refit | 0.468 | 0.484 | 0.841 | 0.941 | 0.893 |
| broad pairs/substep | 10,056 | 3,500 | 15,836 | 7,108 | (7,108~15,836 사이, 정확한 값 확인 필요) |

Substep 수가 같은 세 CPU solver는 pair 수가 2.2배 벌어져도 refit이 10% 안에서 같다. 정점 수 × 노드 수의 함수지 접촉의 함수가 아니다. 반면 substep 5와 60은 거의 2배 차이가 나는데, 이건 프레임당 한 번 내는 고정비를 substep 수로 나누는 효과다. 프레임당 총합을 $F+n\cdot m$으로 피팅하면 refit은 $F=1.94$ms, $m=0.452$ms/substep이었다. 첫 substep 한 번의 비용으로 환산하면 warm의 5배쯤이다. 프레임 경계에서 render/imgui가 BVH 워킹셋을 캐시에서 밀어내는 그림과 크기가 맞는데, 확정하려면 첫 substep의 refit만 별도 섹션으로 재야 한다(`broad_refit_s0`). 아직 안 했다.

한 가지 더. "GPU BVH"라 부르는 경로의 절반은 CPU다. Swept AABB를 만드는 `enlargeTrajectory`는 기본 경로에서 순수 CPU 루프이고, refit의 두 번째 pass(object별 root box를 읽어 TLAS를 짜는 부분)도 CPU에서 돈다. 이걸 모르고 "GPU 커널이 CPU 작업과 겹쳐서 빠르다"고 해석했다가 프로파일로 반박당했다.

## Frozen topology의 품질 문제

Refit은 leaf box만 새로 계산하고 parent/child 링크는 절대 건드리지 않는다. 마지막 build 시점의 위상이 옷감이 아무리 접혀도 그대로 굳는다. 문제는 두 겹이다.

첫째, 시작 위상 자체가 좋지 않다. LBVH의 tree 품질은 SAH 기준으로 SweepSAH 대비 70% 근처에 그친다고 보고된다(Karras & Aila 2013, 문헌 조사 노트 기준이라 원표 재확인 필요). Refit은 처음부터 품질이 낮은 tree를 영구 보존한다.

둘째, 변형이 진행될수록 더 나빠진다. 옷감이 접히거나 self-contact가 생기면 원래 멀리 있던 leaf들이 한 subtree에 묶여 box가 비대해지고 query가 폭증한다. Collision-Streams 논문의 측정에 따르면 변형 cloth에서 refit 자체는 프레임의 7% 정도이고 나머지는 query다. 즉 frozen topology가 악화시키는 것은 refit 시간이 아니라 그 다음 query 시간이다.

문헌은 이걸 2006년에 이미 해결했다. RT-DEFORM(Lauterbach et al. 2006)의 방법이 표준이다. Build 시 노드별로 $SA(\text{parent})/(SA(c_0)+SA(c_1))$ 비율을 저장해 두고, 매 refit에서 새 비율과의 차이를 누적해 root에서 $(n-1)$로 정규화한다. 이 값이 임계(논문은 0.4)를 넘으면 full rebuild. ysim의 bottom-up pass에 누적 한 줄만 더하면 되는 센서인데, 지금은 이 센서 없이 10프레임마다 무조건 rebuild한다. 옷감 motion에서 정말 품질이 문제인지를 먼저 재 주는 장치라 다음에 붙일 첫 번째 것이다.

## "Substep마다 refit"은 자연법칙이 아니다

Symplectic 경로는 substep 60에 매 substep refit이라 프레임 103ms 중 충돌이 89ms였다. Substep당 충돌 비용 1.447ms는 네 solver 중 가장 쌌다. 코드가 느린 게 아니라 60번 부르는 게 느린 것이다.

이 지점에서 문헌이 가리키는 가장 큰 지렛대는 refit 커널 최적화도, implicit 전환도 아니었다. Small Steps(Macklin et al. 2019)는 collision detection을 **프레임당 1회**만 하고 전체 프레임 궤적을 현재 속도로 예측해 margin을 둔 contact set을 만든 뒤 모든 substep이 그것을 재사용한다. Hero cloth 150k particle에서 1 substep/30 iteration과 30 substep/1 iteration이 12.4ms 대 13.5ms로 같은 비용인 이유가 그것이다. 둘 다 detection은 프레임당 한 번이다. "Substep 많음 = refit 많음"은 적분기의 성질이 아니라 구현 선택이었다.

ysim에는 `refitSubstepPeriod`/`cdSubstepPeriod` 노브가 있고, PBD/XPBD 계열은 무조건 안정이라 이 분리를 감당한다. 다만 explicit 경로는 substep을 stability 때문에 쓰는지 collision 때문에 쓰는지부터 재야 한다. Stability-bound면 적분기를 바꿔야 하고, collision-bound면 적분기를 바꿔도 refit 횟수는 안 줄어든다.

## 정리

- Karras/Apetrei 커널 자체는 교과서적이고 옮기는 데 함정이 적다. Metal 고유의 함정은 relaxed-only atomic이라 fence를 직접 두어야 한다는 것 하나다.
- 시간을 먹은 곳은 커널이 아니라 `commitAndWait` 위치, CPU에 남은 pass, 프레임당 고정비, 그리고 refit을 부르는 횟수였다.
- 다음 순서는 sync 제거 → 품질 저하 센서 → refit을 substep에서 프레임으로 분리 → 그 다음에야 tree rotation이나 더 나은 초기 위상이다.

> 수치 출처: refit 벤치는 `profiles/experiment/bvh-refit-2026-05-12`, solver별 substep 정규화는 `profiles/system-bottleneck-2026-08-09`, 문헌 수치는 각 논문 표 인용. 전부 InFrame 프로파일(섹션별 sync 포함)이라 절대값은 부풀려져 있고 비중과 비교만 신뢰한다.
