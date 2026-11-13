# 귀여운 발견 운영

검증한 실제 출처가 있는 상품을 `content/discoveries.json`에 등록합니다. 직접 사용하지 않은 상품은 `found`로 표시합니다. 사진은 재사용 권한을 확인한 경우에만 게재하며, 권한 미확인 상품은 사진 없이 자료 조사로 소개합니다. 분류 그림은 직접 작성한 SVG이며 실제 상품을 묘사하지 않습니다.

각 항목 필드:
- `id`: 고유 식별자 (기존 식별자는 유지)
- `product_key`: 브랜드와 모델을 나타내는 안정적인 중복 방지 키. 판매처·색상·길이·크기 차이는 새 상품으로 세지 않음
- `category`: `desk`, `keyboard`, `display`
- `experience`: 실제 사용한 `used` 또는 미사용 자료 조사인 `found`
- `title`, `summary`: 사실에 근거한 제목과 설명
- `source_url`: 확인한 HTTPS 제조사/원문 URL
- `seller_url`: 선택 필드. 실제 확인한 HTTPS 판매 페이지 URL
- `price_note`: 선택 필드. 확인일의 옵션·통화·표시가격·배송비와 미확인 조건. `seller_url` 필수. 현재 결제금액 보장 아님
- `checked_at`: 실제 자료 확인일 (`YYYY-MM-DD`)
- `pros`, `cons`: 확인한 특징/장점, 사용 조건과 한계/미확인 사항의 문자열 목록
- `usage_notes`: `used` 항목에 필수인 실제 사용 조건과 경험
- `affiliate`: 확인된 제휴 `true`, 확인된 비제휴 `false`, 관계 미확인 `null`. 필드 생략 불가

`found`는 사용 후기라고 표현하지 않습니다. 판매처의 구매·리뷰 수는 표시 사실과 출처를 밝히며 독립적인 구매 검증으로 간주하지 않습니다. 배송, 재고, 사진 권한과 사용 경험을 추측하지 않습니다. 제휴 링크는 수수료 안내와 `sponsored noopener noreferrer`를, 일반 출처는 새 탭 안내와 `noopener noreferrer`를 사용합니다. `null`은 ‘제휴·협찬 관계 미확인’으로 표시합니다.

## 등록과 중복 검사

최신 main의 모든 항목과 제조사 모델명·별칭·정규화한 출처/판매처 URL을 대조합니다. 모델이 같으면 색상, 크기 또는 판매처가 달라도 재등록하지 않습니다. 코드 검증은 정규화한 `product_key`와 추적 매개변수를 제외한 URL의 중복을 거절합니다. 모델의 별칭이나 서로 다른 URL 여부는 조사자가 추가 확인하며, 동일 상품인지 불명확하면 보류합니다.

일일 탐색은 한국 시간 오전 9시에 실행하는 별도 자동화에서 적합한 새 상품 1개를 우선 찾습니다. 10만 원 이하의 귀엽고 실용적인 소품을 선호하며 손난로·책상 청소기·숫자 표시만 있는 시계는 제외합니다. AliExpress를 우선 확인하되 차단되면 제조사·확인 가능한 판매처를 사용합니다. 조건을 충족하는 새 상품이 없으면 등록하지 않습니다. 사용자가 운영 등록을 승인한 범위에서 매번 재승인을 요구하지 않습니다.

수정 직전에 main을 다시 읽고 기존 항목을 유지한 채 추가합니다. `content/discoveries.json`과 그 공개 사본 `docs/static/discoveries.json`을 같은 커밋에 동일한 내용으로 저장합니다. 공개 사본은 운영 데이터 확인과 기존 Cloudflare의 `docs/static/**` 변경 감지에 사용됩니다. 예상한 main SHA가 달라지면 최신 데이터를 다시 읽어 병합·중복 검사를 반복하고 강제 덮어쓰지 않습니다.

상품은 기존 글·발행 큐에 섞지 않습니다. 소스 push 배포는 `release_for_event('push')`로 글 발행을 건너뛰며 글·큐·발행 상태를 변경하지 않습니다. 기존 정기 글 발행의 일정과 일일 검사는 유지합니다. 상품 등록은 workflow_dispatch로 글 발행을 강제 실행하지 않고 소스 push 배포로 진행합니다.

검증: `python3 -m unittest discover -s tests -v`, `python3 scripts/build.py`. Playwright 환경에서 `python tests/browser_discoveries.py`는 로컬 빌드를 검사합니다. `BLOG_CHECK_URL=https://lifehint-daily.pages.dev/`를 지정하면 운영 화면의 상품, 링크, 미사용/관계 표시, 모바일 넘침을 검사합니다. 운영 배포 후 실제 페이지와 공개 JSON을 확인하고 성공 여부를 보고합니다.
