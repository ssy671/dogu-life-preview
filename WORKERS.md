# Cloudflare Workers에서 무료 정적 블로그 배포

Workers 애플리케이션 생성 화면을 사용하는 경우 이 설정으로 배포합니다. 정적 파일은 `wrangler.jsonc`가 지정한 `docs`에서 제공하며 별도의 서버 코드나 데이터베이스가 필요하지 않습니다.

| 화면 항목 | 값 |
| --- | --- |
| 프로젝트 이름 | `lifehint` |
| 빌드 명령 | `python3 scripts/build.py` |
| 배포 명령 | `npx wrangler deploy` |
| 미리보기 빌드 활성화 | 처음에는 끄기 |
| Cloudflare Access로 보호 | 끄기 |
| 고급 설정의 경로 | `/` |
| API 토큰 | 자동 생성 기본값 유지 |
| 추가 변수 | 최초 배포에는 입력하지 않아도 됨 |

Workers Builds가 제공하는 `WORKERS_CI`를 감지하면 글·그림·메뉴 링크를 루트 경로로 생성합니다. GitHub Pages에서는 기존 `/dogu-life-preview/` 경로를 계속 사용합니다.

주소는 `lifehint.<계정 서브도메인>.workers.dev` 형식입니다. 계정 서브도메인은 Cloudflare에서 변경할 수 있습니다. `lifehint.pages.dev`는 Pages 프로젝트의 주소 형식이며 이 Workers 배포에서 생성되는 주소가 아닙니다.

첫 배포 후 실제 공개 주소를 빌드 환경 변수 `BLOG_SITE_URL`에 설정합니다. 확정 전에는 정규 주소와 해당 주소를 사용하는 구조화 데이터를 추측해 만들지 않습니다. 기존 검색 수집 차단 설정은 공개 운영 준비 단계에서 따로 전환합니다.

조회수 집계만으로 불필요한 배포가 반복되지 않도록 Workers의 Build watch paths 포함 경로를 다음으로 제한하는 것을 권장합니다.

```text
content/posts.json
content/illustrations.json
scripts/build.py
wrangler.jsonc
docs/static/**
docs/about/**
docs/contact/**
```

매일 원고 세 편 발행은 기존 GitHub Actions가 처리하며 새 글 변경이 Workers 빌드를 시작합니다. 조회수는 브라우저에서 공개 스냅샷을 읽으므로 매시간 사이트를 재배포할 필요가 없습니다.

정적 자산 요청과 저장은 Workers의 무료 범위에 포함됩니다. 파일 수·파일 크기·빌드 시간에는 무료 한도가 있습니다.

- [정적 자산 구성](https://developers.cloudflare.com/workers/static-assets/binding/)
- [정적 자산 비용과 한도](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/)
- [빌드 설정](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)
- [Workers 주소](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/)
