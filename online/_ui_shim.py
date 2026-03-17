"""
Manila/online/_ui_shim.py
作为 ui 模块的替代品注入给 game.py，
将 game.py 中所有 ui.xxx() 调用透传给当前 _current_shim 实例。
"""
import sys

_current_shim = None

def __getattr__(name):
    if _current_shim is None:
        raise AttributeError(f'_ui_shim: shim 未初始化，无法调用 {name!r}')
    attr = getattr(_current_shim, name, None)
    if attr is None:
        # 返回空函数，忽略未实现的 show_* 等
        return lambda *a, **kw: None
    return attr
