# 변형증강체스 - 1단계: 기본 체스 구현

## 폴더 구조

```
chess_game/
├── pieces.py       # 기물별 이동 규칙 (폰/나이트/비숍/룩/퀸/킹)
├── board.py        # 8x8 체스판, 저수준 이동/조회
├── game.py         # 턴 관리, 체크/체크메이트, 캐슬링/앙파상/프로모션
├── console_ui.py   # 텍스트(콘솔) 기반 UI
├── main.py         # 실행 진입점
├── test_game.py    # 자동 검증 스크립트
└── README.md
```

**왜 이렇게 나눴나:** 화면(UI)과 규칙(로직)을 완전히 분리했다.
`console_ui.py`는 `game.py`가 제공하는 함수(`get_legal_moves`, `make_move` 등)만
쓰기 때문에, 나중에 콘솔 대신 pygame 같은 그래픽 UI로 바꿀 때
`pieces.py` / `board.py` / `game.py`는 **전혀 건드릴 필요가 없다.**

## 실행 방법

```bash
cd chess_game
python3 main.py
```

이동은 `e2 e4` 형식(출발칸 도착칸)으로 입력. 종료는 `quit`.

## 테스트 실행

```bash
cd chess_game
python3 test_game.py
```

기본 이동/캡처, 체크메이트 판정(Scholar's Mate), 캐슬링, 앙파상, 프로모션을
자동으로 검증한다.

## 구현된 규칙

- 6개 기물 전부의 정상 이동 규칙
- 체크 판정 / 체크메이트 / 스테일메이트
- 캐슬링 (킹/룩 미이동, 사이 칸 비어있음, 체크 경유 안 함 조건 모두 확인)
- 앙파상
- 폰 프로모션 (승진 기물 선택 가능)

## 앞으로 "증강 선택" 기능을 붙일 때 (설계 미리 해둔 부분)

`game.py`의 `Game` 클래스에 이미 아래 확장 지점을 만들어뒀다:

- `self.halfmove_number`: 지금까지 둔 수의 개수 (N수마다 트리거할 때 사용)
- `self.move_log`: 기보 전체 기록
- `self.pending_augment_choice`: 이 값이 True가 되면 UI 쪽에서 게임을 멈추고
  증강 선택 화면을 띄우면 되는 신호 플래그
- `self.augment_trigger_every_n_moves`: N수마다 트리거하고 싶을 때 설정할 값
- `_on_move_completed()`: 매 수가 끝날 때마다 호출되는 훅. 여기에
  "N수 지났으면 pending_augment_choice = True" 같은 조건을 추가하면 됨
  (시간 기반 트리거를 원하면 `game_start_time`을 기록해두고 여기서 비교)

즉, 증강 기능을 넣을 때는:
1. `Game.__init__`에 시간/카운터 관련 필드 추가
2. `_on_move_completed()` 안에 트리거 조건 추가
3. UI(`console_ui.py`의 while 루프, 혹은 나중에 만들 GUI)에서 매 턴마다
   `game.pending_augment_choice`를 확인해서 True면 증강 선택 화면을 보여주기
4. 증강 효과 자체는 `Piece`에 속성을 추가하거나 `Game`에
   `active_augments` 같은 리스트를 두는 방식으로 구현

기존 `pieces.py`/`board.py`의 이동 계산 로직은 거의 안 건드리고
확장할 수 있도록 설계해뒀다.
