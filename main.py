# -*- coding: utf-8 -*-
"""
main.py
=======
프로그램 실행 진입점.
지금은 콘솔 UI로 실행하지만, 나중에 GUI(pygame 등)로 바꾸고 싶다면
이 파일에서 run_console_game() 대신 run_gui_game() 같은 함수를 호출하도록
바꾸기만 하면 된다. game.py / board.py / pieces.py 는 그대로 재사용 가능.
"""

from console_ui import run_console_game

if __name__ == "__main__":
    run_console_game()
