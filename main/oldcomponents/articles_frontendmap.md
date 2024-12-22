### FE Roadmap

1.  Basic Tools: 개발 툴 설정

    1. Computer → MacOS, `Windows`, Linux

    2. Text Editor → `VS Code`, IntelliJ, Atom, Sublime Text

    3. Browser → `Chrome`, Edge, Safari, Firefox

    4. Terminal → Powershell, Bash, zsh

2.  Frone-end: FE 관련 지식 습득  
    너무 지나치게 붙잡고 있어도 안 되지만, 너무 소홀하면 다음 프레임워크에서 많이 무너질 수 있다.

        1. `HTML` → Structure

            1. HTML Tags → Tag 정보 습득

            2. Page Structure → 페이지 구조 설계

            3. Semantic Tags → 의미있는 태그

            4. <span style="background-color: rgba(235, 112, 112, 0.521)">SEO</span> → Search Engine Optimazation
            → 사용자가 특정 키워드로 검색할 때에 우리 사이트를 찾을 수 있게 신경써서 만드는 것이 중요.

            5. Accessibility → 접근성

        2. `CSS` → Presentation

            1. Basic

                1. Styling

                2. Layouts → Float, CSS Flex, Grid, etc.

                3. <span style="background-color: rgba(235, 112, 112, 0.521)">Responsive Design</span> → CSS Unit, Media Query

                4. <span style="background-color: rgba(235, 112, 112, 0.521)">Animation</span>

            2. Advanced

                1. `Architecture`

                    1. <span style="background-color: rgba(235, 112, 112, 0.521)">BEM</span> → Naming Rule
                    *BEM이 여전히 실무에서 유효한지 체크 필요*

                2. `Preprocessors` → 기존의 CSS 문법(반복 등의 문제)에서 벗어나 생산성 향상

                    1. Sass

                    2. Less

                    3. PostCSS → + 모듈화로 이름 충돌 방지

                3. `CSS Framework`

                    1. Bootstrap

                    2. PostCSS → 미리 만들어진 UI Component를 사용하는 것이 아니라,
                    CSS보다 조금 더 간편한 문법으로 UI Component마다 고립된 환경에서 작업할 수 있음.

                    3. <span style="background-color: rgba(235, 112, 112, 0.521)">Tailwind CSS</span> → Bootstrap처럼 지정된 클래스를 사용하면 쉽게 디자인 가능.

                    4. Material UI → React에서 이미 제작된 UI를 가져와서 사용 가능.

                    5. Styled-Components → JS 파일 안에 스타일을 변수처럼 정의해서 사용할 수 있음. CSS in JS

        3. `JavaScript` → Behavior

            1. Basic

                1. `ES6 + Syntax` → JS 문법 등.. how to implementation

                    1. Basic

                        1. let, const

                        2. if, for, switch, while


                        3. function

                        4. object

                    2. Advanced

                        1. Prototype

                        2. Hoisting

                        3. Scope

                        4. Closure

                2. `Browser APIs` → 존재와 사용 방법을 찾을 수 있는 수준의 능력.

                    1. DOM Manipulation

                    2. Events

                    3. Fetch API (Async)

            2. Advanced

                1. `TypeScript` → JS보다 안정성과 유지보수성이 높음.

                    1. Types

                    2. OOP

                2. `JavaScript Framework` → 개발자가 로직에만 집중할 수 있도록 나머지 작업을 보조. (Ex. 반복 제거)
                하나만 배우면 나머지는 쉽게 배움. 우선 하나 배우고 나머진 필요할 때마다 사용.

                    1. `React`

                    2. Vue

                    3. Angular

                    4. Svelte

                    → 여기까지 하면 Single Page Application (SPA)을 위한, Browser에서 동작하는 것만을 위한 것들.
                    SEO가 취약하거나 사용자가 웹페이지 보는 데에 시간이 오래 걸린다 등의 문제 발생.
                    아래 중 하나로 해결.

                3. Static Site Generation (SSG) → 서버에서 사이트를 미리 만들어 둠.

                    1. Gatsby (React)

                    2. GridSome (Vue)

                    3. 11ty (JS)

                4. Server Side Rendering (SSR) → 요청이 있을 때 사이트를 서버에서 만들어서 전송.


                    1. `Next.js` (React)

                    2. Nuxt.js (Vue)

                    3. Universal (Angular)

                    4. Sapper (Svelte)

3.  Tools: 생산성 향상 툴 학습

    1.  Version Control System

        1. Git → GitHub, Bitbucket, GitLab

    2.  Package Manager → 외부 라이브러리 설치 및 관리 가능. 둘 다 상호호환 가능.

        1. `npm`

        2. yarn

    3.  Module Bundler → 개발한 파일을 모두 그대로 사용자에게 제공하지 않고,  
        일부는 압축, 제외 등의 과정으로 작은 사이즈로 제공하는데, 여기서 사용.

            1. Webpack

            2. Rollup

            3. Parcel

            4. JSF

4.  Testing: 테스트 방법 학습

    1. Test Pyramid

       1. Jest

       2. Cypress

       3. Enzyme

       4. react-testing-library

    2. Good Test Principles

    3. CI/CD → 마지막 공부

5.  Publish: 배포

    1. Azure

    2. AWS

    3. Github Pages

    4. Netlify

    5. Vercel

    6. Heroku

2와 3은 병행하여 진행
