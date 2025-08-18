import curses
from datetime import datetime
from contextlib import suppress


class Terminal:
    logs: list[tuple[str, str, str]] = list()
    color: dict[int, int] = {
        1: curses.COLOR_GREEN,
        2: curses.COLOR_RED,
        3: curses.COLOR_YELLOW,
        4: curses.COLOR_CYAN,
        5: curses.COLOR_MAGENTA,
    }

    def __init__(self) -> None:
        curses.wrapper(self._initialize)

        if curses.has_colors():
            curses.start_color()

            for key, value in self.color.items():
                curses.init_pair(key, value, curses.COLOR_BLACK)

    def _initialize(self, stdsrc) -> None:
        self.stdscr = stdsrc
        self.height, self.width = self.stdscr.getmaxyx()

        self.logWindow = curses.newwin(self.height - 3, self.width, 0, 0)
        self.inputWindow = curses.newwin(1, self.width, self.height - 1, 0)

    def input(self, prompt: str = " > ") -> str:
        self.inputWindow.clear()
        self.inputWindow.addstr(0, 0, prompt)
        self.inputWindow.refresh()

        curses.echo()
        user_input = self.inputWindow.getstr(0, len(prompt)).decode("utf-8")

        curses.noecho()
        return user_input

    def console_log(self, message: str, level: str = "INFO") -> None:
        self.logs.append(
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                level,
                message,
            )
        )

        self.display_logs()

    def display_logs(self) -> None:
        curses.curs_set(0)
        self.stdscr.clear()
        self.logWindow.clear()

        for idx, (timestamp, _level, msg) in enumerate(
            self.logs if len(self.logs) < self.height - 3 else self.logs[len(self.logs) - (self.height - 3) :]
        ):
            with suppress(Exception):
                attr_color = 5

                if _level != "PLAIN":
                    self.logWindow.attron(curses.color_pair(1))
                    self.logWindow.addstr(idx, 0, timestamp)
                    self.logWindow.attroff(curses.color_pair(1))

                    if _level == "ERROR":
                        self.logWindow.attron(curses.color_pair(2))
                        attr_color = 2

                    elif _level == "WARNING":
                        self.logWindow.attron(curses.color_pair(3))
                        attr_color = 3

                    elif _level == "CHAT":
                        self.logWindow.attron(curses.color_pair(5))

                    self.logWindow.addstr(idx, len(timestamp) + 1, f"[{_level}] ")
                    self.logWindow.attroff(curses.color_pair(attr_color))

                    self.logWindow.attron(curses.color_pair(4))
                    self.logWindow.addstr(idx, len(timestamp) + len(_level) + 4, msg)
                    self.logWindow.attroff(curses.color_pair(4))
                    continue

                self.logWindow.attron(curses.color_pair(4))
                self.logWindow.addstr(idx, 0, msg)
                self.logWindow.attroff(curses.color_pair(4))

        self.logWindow.refresh()
