# Introduce

컴퓨터 그래픽스, Dynamics에 관심이 있는 학생입니다.

# Projects

## 1. ysim

C++, Metal 기반 시뮬레이션 엔진.

- GPU based simulation engine using Metal kernel
  - BVH build & query on GPU
  - Explicit simulation step
- Cache-friendly memory layout
  - Pack the scene data into a continuous
- Template-based classes
  - Easily extensible to other backends(CPU, CUDA)
  - Avoid polymorphism due to the vtable lookup.

무엇을 배웠나?

- GPU라고 무조건 다 빠른게 아님.
  - 사례: BVH construction의 사례에서 CPU로 먼저 구현 후 스텝 별로 GPU로 전환함. 여기서 GPU로 전환 후 오히려 느려지기도 하는 사례 발견.
  - 결론1: GPU도 병렬성이 높거나 작업량이 많은 등 특수한 경우에서 유의미하게 빠른 성능을 보임.
  - 결론2: Hybrid method가 좋을 수도 있다. (사례 검증 필)

## 2. Collision detection researches
