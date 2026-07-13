# -*- coding: utf-8 -*-
"""
test_game.py
============
사람이 직접 콘솔에 입력하지 않고도 핵심 규칙들이 제대로 동작하는지
확인하기 위한 간단한 자동 테스트.
(정식 unittest는 아니고, assert로 빠르게 검증하는 스크립트)
"""

from game import Game
from board import Board


def mv(s):
    return Board.algebraic_to_pos(s)


def test_basic_moves_and_capture():
    game = Game()
    assert game.make_move(mv("e2"), mv("e4")) is True
    assert game.make_move(mv("e7"), mv("e5")) is True
    assert game.make_move(mv("g1"), mv("f3")) is True
    assert game.make_move(mv("b8"), mv("c6")) is True
    # 규칙에 안 맞는 수는 거부되어야 함 (백 나이트가 이미 옮겨졌는데 또 백 차례 아님)
    assert game.make_move(mv("f3"), mv("f3")) is False
    print("test_basic_moves_and_capture: OK")


def test_scholars_mate_checkmate_detection():
    """유명한 4수 체크메이트(Scholar's Mate)로 체크메이트 판정을 검증."""
    game = Game()
    moves = [
        ("e2", "e4"), ("e7", "e5"),
        ("f1", "c4"), ("b8", "c6"),
        ("d1", "h5"), ("g8", "f6"),  # 흑의 실수 수
        ("h5", "f7"),                # 체크메이트
    ]
    for f, t in moves:
        ok = game.make_move(mv(f), mv(t))
        assert ok, f"수 실패: {f}->{t}"
    assert game.status == "checkmate", f"체크메이트가 감지되지 않음: {game.status}"
    assert game.winner == "white"
    print("test_scholars_mate_checkmate_detection: OK")


def test_illegal_move_exposing_king_is_rejected():
    """킹이 체크에 노출되는 수는 합법 수 목록에 없어야 한다."""
    game = Game()
    # 폰을 옮겨서 비숍이 킹을 노릴 수 있는 상황을 만든다
    game.make_move(mv("e2"), mv("e4"))
    game.make_move(mv("d7"), mv("d5"))
    game.make_move(mv("f1"), mv("b5"))  # 비숍이 e8 킹 라인을 봄 (사실 c6 폰 막힘 없음 가정 단순화)
    # 여기서는 정교한 핀 상황을 만들기보다, get_legal_moves가 항상
    # '체크 안 걸리는 수만' 반환하는지 스모크 테스트로 확인
    for row in range(8):
        for col in range(8):
            piece = game.board.get_piece((row, col))
            if piece and piece.color == game.current_turn:
                for target in game.get_legal_moves((row, col)):
                    assert not game._move_leaves_king_in_check((row, col), target)
    print("test_illegal_move_exposing_king_is_rejected: OK")


def test_castling():
    """킹사이드 캐슬링이 정상적으로 되는지 확인."""
    game = Game()
    setup_moves = [
        ("g1", "f3"), ("g8", "f6"),
        ("g2", "g3"), ("g7", "g6"),
        ("f1", "g2"), ("f8", "g7"),
    ]
    for f, t in setup_moves:
        assert game.make_move(mv(f), mv(t)), f"셋업 수 실패: {f}->{t}"

    # 백 킹사이드 캐슬링: e1 -> g1
    assert (mv("g1")) in game.get_legal_moves(mv("e1")), "캐슬링이 합법 수 목록에 없음"
    assert game.make_move(mv("e1"), mv("g1")) is True
    king = game.board.get_piece(mv("g1"))
    rook = game.board.get_piece(mv("f1"))
    assert king is not None and king.symbol() == "K"
    assert rook is not None and rook.symbol() == "R"
    print("test_castling: OK")


def test_en_passant():
    """앙파상 캡처가 정상적으로 되는지 확인."""
    game = Game()
    setup_moves = [
        ("e2", "e4"), ("a7", "a6"),
        ("e4", "e5"), ("d7", "d5"),  # 흑이 d7->d5로 2칸 전진 (앙파상 조건 충족)
    ]
    for f, t in setup_moves:
        assert game.make_move(mv(f), mv(t)), f"셋업 수 실패: {f}->{t}"

    # 백 폰(e5)이 앙파상으로 d5의 흑 폰을 잡을 수 있어야 함 -> e5 x d6
    legal = game.get_legal_moves(mv("e5"))
    assert mv("d6") in legal, "앙파상 수가 합법 수 목록에 없음"
    assert game.make_move(mv("e5"), mv("d6")) is True
    assert game.board.get_piece(mv("d5")) is None, "앙파상으로 잡힌 폰이 제거되지 않음"
    print("test_en_passant: OK")


def test_promotion():
    """폰이 마지막 랭크에 도달하면 지정한 기물로 승진하는지 확인."""
    from pieces import Queen, King, Pawn, WHITE, BLACK

    game = Game()
    # 빠른 테스트를 위해 보드를 직접 세팅 (킹 2개 + 승진 직전 폰 1개만 남김)
    game.board.grid = [[None] * 8 for _ in range(8)]
    game.board.set_piece(mv("e1"), King(WHITE))
    game.board.set_piece(mv("e8"), King(BLACK))
    game.board.set_piece(mv("a7"), Pawn(WHITE))
    game.current_turn = "white"

    assert game.make_move(mv("a7"), mv("a8"), promotion_piece_cls=Queen) is True
    promoted = game.board.get_piece(mv("a8"))
    assert isinstance(promoted, Queen) and promoted.color == WHITE
    print("test_promotion: OK")


if __name__ == "__main__":
    test_basic_moves_and_capture()
    test_scholars_mate_checkmate_detection()
    test_illegal_move_exposing_king_is_rejected()
    test_castling()
    test_en_passant()
    test_promotion()
    print("\n모든 테스트 통과!")
