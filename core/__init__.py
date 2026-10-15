"""
Core module - コア機能
"""
from .state import bot
from .config import TOKEN

__all__ = ['bot', 'TOKEN']

# 停止中に期限を迎えた出品も、Discord 接続前に返却・保存する。
from .auction import expire_auctions
expire_auctions()
