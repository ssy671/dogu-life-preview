# 귀여운 발견 운영

`content/discoveries.json`의 `items`는 의도적으로 비어 있습니다. 검증된 상품, 사용 경험, 사진 권리가 확보되기 전까지 상품을 등록하지 않습니다. 준비 화면의 그림은 직접 작성한 SVG이며 실제 상품을 묘사하지 않습니다.

향후 각 항목 필드:
- `id`: 고유 식별자
- `category`: `desk`, `keyboard`, `display`
- `experience`: 실제 사용한 `used` 또는 미사용 자료 조사인 `found`
- `title`, `summary`: 사실에 근거한 제목과 설명
- `source_url`: 확인한 HTTPS 원문/판매처 URL
- `checked_at`: 실제 자료 확인일 (`YYYY-MM-DD`)
- `pros`, `cons`: 확인한 특징/장점과 한계/단점 문자열 목록
- `usage_notes`: `used` 항목에 필수인 실제 사용 조건과 경험
- `affiliate`: 제휴 여부를 확인해 명시한 불리언

`found`는 사용 후기라고 표현하지 않으며 자료의 특징과 확인할 점으로 표시됩니다. 제휴 링크는 항목에 수수료 안내를 표시하고 `sponsored noopener noreferrer`를 적용합니다. 일반 출처도 새 탭 열림 안내와 `noopener noreferrer`를 사용합니다. 별점·가격·사진 필드는 아직 제공하지 않습니다. 광고 시스템과 기존 발행 큐에는 상품 항목을 섞지 않습니다.

검증: `python3 -m unittest discover -s tests -v`, `python3 scripts/build.py`, Playwright 설치 환경에서 `python tests/browser_check.py` 및 `python tests/browser_discoveries.py`.
