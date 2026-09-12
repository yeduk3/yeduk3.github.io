---
title: 같은 씬, 네 개의 솔버 - symplectic·PBD·PD·implicit의 병목은 다 달랐다
date: 2026.09
tag: Simulation
draft: true
math: true
---

ysim에는 옷감 solver가 넷 있다. GPU explicit(symplectic Euler), CPU PBD, CPU Projective Dynamics, 그리고 Baraff-Witkin식 implicit Euler(Large Steps). 같은 씬에서 넷을 돌리고 프로파일을 나란히 놓으면 뭐가 보일까 싶어 camel mesh 위에 옷감을 떨어뜨리는 씬으로 30프레임씩 잡았다. 결론은 "넷의 병목이 전부 다르다"인데, 거기 도달하기까지 계측을 세 번 고쳐야 했다. 그 과정이 결과보다 더 쓸 만해서 같이 적는다.

## 셋업

- 씬: camel-reference.obj 위 y=1에서 옷감 낙하. Broad phase는 LBVH, narrow는 point-triangle.
- symplectic은 substep 60(explicit이라 그 이하로는 발산), PBD/PD/Large Steps는 substep 5. PD는 local/global 16 iteration.
- 실제 렌더러, foreground, InFrame 프로파일(섹션마다 `commitAndWait`), 30프레임 평균.

## 계측을 세 번 고쳤다

**첫째, symplectic의 solver 시간 0.06ms는 허수였다.** GPU 적분 dispatch를 감싼 스코프 안에 sync가 없었다. Sync는 refit/detect/narrow 세 구간에만 있었고, 적분 커널의 실제 시간은 다음 substep에서 제일 먼저 sync하는 refit이 대신 기다리고 있었다. 스코프 안에 `commitAndWait` 한 줄을 넣자 `system_update`가 0.06 → 13.07ms로 나타났다.

그런데 내 예측은 틀렸다. "12ms가 refit 안에 숨어 있으니 진짜 refit은 33ms"라고 했는데, 실제로는 refit이 5%만 줄고 physics 총합이 11.5ms 늘었다. 그 12ms는 refit의 wall-clock **안**이 아니라 **옆**에 있었다. Substep N의 적분 커널이 substep N+1의 refit을 CPU가 인코드하는 동안 GPU에서 돌고 있었고, refit의 sync는 꼬리만 기다린 것이다. 따라서 (1) refit 열은 원래부터 거의 정직했고, (2) async 운용에서 GPU 적분 13ms는 CPU 인코드 뒤에 숨는 사실상 공짜였으며, (3) InFrame 프로파일은 symplectic에 +12.5%의 관측자 효과를 얹는다. 섹션 귀속은 InFrame으로, 절대 fps는 PerFrame으로 봐야 한다.

**둘째, refit 경로가 달랐다.** symplectic/PBD는 refit과 swept enlarge가 fused된 경로, PD/Large Steps는 legacy 2-pass였다. 통일하기 전까지는 비교 자체가 무효였다.

**셋째, 프레임당 비교는 무의미하다.** Substep이 12배 차이 나므로 substep당으로 정규화해야 한다. 그리고 정규화해도 "같은 시뮬레이션"이 아닐 수 있다. PD의 broad pair 수가 PBD의 21%였는데, 이유는 PD 옷감이 camel을 통과해 내려갔기 때문이었다. "PD 충돌이 제일 싸다"는 성능이 아니라 실패의 결과였다.

## 결과

계측을 고친 뒤의 표다(`profiles/system-bottleneck-2026-08-09`).

| | symplectic ×60 | PBD ×5 | PD ×5 | Large Steps ×5 |
|---|---|---|---|---|
| frame (ms) | 103.41 | 22.94 | 25.06 | 23.13 |
| 충돌 : 솔버 | 86 : 13 | 68 : 28 | 50 : 46 | 66 : 30 |
| 충돌 / substep (ms) | **1.447** | 2.576 | 2.117 | 2.535 |
| 솔버 / substep (ms) | 0.218 | 1.057 | **1.960** | 1.153 |

Substep당으로 보면 symplectic의 충돌 비용이 넷 중 가장 싸다. 코드가 느린 게 아니라 60번 부르는 게 느린 것이다.

병목은 넷이 다 달랐다.

- **symplectic**: physics의 98.9%가 충돌. Refit 28.08ms와 detect 26.63ms가 동률이고, swept enlarge 15.30ms가 그 다음이다. 그리고 enlarge는 GPU가 아니라 순수 CPU 루프였다. 레버는 refit 주기 → detect 주기 → substep 수 순.
- **PBD**: 접촉이 가장 많은데도(substep당 15.8k pair) 가장 빠르다. Detect가 최대 항목인데 주기를 늘리면 관통하니 못 늘린다.
- **Large Steps**: PBD와 프로파일이 거의 같다. 솔버 5.77ms 중 행렬 조립 2.35 + PCG 2.07. 조립이 반복해보다 비싸다는 게 의외였다(이건 나중에 sparsity 패턴 캐싱으로 11~13배 줄였다).
- **PD**: 유일한 솔버 바운드. `pd_global` 6.31ms가 physics의 30%로 단일 최대 항목. 16 iteration × 5 substep = 80회 back-substitution, 1회 0.079ms. Local step의 3.5배다. 직렬 희소 Cholesky back-substitution이 벽이다.

## Refit은 고정비, 그리고 프레임당 한 번 내는 비용이 있다

세 CPU solver의 refit/substep은 0.841 / 0.941 / 0.893ms로 10% 안에 있는데 pair 수는 2.2배 차이가 난다. Refit은 접촉과 무관한 고정비다. 그런데 substep 60인 symplectic은 0.468이다. 두 배 차이의 원인이 CPU 경합인지(CPU solver가 코어와 캐시를 갈아먹은 직후에 refit이 돈다), substep 밀도인지 가르기 위해 PBD를 substep 60으로 돌렸다.

| ms/substep | sym ×60 | PBD ×60 | PBD ×5 |
|---|---|---|---|
| refit | 0.468 | **0.484** | 0.841 |
| enlarge | 0.255 | **0.240** | 0.362 |
| solver | 0.218 | 0.698 | 1.057 |

PBD ×60은 CPU solver가 프레임당 41.88ms를 돌고 있는데(×5의 7.9배) refit이 symplectic과 3.4% 차이다. CPU 경합 가설은 죽었다. GPU DVFS 가설도 데이터가 반대로 간다(GPU 유휴가 0 → 0.698ms일 때 refit이 3.4% 오르는데 0.698 → 1.057ms에서 74% 뛴다. 유휴 길이에 선형이 아니다). 남는 설명은 **프레임당 1회성 고정비**다. `total = F + n·m`으로 피팅하면 refit $F=1.94$ms, enlarge $F=0.66$ms. Substep 5짜리 CPU solver 셋은 프레임당 2.6ms, physics의 13%를 여기서 잃는다. 프레임 경계에서 render/imgui/mesh upload가 BVH 워킹셋을 캐시에서 밀어내는 그림과 크기가 맞는데, 확정 실험(첫 substep의 refit만 별도 섹션으로 계측)은 아직 안 했다.

## 부수 발견: PBD에서 substep은 재질 노브다

PBD ×60은 성능 실험이었는데 옷감이 휘어지는 평판처럼 변했다. 원인은 PBD의 iteration 보정 $k'=1-(1-k)^{1/n}$이 Gauss-Seidel sweep 수만 보정하고 substep 수는 지수에서 빠져 있기 때문이다. 프레임당 실제 projection 횟수는 substep × iteration이니 5 → 60이면 유효 강성이 $1-(1-k)^{40}$에서 $1-(1-k)^{480}$으로 뛴다. 버그라 단정하진 않는다(Small Steps는 substepping을 강성 확보 수단으로 권장한다). 다만 iteration에는 주는 보호를 substep에는 안 주는 비대칭이고, 재질을 substep과 무관하게 하려면 지수를 substep × iteration으로 바꾸거나 XPBD compliance로 가야 한다. 그래서 위 PBD ×60의 detect/narrow 수치는 비교에 못 쓴다. 옷감이 뻣뻣해져 pair가 15.8k → 3.5k로 줄었으니 같은 시뮬레이션이 아니다. Refit/enlarge만 유효하고, 그게 판별의 근거였다.

## 정리

- 프로파일은 sync 위치가 정한다. 스코프 안에 sync가 없으면 그 시간은 다음 sync를 가진 스코프로 흘러간다. 그리고 sync를 넣으면 겹침이 사라져 총합이 는다. 두 모드를 역할별로 써야 한다.
- 비교는 substep당으로, 그리고 같은 시뮬레이션인지(pair 수, contact 수)부터 확인하고.
- 네 solver의 병목: symplectic은 호출 횟수, PBD는 detect, Large Steps는 조립, PD는 직렬 back-substitution. "어떤 solver가 빠른가"보다 "어떤 solver의 어디를 고칠 수 있는가"가 답에 가깝다.

> 수치 출처: `profiles/system-bottleneck-2026-08-09/` (CSV, analyze.py, report.html). InFrame 티어라 절대값은 부풀려져 있다.
