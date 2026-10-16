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

조회수 수집은 기존 GitHub Actions에서 매시간 수행합니다. Cloudflare 페이지는 브라우저에서 공개된 조회수 스냅샷을 별도로 읽으므로 조회수 갱신만을 위한 사이트 재빌드가 필요하지 않습니다. 실패하면 빌드에 포함된 마지막 값으로 정렬합니다. 카운터 식별자는 기존 것을 유지해 조회수 이력을 보존합니다.

Pages의 `main` 배포는 검색 접근을 허용하며 `sitemap.xml`을 생성합니다. 다른 브랜치와 기존 GitHub Pages·Workers 배포는 검색을 차단하고 광고 코드를 포함하지 않습니다. 검색 허용이 즉시 검색 노출을 보장하지는 않습니다.

## 애드센스 연결

`content/site.json`의 `adsense_client`에는 공개 게시자 ID를, `contact_email`에는 공개 문의 이메일을 저장합니다. Pages의 `main` 배포에서 공통 헤드에 애드센스 스크립트와 계정 메타 태그를 넣고, 루트 `ads.txt`를 생성합니다. 소개·문의·개인정보 페이지도 동일한 레이아웃으로 생성합니다.

배포 후 `Check preview URL` 워크플로가 공개 Pages 주소에서 코드·메타 태그·ads.txt·검색 접근·사이트맵·문의·글과 그림을 검사합니다. 브라우저 검사는 광고 요청과 조회수 요청을 차단합니다.

애드센스 화면에서는 코드 삽입을 확인한 뒤 소유권 확인과 사이트 검토 요청을 진행합니다. 코드 연결과 광고 게재 승인은 별개입니다. 승인 후 실제 자동 광고 설정과 개인정보 보호 및 메시지의 동의 설정은 애드센스 계정에서 관리합니다.
