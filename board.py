# -*- coding: utf-8 -*-
"""
board.py
========
체스판(Board)을 표현하는 파일.

체스판은 8x8 2차원 리스트(grid)로 표현하고, 각 칸에는
Piece 객체 또는 None(빈 칸)이 들어간다.

좌표 규칙: (row, col)
  - row=0 은 흑 진영 첫 줄(체스 표기로는 8랭크), row=7은 백 진영 첫 줄(1랭크)
  - col=0 은 a파일, col=7은 h파일
  이렇게 정한 이유: 콘솔에 출력할 때 위에서 아래로 자연스럽게 8랭크 -> 1랭크 순으로
  찍히도록 하기 위함. (algebraic notation과의 변환은 game.py/console_ui.py 에서 처리)

[중요] Board는 '규칙 판단'을 하지 않는다.
  - move_piece_raw() 는 체크/체크메이트 여부를 전혀 신경쓰지 않고 그냥 옮긴다.
  - "이 수가 합법인가?"는 Game 클래스(game.py)가 Board 를 이용해 판단한다.
  이렇게 분리해야 나중에 규칙이 추가/변경(변형증강체스)되어도 Board는 그대로 두고
  Game 쪽만 수정하면 된다.
"""

import copy
from pieces import Rook, Knight, Bishop, Queen, King, Pawn, WHITE, BLACK


class Board:
    def __init__(self):
        # 8x8 빈 보드를 만들고 초기 배치를 채운다.
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self._setup_initial_position()

    def _setup_initial_position(self):
        """표준 체스 초기 배치를 세팅한다."""
        back_rank_order = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]

        # row=0: 흑 백랭크, row=1: 흑 폰
        for col, piece_cls in enumerate(back_rank_order):
            self.grid[0][col] = piece_cls(BLACK)
            self.grid[1][col] = Pawn(BLACK)

        # row=6: 백 폰, row=7: 백 백랭크
        for col, piece_cls in enumerate(back_rank_order):
            self.grid[7][col] = piece_cls(WHITE)
            self.grid[6][col] = Pawn(WHITE)

    @staticmethod
    def in_bounds(pos):
        """좌표가 체스판 범위(0~7) 안에 있는지 확인."""
        row, col = pos
        return 0 <= row < 8 and 0 <= col < 8

    def get_piece(self, pos):
        row, col = pos
        return self.grid[row][col]

    def set_piece(self, pos, piece):
        row, col = pos
        self.grid[row][col] = piece

    def remove_piece(self, pos):
        self.set_piece(pos, None)

    def move_piece_raw(self, from_pos, to_pos):
        """
        규칙 검증 없이 그냥 기물을 옮기기만 하는 저수준 메서드.
        to_pos에 기물이 있었다면 그냥 덮어써지면서 캡처된다.
        캐슬링/앙파상처럼 '두 개의 기물이 동시에 움직이는' 특수 상황은
        game.py 에서 move_piece_raw를 두 번 호출하는 식으로 처리한다.
        """
        piece = self.get_piece(from_pos)
        self.set_piece(to_pos, piece)
        self.remove_piece(from_pos)
        if piece is not None:
            piece.has_moved = True

    def find_king(self, color):
        """해당 색깔 킹의 좌표를 찾아 반환. 못 찾으면 None (정상적으론 항상 있어야 함)."""
        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if isinstance(piece, King) and piece.color == color:
                    return (row, col)
        return None

    def is_square_attacked(self, pos, by_color):
        """
        pos 칸이 by_color 진영의 '어떤 기물'에게든 공격받고 있는지 확인.
        용도:
          1) 체크 판정 (내 킹 자리가 상대에게 공격받는가)
          2) 캐슬링 시 "킹이 지나가는 칸"이 공격받는지 확인
        여기서는 상대 기물들의 pseudo-legal move만 확인하면 충분하다.
        (재귀적으로 '그 수가 체크를 유발하는지'까지 검사할 필요는 없음)
        """
        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece is not None and piece.color == by_color:
                    if pos in piece.get_pseudo_legal_moves(self, (row, col)):
                        return True
        return False

    def clone(self):
        """
        보드를 깊은 복사(deep copy)한다.
        '이 수를 두면 우리 킹이 체크에 걸리는가?'를 시뮬레이션할 때
        실제 보드를 건드리지 않기 위해 가짜 보드에서 시험 삼아 둬보는 용도.
        """
        return copy.deepcopy(self)

    # ---- 좌표 <-> 체스 표기법(algebraic notation) 변환 헬퍼 ----
    @staticmethod
    def pos_to_algebraic(pos):
        """(row, col) -> 'e4' 같은 문자열로 변환."""
        row, col = pos
        file_letter = "abcdefgh"[col]
        rank_number = 8 - row
        return f"{file_letter}{rank_number}"

    @staticmethod
    def algebraic_to_pos(s):
        """'e4' 같은 문자열 -> (row, col) 튜플로 변환."""
        s = s.strip().lower()
        col = "abcdefgh".index(s[0])
        row = 8 - int(s[1])
        return (row, col)

    def print_board(self):
        """콘솔에 보드를 사람이 보기 좋게 출력한다. (디버깅/텍스트 플레이용)"""
        print("   +----------------------------------+")
        for row in range(8):
            rank_label = 8 - row  # row=0 -> 8랭크, row=7 -> 1랭크
            line = f" {rank_label} |"
            for col in range(8):
                piece = self.grid[row][col]
                cell = repr(piece) if piece else "."
                line += f"  {cell} "
            print(line + "|")
        print("   +----------------------------------+")
        print("      a   b   c   d   e   f   g   h")
