# GitHub 아이디가 없는 무료 주소로 연결

Cloudflare Pages 계정 연결은 사용자가 Cloudflare 웹에서 한 번 진행해야 합니다. 이 저장소는 Cloudflare의 Git 연동 빌드를 지원하도록 준비되어 있습니다. 현재 GitHub Pages 주소도 유지됩니다.

## 새 Pages 프로젝트 설정

GitHub 저장소: `ssy671/dogu-life-preview`

| 항목 | 값 |
| --- | --- |
| 프로젝트 이름 | 원하는 이름. 사용 가능한 경우 `dogu-life` |
| 배포 브랜치 | `main` |
| 프레임워크 | `None` |
| 빌드 명령 | `python3 scripts/build.py` |
| 출력 폴더 | `docs` |
| 루트 폴더 | 저장소 루트 |

Pages가 제공하는 `CF_PAGES` 환경 변수를 감지하면 URL 경로가 `/`로 바뀝니다. 제목·검색·그림·개별 글·오늘 글의 링크는 새 호스트의 루트에서 동작합니다. GitHub Pages용 `/dogu-life-preview/` 경로는 기존 사이트에서 계속 사용합니다.

프로젝트 이름이 확정되면 Cloudflare의 production 환경 변수 `BLOG_SITE_URL`에 `https://실제프로젝트이름.pages.dev`를 설정합니다. 이는 검색엔진용 정규 주소에 사용합니다. 미설정 상태에서는 Cloudflare가 알려 주는 배포 URL을 사용합니다. 별도 API 키나 비밀번호를 저장소에 추가하지 않습니다.

## 무료 빌드 한도를 위한 변경 감지 범위

Cloudflare Pages 무료 요금제의 월 빌드 한도 때문에 매시간 변하는 조회수만으로는 새 빌드를 시작하지 않도록 설정합니다. build watch paths의 포함 경로를 다음으로 제한합니다.

```text
content/posts.json
scripts/build.py
docs/static/**
docs/about/**
docs/contact/**
docs/plan/**
```

`content/views.json`, `content/state.json`, `content/queue.json`, `docs/index.html`, `docs/data/**`, `docs/post/**`의 변경만 있는 커밋은 Cloudflare 빌드를 시작할 필요가 없습니다. 발행 글과 디자인 변경은 위 포함 경로에서 감지됩니다. 새 글 발행은 하루 한 번이며 수동 수정 시 빌드가 추가됩니다.

## 자동 발행과 조회수

매일 오전 9시(한국 시간)에 기존 GitHub Actions가 검토 글 세 편을 발행합니다. `content/posts.json`이 변경되면 연결된 Cloudflare 프로젝트가 새 글을 빌드합니다. 현재 검토 대기 원고는 45편(15일치)이며 소진 전에 보충해야 합니다.

조회수 수집은 기존 GitHub Actions에서 매시간 수행합니다. Cloudflare 페이지는 브라우저에서 공개된 조회수 스냅샷을 별도로 읽으므로 조회수 갱신만을 위한 사이트 재빌드가 필요하지 않습니다. 실패하면 빌드에 포함된 마지막 값으로 정렬합니다. 카운터 식별자는 기존 것을 유지해 조회수 이력을 보존합니다.

현재 검색 노출을 막는 `noindex` 설정은 그대로입니다. 새 주소가 확정되고 공개 운영을 결정한 뒤 검색 등록을 별도로 진행할 수 있습니다.
