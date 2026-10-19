# -*- coding: utf-8 -*-
"""
window_control.py —— Windows 窗口前后切换（用户层，仅用于「单屏·前后切」排布）。

通过 Win32 API 控制 pygame 频闪窗的显示层级：
- bring_to_front：进入频闪页时，恢复并置顶频闪窗（盖住浏览器）。
- send_to_back：进入提示/学习页时，最小化频闪窗（露出浏览器）。

不触碰任何 SSVEP 频率/刺激实现，仅操作窗口显示。
"""
import ctypes

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SW_RESTORE = 9
SW_MINIMIZE = 6

user32 = ctypes.windll.user32


def get_hwnd(caption='ssvep demo'):
    """获取 pygame 窗口句柄：优先 pygame.display，失败则按标题查找。"""
    try:
        import pygame
        info = pygame.display.get_wm_info()
        hwnd = info.get('window')
        if hwnd:
            return int(hwnd)
    except Exception:
        pass
    try:
        hwnd = user32.FindWindowW(None, caption)
        if hwnd:
            return hwnd
    except Exception:
        pass
    return None


def bring_to_front(hwnd):
    """恢复并置顶频闪窗。"""
    if not hwnd:
        return
    try:
        hwnd = int(hwnd)
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        user32.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f'[win] bring_to_front 失败: {e}', flush=True)


def send_to_back(hwnd):
    """最小化频闪窗，露出浏览器。"""
    if not hwnd:
        return
    try:
        hwnd = int(hwnd)
        user32.ShowWindow(hwnd, SW_MINIMIZE)
    except Exception as e:
        print(f'[win] send_to_back 失败: {e}', flush=True)
