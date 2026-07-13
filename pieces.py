# -*- coding: utf-8 -*-
"""
pieces.py
=========
체스 기물(Piece)들을 정의하는 파일.

[설계 원칙 - 왜 이렇게 나눴나]
- 각 기물 클래스는 "이 위치에서 어디로 갈 수 있는가?"만 계산한다.
  (get_pseudo_legal_moves)
- "그 수를 두면 우리 편 킹이 체크에 걸리는가?" 같은 검증은 여기서 하지 않는다.
  그 책임은 game.py 의 Game 클래스가 가진다. (책임 분리)
  -> 기물 하나하나는 "이동 규칙"만 알고, 게임 전체 규칙(체크메이트 등)은 모른다.
- 이렇게 분리해두면 나중에 "변형증강체스"에서 새로운 기물(특수 능력 기물)을
  추가할 때, 이 파일에 Piece 를 상속받는 클래스 하나만 추가하면 된다.
  board.py, game.py 는 거의 건드릴 필요가 없다.
"""

from abc import ABC, abstractmethod

# 문자열을 직접 여기저기 쓰면 오타 나기 쉬우니 상수로 관리
WHITE = "white"
BLACK = "black"


class Piece(ABC):
    """모든 기물의 부모 클래스 (직접 사용하지 않는 추상 클래스)."""

    def __init__(self, color: str):
        self.color = color          # "white" 또는 "black"
        self.has_moved = False      # 캐슬링/폰 2칸전진 판정에 필요한 상태값

    @property
    def enemy_color(self):
        """상대 진영 색을 바로 알려주는 편의 프로퍼티."""
        return BLACK if self.color == WHITE else WHITE

    @abstractmethod
    def symbol(self) -> str:
        """콘솔 출력용 1글자 기호 (예: 폰='P', 나이트='N')."""
        raise NotImplementedError

    @abstractmethod
    def get_pseudo_legal_moves(self, board, pos):
        """
        이 기물이 '체크 여부를 고려하지 않은 상태에서' 이동 가능한 좌표들을 반환.

        Args:
            board: Board 객체 (board.py 의 Board)
            pos: (row, col) 현재 위치

        Returns:
            [(row, col), ...] 이동 가능한 좌표 리스트
        """
        raise NotImplementedError

    def __repr__(self):
        # 콘솔에 보드 찍을 때 쓰는 표현. 백은 대문자, 흑은 소문자로 구분.
        s = self.symbol()
        return s.upper() if self.color == WHITE else s.lower()


def _slide(board, pos, directions):
    """
    룩/비숍/퀸처럼 '한 방향으로 쭉 미끄러지는' 기물들이 공유하는 이동 계산 로직.

    directions: [(dr, dc), ...] 형태의 방향 벡터 리스트
    각 방향으로 계속 진행하다가
      - 보드 밖으로 나가면 멈춤
      - 아군 기물을 만나면 그 직전 칸까지만 이동 가능(그 칸은 불가)
      - 적군 기물을 만나면 그 칸까지는 이동(캡처) 가능하고 거기서 멈춤
    """
    from_row, from_col = pos
    piece = board.get_piece(pos)
    moves = []

    for dr, dc in directions:
        r, c = from_row + dr, from_col + dc
        while board.in_bounds((r, c)):
            target = board.get_piece((r, c))
            if target is None:
                moves.append((r, c))
            else:
                if target.color != piece.color:
                    moves.append((r, c))  # 캡처는 가능
                break  # 기물을 만났으니 이 방향은 더 못 감
            r += dr
            c += dc

    return moves


class Pawn(Piece):
    """
    폰.
    주의: 앙파상(en passant)은 '직전 수'라는 게임 전역 정보가 필요하므로
    여기서는 처리하지 않고 game.py 의 Game 클래스에서 특수 규칙으로 추가한다.
    프로모션(승진)도 마찬가지로 게임 로직 쪽에서 처리한다.
    """

    def symbol(self):
        return "P"

    def get_pseudo_legal_moves(self, board, pos):
        row, col = pos
        moves = []
        # 백은 위쪽(row 감소 방향)으로, 흑은 아래쪽(row 증가 방향)으로 전진
        direction = -1 if self.color == WHITE else 1
        start_row = 6 if self.color == WHITE else 1

        # 1칸 전진 (앞이 비어있을 때만)
        one_step = (row + direction, col)
        if board.in_bounds(one_step) and board.get_piece(one_step) is None:
            moves.append(one_step)

            # 2칸 전진: 시작 위치에 있고, 1칸 전진도 비어있었을 때만
            two_step = (row + direction * 2, col)
            if row == start_row and board.get_piece(two_step) is None:
                moves.append(two_step)

        # 대각선 캡처 (양쪽)
        for dc in (-1, 1):
            capture_pos = (row + direction, col + dc)
            if board.in_bounds(capture_pos):
                target = board.get_piece(capture_pos)
                if target is not None and target.color != self.color:
                    moves.append(capture_pos)

        return moves


class Knight(Piece):
    def symbol(self):
        return "N"

    def get_pseudo_legal_moves(self, board, pos):
        row, col = pos
        piece = board.get_piece(pos)
        offsets = [
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1),
        ]
        moves = []
        for dr, dc in offsets:
            target_pos = (row + dr, col + dc)
            if board.in_bounds(target_pos):
                target = board.get_piece(target_pos)
                if target is None or target.color != piece.color:
                    moves.append(target_pos)
        return moves


class Bishop(Piece):
    def symbol(self):
        return "B"

    def get_pseudo_legal_moves(self, board, pos):
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        return _slide(board, pos, directions)


class Rook(Piece):
    def symbol(self):
        return "R"

    def get_pseudo_legal_moves(self, board, pos):
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        return _slide(board, pos, directions)


class Queen(Piece):
    def symbol(self):
        return "Q"

    def get_pseudo_legal_moves(self, board, pos):
        directions = [
            (-1, -1), (-1, 1), (1, -1), (1, 1),  # 비숍 방향
            (-1, 0), (1, 0), (0, -1), (0, 1),    # 룩 방향
        ]
        return _slide(board, pos, directions)


class King(Piece):
    """
    킹. 여기서는 '한 칸 이동'만 계산한다.
    캐슬링은 (1) 킹/룩이 안움직였는지 (2) 사이 칸이 비었는지
    (3) 지나가는 칸이 공격받지 않는지 등 게임 전역 정보가 필요하므로
    game.py 의 Game 클래스에서 특수 규칙으로 별도 추가한다.
    """

    def symbol(self):
        return "K"

    def get_pseudo_legal_moves(self, board, pos):
        row, col = pos
        piece = board.get_piece(pos)
        moves = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                target_pos = (row + dr, col + dc)
                if board.in_bounds(target_pos):
                    target = board.get_piece(target_pos)
                    if target is None or target.color != piece.color:
                        moves.append(target_pos)
        return moves
