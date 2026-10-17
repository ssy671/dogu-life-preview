# GitHub 아이디가 없는 무료 주소로 연결

Cloudflare Pages 계정 연결은 사용자가 Cloudflare 웹에서 한 번 진행해야 합니다. 이 저장소는 Cloudflare의 Git 연동 빌드를 지원하도록 준비되어 있습니다. 현재 GitHub Pages 주소도 유지됩니다.

## 새 Pages 프로젝트 설정

GitHub 저장소: `ssy671/dogu-life-preview`

| 항목 | 값 |
| --- | --- |
| 프로젝트 이름 | `lifehint-daily` |
| 배포 브랜치 | `main` |
| 프레임워크 | `None` |
| 빌드 명령 | `python3 scripts/build.py` |
| 출력 폴더 | `docs` |
| 루트 폴더 | 저장소 루트 |

Pages가 제공하는 `CF_PAGES` 환경 변수를 감지하면 URL 경로가 `/`로 바뀝니다. 제목·검색·그림·개별 글·오늘 글의 링크는 새 호스트의 루트에서 동작합니다. GitHub Pages용 `/dogu-life-preview/` 경로는 기존 사이트에서 계속 사용합니다.

공개 주소는 `https://lifehint-daily.pages.dev`입니다. `content/site.json`의 `production_url`을 정규 주소로 사용하므로, 해시가 붙은 개별 배포 주소가 검색 대표 주소로 들어가지 않습니다. `BLOG_SITE_URL` 환경 변수로 재정의할 수도 있습니다. 별도 API 키나 비밀번호를 저장소에 추가하지 않습니다.

## 무료 빌드 한도를 위한 변경 감지 범위

Cloudflare Pages 무료 요금제의 월 빌드 한도 때문에 매시간 변하는 조회수만으로는 새 빌드를 시작하지 않도록 설정합니다. build watch paths의 포함 경로를 다음으로 제한합니다.

```text
content/posts.json
content/illustrations.json
content/site.json
scripts/build.py
docs/static/**
docs/about/**
docs/contact/**
```

`content/views.json`, `content/state.json`, `content/queue.json`, `docs/index.html`, `docs/data/**`, `docs/post/**`의 변경만 있는 커밋은 Cloudflare 빌드를 시작할 필요가 없습니다. 발행 글과 디자인 변경은 위 포함 경로에서 감지됩니다. 새 글 발행은 하루 한 번이며 수동 수정 시 빌드가 추가됩니다.

## 자동 발행과 조회수

매일 오전 9시(한국 시간)에 기존 GitHub Actions가 검토 글 세 편을 발행합니다. `content/posts.json`이 변경되면 연결된 Cloudflare 프로젝트가 새 글을 빌드합니다. 검토 대기 원고 수는 `content/queue.json`에서 확인하고 소진 전에 보충해야 합니다.

조회수 수집은 기존 GitHub Actions에서 매시간 수행합니다. 실제 집계가 바뀐 경우에만 별도 `publication-state` 브랜치의 `content/views.json`을 저장합니다. 이 브랜치에는 조회수와 배포 상태 JSON만 두며, 사이트 소스가 있는 `main`에는 조회수 전용 커밋을 만들지 않습니다. 이전 GitHub Pages의 `main` 자동 배포도 조회수 변경으로 시작되지 않습니다.

상태 브랜치의 커밋 제목은 `[skip ci]`로 시작해 Cloudflare Pages·Workers의 빌드도 생략합니다. 홈페이지와 본문은 `https://raw.githubusercontent.com/ssy671/dogu-life-preview/publication-state/content/views.json`을 읽으므로 HTML을 매시간 다시 만들지 않습니다. 실패하거나 오래된 스냅샷이면 마지막 표시 값을 유지합니다. `main`의 조회수 JSON은 초기 표시를 위한 예비 값이며 최신 집계는 상태 브랜치에서 확인합니다. 카운터 식별자는 기존 것을 유지해 조회수 이력을 보존합니다.

09:00 발행과 매시간 점검은 같은 발행 잠금을 사용합니다. 오늘 이미 세 편을 발행했으면 원고를 추가로 소비하지 않습니다. 정기 실행은 새 글이나 실제 렌더링 입력이 바뀌었을 때만 전체 빌드·배포를 실행합니다. 소스 수정이나 수동 실행은 검증을 위해 한 번 전체 배포합니다.

상태 브랜치의 `content/deployment.json`은 마지막으로 실주소 검사를 통과한 버전을 기록합니다. 정기 실행은 이 파일을 먼저 읽고, 배포를 시작할 때 `pending`으로 바꿉니다. 두 호스트의 `data/build.json`이 예상 버전과 일치한 뒤에만 `verified`로 기록합니다. 배포나 검사가 실패하면 다음 정기 실행에서 다시 시도합니다. 조회수·대기 원고·생성된 HTML·생성된 도식의 변화는 배포 버전 계산에 포함하지 않습니다. 상태 브랜치 저장은 Git 객체를 직접 만들어 `main`의 체크아웃·스테이징을 바꾸지 않으며, 기존 브랜치 이력은 강제로 덮어쓰지 않습니다.

Pages의 `main` 배포는 검색 접근을 허용하며 `sitemap.xml`을 생성합니다. 다른 브랜치와 기존 GitHub Pages·Workers 배포는 검색을 차단하고 광고 코드를 포함하지 않습니다. 검색 허용이 즉시 검색 노출을 보장하지는 않습니다.

## 애드센스 연결

`content/site.json`의 `adsense_client`에는 공개 게시자 ID를, `contact_email`에는 공개 문의 이메일을 저장합니다. Pages의 `main` 배포에서 공통 헤드에 애드센스 스크립트와 계정 메타 태그를 넣고, 루트 `ads.txt`를 생성합니다. 소개·문의·개인정보 페이지도 동일한 레이아웃으로 생성합니다.

실제 배포 후에만 `Check preview URL` 재사용 워크플로를 한 번 호출합니다. GitHub Pages는 URL·그림·배포 버전을 확인하고, 공개 Pages 주소에서는 광고 코드·메타 태그·ads.txt·검색 접근·사이트맵·문의와 데스크톱·모바일 동작까지 확인합니다. 브라우저 설치와 전체 화면 검사는 공개 Pages에서만 수행하며, 광고 요청과 조회수 요청은 차단합니다.

조회수 전용 커밋의 빌드 생략은 [Pages 공식 안내](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/#skipping-a-build-via-a-commit-message)와 [Workers SDK의 지원 안내](https://github.com/cloudflare/workers-sdk/discussions/13216)를 따릅니다. 선택적으로 위 변경 감지 범위까지 설정하면 문서만 수정한 커밋의 Cloudflare 빌드도 줄일 수 있습니다. 이전 Workers 프로젝트의 자동 배포 자체를 완전히 끄는 설정은 해당 프로젝트의 Cloudflare Build 설정에서 관리합니다.

애드센스 화면에서는 코드 삽입을 확인한 뒤 소유권 확인과 사이트 검토 요청을 진행합니다. 코드 연결과 광고 게재 승인은 별개입니다. 승인 후 실제 자동 광고 설정과 개인정보 보호 및 메시지의 동의 설정은 애드센스 계정에서 관리합니다.
