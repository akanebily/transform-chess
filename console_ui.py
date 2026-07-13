# -*- coding: utf-8 -*-
"""
console_ui.py
=============
텍스트(콘솔) 기반으로 체스를 플레이하기 위한 UI.

[왜 처음부터 그래픽(pygame 등)이 아니라 텍스트로 시작하나]
- game.py 의 규칙 로직이 진짜 제대로 동작하는지 빠르게 검증하기 위함.
- UI 코드는 Game 클래스가 제공하는 메서드(get_legal_moves, make_move 등)만
  사용하고 있으므로, 나중에 이 파일을 pygame 기반 GUI로 통째로 갈아끼워도
  board.py / pieces.py / game.py 는 전혀 손댈 필요가 없다.
  즉 "화면"과 "규칙"이 완전히 분리되어 있다는 걸 보여주는 예시이기도 하다.

사용법: 터미널에서 좌표를 algebraic notation으로 입력한다.
  예) e2 e4      (e2에서 e4로 이동)
  종료하려면 'quit' 입력.
"""

from game import Game
from board import Board
from pieces import Queen, Rook, Bishop, Knight


PROMOTION_MAP = {
    "q": Queen,
    "r": Rook,
    "b": Bishop,
    "n": Knight,
}


def ask_promotion_choice(color):
    """폰이 마지막 랭크에 도달했을 때 어떤 기물로 승진할지 콘솔에서 입력받는다."""
    while True:
        choice = input(
            f"  [{color}] 폰 프로모션! 승진시킬 기물을 고르세요 (q=퀸, r=룩, b=비숍, n=나이트): "
        ).strip().lower()
        if choice in PROMOTION_MAP:
            return PROMOTION_MAP[choice]
        print("  잘못된 입력입니다. q/r/b/n 중 하나를 입력하세요.")


def is_promotion_move(game, from_pos, to_pos):
    """이 수가 폰 프로모션을 유발하는 수인지 미리 확인 (입력받기 위해)."""
    piece = game.board.get_piece(from_pos)
    from pieces import Pawn
    return isinstance(piece, Pawn) and to_pos[0] in (0, 7)


def parse_input(user_input):
    """
    'e2 e4' 같은 입력을 (from_pos, to_pos) 튜플로 변환.
    입력 형식이 잘못되면 None을 반환.
    """
    parts = user_input.strip().split()
    if len(parts) != 2:
        return None
    try:
        from_pos = Board.algebraic_to_pos(parts[0])
        to_pos = Board.algebraic_to_pos(parts[1])
    except (IndexError, ValueError):
        return None
    if not Board.in_bounds(from_pos) or not Board.in_bounds(to_pos):
        return None
    return from_pos, to_pos


def run_console_game():
    game = Game()

    print("=" * 50)
    print(" 텍스트 체스 - 좌표 입력 예: e2 e4 / 종료: quit")
    print("=" * 50)

    while game.status == "ongoing":
        game.board.print_board()
        turn_kr = "백(White)" if game.current_turn == "white" else "흑(Black)"
        check_note = " (체크!)" if game.is_in_check(game.current_turn) else ""
        print(f"\n>> {turn_kr} 차례{check_note}")

        user_input = input("이동 입력 (예: e2 e4): ").strip()
        if user_input.lower() == "quit":
            print("게임을 종료합니다.")
            return

        parsed = parse_input(user_input)
        if parsed is None:
            print("!! 입력 형식이 잘못되었습니다. 'e2 e4' 형식으로 입력하세요.\n")
            continue

        from_pos, to_pos = parsed

        # 합법 수인지 먼저 확인 (에러 메시지를 더 정확히 주기 위함)
        legal_moves = game.get_legal_moves(from_pos)
        if to_pos not in legal_moves:
            print("!! 그 곳으로는 이동할 수 없습니다.\n")
            continue

        # 프로모션이 필요한 수라면 미리 어떤 기물로 승진할지 물어봄
        promotion_cls = Queen
        if is_promotion_move(game, from_pos, to_pos):
            promotion_cls = ask_promotion_choice(game.current_turn)

        game.make_move(from_pos, to_pos, promotion_piece_cls=promotion_cls)

        # ---- 미래 확장 지점 ----
        # 나중에 증강 기능을 넣으면 여기서 아래처럼 체크하면 된다:
        #   if game.pending_augment_choice:
        #       show_augment_selection_ui(game)
        #       game.pending_augment_choice = False

    # 게임 종료 후 최종 보드와 결과 출력
    game.board.print_board()
    if game.status == "checkmate":
        winner_kr = "백(White)" if game.winner == "white" else "흑(Black)"
        print(f"\n체크메이트! {winner_kr} 승리!")
    elif game.status == "stalemate":
        print("\n스테일메이트! 무승부입니다.")


if __name__ == "__main__":
    run_console_game()
