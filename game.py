# -*- coding: utf-8 -*-
"""
game.py
=======
게임 전체 규칙과 진행(턴, 체크, 체크메이트, 캐슬링, 앙파상, 프로모션)을 관리하는 파일.

[여기가 핵심 이유]
board.py 와 pieces.py 는 "판"과 "기물 하나하나의 이동 규칙"만 안다.
반면 이 파일의 Game 클래스는 그 위에서:
  - 지금 누구 차례인가
  - 이 수를 두면 내 킹이 체크에 걸리는가 (그러면 그 수는 반칙)
  - 체크메이트/스테일메이트인가
  - 캐슬링/앙파상/프로모션 같은 "여러 기물 상태를 같이 봐야 하는" 특수 규칙
  - (미래) 일정 수/시간이 지나면 게임을 멈추고 증강을 선택하게 하는 훅
을 담당한다.

[미래 확장(변형증강체스)을 위한 설계]
- 매 수가 끝날 때마다 self._on_move_completed() 를 호출하도록 만들어뒀다.
  나중에 "N수마다 / N초마다 증강 선택" 기능을 넣을 때는
  이 메서드 안에서 조건을 검사해서 self.pending_augment_choice = True 같은
  플래그만 세우면 된다. Game 클래스의 다른 부분(이동 검증 로직 등)은
  전혀 손댈 필요가 없다.
- self.halfmove_number (지금까지 둔 하프무브 수)와 self.move_log(기보)를
  이미 기록하고 있으므로 "몇 수마다 증강" 조건은 바로 구현 가능하다.
- 시간 기반 트리거를 넣고 싶다면 self.game_start_time 같은 필드를 추가하고
  _on_move_completed 안에서 경과 시간을 체크하면 된다. (이 파일에 TODO로 표시해둠)
"""

from board import Board
from pieces import Pawn, Rook, Knight, Bishop, Queen, King, WHITE, BLACK


class Game:
    def __init__(self):
        self.board = Board()
        self.current_turn = WHITE          # 백이 항상 선공
        self.move_log = []                 # 지금까지 둔 수의 기록 (기보용)
        self.halfmove_number = 0           # 백/흑 한 번씩 두는 게 아니라 '한 쪽이 한 번 두면' +1

        # 앙파상 판정을 위해 "직전 수가 폰이 2칸 전진한 수였는지" 기록해둔다.
        # 값은 '앙파상으로 잡을 수 있는 대상 칸(=폰을 건너뛴 칸)' 좌표, 없으면 None.
        self.en_passant_target = None

        # 게임 종료 상태: "ongoing", "checkmate", "stalemate"
        self.status = "ongoing"
        self.winner = None  # 체크메이트일 때 승자 색

        # ---- 미래 증강 기능을 위한 확장 지점 (지금은 아무 동작 안 함) ----
        self.pending_augment_choice = False  # True가 되면 UI 쪽에서 게임을 멈추고 증강 선택 UI를 띄우면 됨
        self.augment_trigger_every_n_moves = None  # 예: 10으로 설정하면 10수마다 트리거 (지금은 미설정=비활성)

    # ------------------------------------------------------------------
    # 합법 수 계산
    # ------------------------------------------------------------------
    def get_legal_moves(self, pos):
        """
        pos에 있는 기물이 실제로 '합법적으로' 이동 가능한 좌표 리스트를 반환.
        pieces.py 의 get_pseudo_legal_moves() 는 체크 여부를 고려하지 않으므로,
        여기서 한 단계 더 걸러준다: "이 수를 두면 내 킹이 체크에 걸리는가?"
        + 캐슬링/앙파상 같은 특수 수를 추가한다.
        """
        piece = self.board.get_piece(pos)
        if piece is None or piece.color != self.current_turn:
            return []  # 빈 칸이거나 상대 기물이면 애초에 움직일 수 없음

        candidate_moves = piece.get_pseudo_legal_moves(self.board, pos)
        candidate_moves += self._get_special_moves(piece, pos)

        legal_moves = []
        for target in candidate_moves:
            if not self._move_leaves_king_in_check(pos, target):
                legal_moves.append(target)
        return legal_moves

    def _move_leaves_king_in_check(self, from_pos, to_pos):
        """
        '가짜 보드'에서 실제로 수를 둬본 뒤, 그 결과 내 킹이 체크 상태인지 확인.
        진짜 보드는 건드리지 않기 위해 board.clone() 으로 복제본을 사용한다.
        """
        trial_board = self.board.clone()
        moving_piece = trial_board.get_piece(from_pos)
        trial_board.move_piece_raw(from_pos, to_pos)

        king_pos = trial_board.find_king(moving_piece.color)
        if king_pos is None:
            return False  # 이론상 발생하지 않지만 방어적으로 처리

        return trial_board.is_square_attacked(king_pos, moving_piece.enemy_color)

    def _get_special_moves(self, piece, pos):
        """캐슬링, 앙파상처럼 '여러 상태를 같이 봐야 하는' 특수 수를 추가로 계산."""
        special_moves = []
        if isinstance(piece, King):
            special_moves += self._get_castling_moves(piece, pos)
        if isinstance(piece, Pawn):
            special_moves += self._get_en_passant_moves(piece, pos)
        return special_moves

    def _get_castling_moves(self, king, king_pos):
        """
        캐슬링 조건:
          1) 킹과 해당 룩이 한 번도 움직인 적 없어야 함
          2) 킹과 룩 사이 칸이 모두 비어있어야 함
          3) 킹이 현재 체크 상태가 아니어야 함
          4) 킹이 지나가는 칸(중간 칸 포함, 도착 칸까지)이 공격받고 있지 않아야 함
        """
        moves = []
        if king.has_moved:
            return moves

        row, col = king_pos
        enemy = king.enemy_color

        # 지금 이미 체크 상태면 캐슬링 불가
        if self.board.is_square_attacked(king_pos, enemy):
            return moves

        # 킹사이드(오른쪽, h파일 룩)와 퀸사이드(왼쪽, a파일 룩) 둘 다 검사
        for rook_col, step, king_target_col in [(7, 1, 6), (0, -1, 2)]:
            rook = self.board.get_piece((row, rook_col))
            if not isinstance(rook, Rook) or rook.color != king.color or rook.has_moved:
                continue

            # 킹과 룩 사이 칸들이 비어있는지 확인
            path_clear = True
            c = col + step
            while c != rook_col:
                if self.board.get_piece((row, c)) is not None:
                    path_clear = False
                    break
                c += step
            if not path_clear:
                continue

            # 킹이 지나가는 두 칸(현재 위치 제외, 도착 칸까지)이 공격받지 않는지 확인
            passes_through_check = False
            for c in (col + step, col + step * 2):
                if self.board.is_square_attacked((row, c), enemy):
                    passes_through_check = True
                    break
            if passes_through_check:
                continue

            moves.append((row, king_target_col))

        return moves

    def _get_en_passant_moves(self, pawn, pos):
        """직전 수가 상대 폰의 2칸 전진이었고, 내 폰이 그 옆에 있다면 앙파상 캡처 가능."""
        moves = []
        if self.en_passant_target is None:
            return moves

        row, col = pos
        direction = -1 if pawn.color == WHITE else 1
        target_row, target_col = self.en_passant_target

        # 내 폰이 앙파상 대상 칸의 좌우 대각선 방향에서 캡처할 수 있는 위치인지 확인
        if target_row == row + direction and abs(target_col - col) == 1:
            moves.append(self.en_passant_target)

        return moves

    # ------------------------------------------------------------------
    # 수 실행
    # ------------------------------------------------------------------
    def make_move(self, from_pos, to_pos, promotion_piece_cls=Queen):
        """
        실제로 수를 둔다. 합법이 아니면 False를 반환하고 아무것도 하지 않는다.
        promotion_piece_cls: 폰이 마지막 랭크에 도달했을 때 승진할 기물 클래스
                              (기본값은 퀸. UI에서 사용자가 고르게 할 수도 있음)
        """
        if self.status != "ongoing":
            return False  # 이미 끝난 게임이면 더 이상 수를 둘 수 없음

        legal_moves = self.get_legal_moves(from_pos)
        if to_pos not in legal_moves:
            return False

        piece = self.board.get_piece(from_pos)
        is_castling = isinstance(piece, King) and abs(to_pos[1] - from_pos[1]) == 2
        is_en_passant = (
            isinstance(piece, Pawn)
            and to_pos == self.en_passant_target
            and self.board.get_piece(to_pos) is None
            and from_pos[1] != to_pos[1]  # 대각선 이동인데 목표 칸이 비어있으면 앙파상
        )

        # ---- 실제 기물 이동 ----
        self.board.move_piece_raw(from_pos, to_pos)

        # 캐슬링이면 룩도 같이 옮겨줘야 함
        if is_castling:
            row = from_pos[0]
            if to_pos[1] == 6:  # 킹사이드
                self.board.move_piece_raw((row, 7), (row, 5))
            else:  # 퀸사이드
                self.board.move_piece_raw((row, 0), (row, 3))

        # 앙파상이면 '건너뛴' 상대 폰을 실제로 제거해야 함
        if is_en_passant:
            captured_row = from_pos[0]  # 잡히는 폰은 이동하는 폰과 같은 랭크에 있음
            captured_col = to_pos[1]
            self.board.remove_piece((captured_row, captured_col))

        # 폰 프로모션: 마지막 랭크에 도달하면 지정된 기물로 교체
        if isinstance(piece, Pawn) and to_pos[0] in (0, 7):
            self.board.set_piece(to_pos, promotion_piece_cls(piece.color))

        # 다음 앙파상 판정을 위해 '이번 수가 폰 2칸 전진이었는지' 갱신
        if isinstance(piece, Pawn) and abs(to_pos[0] - from_pos[0]) == 2:
            skipped_row = (from_pos[0] + to_pos[0]) // 2
            self.en_passant_target = (skipped_row, from_pos[1])
        else:
            self.en_passant_target = None

        # 기보 기록
        self.move_log.append((from_pos, to_pos, piece))
        self.halfmove_number += 1

        # 턴 넘기기
        self.current_turn = BLACK if self.current_turn == WHITE else WHITE

        # 체크메이트/스테일메이트 갱신
        self._update_game_status()

        # 미래 증강 기능 훅 (지금은 아무 동작 안 함, 아래 메서드 설명 참고)
        self._on_move_completed()

        return True

    def _update_game_status(self):
        """현재 턴 플레이어 기준으로 체크메이트/스테일메이트 여부를 갱신."""
        has_any_legal_move = self._has_any_legal_move(self.current_turn)
        king_pos = self.board.find_king(self.current_turn)
        enemy = BLACK if self.current_turn == WHITE else WHITE
        in_check = self.board.is_square_attacked(king_pos, enemy)

        if not has_any_legal_move:
            if in_check:
                self.status = "checkmate"
                self.winner = enemy
            else:
                self.status = "stalemate"
        else:
            self.status = "ongoing"

    def _has_any_legal_move(self, color):
        """color 진영이 둘 수 있는 합법 수가 하나라도 있는지 확인."""
        for row in range(8):
            for col in range(8):
                piece = self.board.get_piece((row, col))
                if piece is not None and piece.color == color:
                    if self.get_legal_moves((row, col)):
                        return True
        return False

    def is_in_check(self, color):
        """color 진영의 킹이 지금 체크 상태인지 여부."""
        king_pos = self.board.find_king(color)
        enemy = BLACK if color == WHITE else WHITE
        return self.board.is_square_attacked(king_pos, enemy)

    # ------------------------------------------------------------------
    # 미래 확장 지점 (변형증강체스 기능이 여기에 들어갈 예정)
    # ------------------------------------------------------------------
    def _on_move_completed(self):
        """
        매 수가 끝날 때마다 호출되는 훅.

        TODO(증강 기능 추가 시):
          - 수 기반 트리거:
              if self.augment_trigger_every_n_moves and \\
                 self.halfmove_number % self.augment_trigger_every_n_moves == 0:
                  self.pending_augment_choice = True
          - 시간 기반 트리거를 원하면 __init__에서 self.game_start_time = time.time()
            을 기록해두고, 여기서 경과 시간을 검사하면 된다.
          - self.pending_augment_choice 가 True가 되면, UI 쪽(콘솔이든 GUI든)에서
            매 턴 진행 전에 이 값을 확인해서 게임 진행을 멈추고 증강 선택 화면을
            보여준 뒤, 선택이 끝나면 False로 되돌리고 게임을 재개하면 된다.
          - '증강 효과'는 아마 Piece 객체에 속성을 추가하거나(예: extra_move_range),
            Game에 active_augments 리스트를 두는 식으로 구현하게 될 것이다.
            지금 구조에서는 두 방식 다 무리 없이 끼워넣을 수 있다.
        """
        pass
