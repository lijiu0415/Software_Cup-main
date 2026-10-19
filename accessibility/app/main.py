# -*- coding: utf-8 -*-
"""
main.py —— 入口。构建官方布局，创建 App 引擎，进入官方主循环。
"""
from app.engine_layout import App, layout


def main():
    app = App(layout)
    app.mainLoop()


if __name__ == '__main__':
    main()
