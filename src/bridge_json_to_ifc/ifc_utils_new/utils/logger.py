"""
logger.py - 統一ロギングシステム

グローバル変数 log_print_func を統一管理するためのモジュール
各モジュールでの使用方法:
    from bridge_bim.utils.logger import log_print, progress_print
"""

# モジュールレベルのグローバル変数
_log_func = None
_debug_mode = False


def set_log_func(func, debug_mode=False):
    """ログ関数とデバッグモードを設定

    Args:
        func: ログ出力に使用する関数（print互換）
        debug_mode: デバッグモードのON/OFF（デフォルト: False）
    """
    global _log_func, _debug_mode
    _log_func = func
    _debug_mode = debug_mode


def get_log_func():
    """現在のログ関数を取得"""
    return _log_func


def get_debug_mode():
    """現在のデバッグモードを取得"""
    return _debug_mode


def log_print(*args, **kwargs):
    """デバッグ用ログ出力関数（DEBUG_MODE時のみ出力）

    Args:
        *args: print関数と同様の引数
        **kwargs: print関数と同様のキーワード引数
    """
    if _log_func and _debug_mode:
        _log_func(*args, **kwargs)


def progress_print(*args, **kwargs):
    """進捗出力関数（常に出力）

    Args:
        *args: print関数と同様の引数
        **kwargs: print関数と同様のキーワード引数
    """
    if _log_func:
        _log_func(*args, **kwargs)


class BridgeLogger:
    """ロギング関数を統一管理するクラス（後方互換性用）"""

    _log_func = None
    _debug_mode = False

    @classmethod
    def set_log_function(cls, func, debug_mode=False):
        """ロギング関数を設定

        Args:
            func: ログ出力に使用する関数（print互換）
            debug_mode: デバッグモードのON/OFF
        """
        cls._log_func = func
        cls._debug_mode = debug_mode
        # モジュールレベルの変数も更新
        set_log_func(func, debug_mode)

    @classmethod
    def log(cls, *args, **kwargs):
        """ログを出力（デバッグモード時のみ）

        Args:
            *args: print関数と同様の引数
            **kwargs: print関数と同様のキーワード引数
        """
        if cls._log_func and cls._debug_mode:
            cls._log_func(*args, **kwargs)
        elif not cls._log_func and cls._debug_mode:
            print(*args, **kwargs)

    @classmethod
    def progress(cls, *args, **kwargs):
        """進捗を出力（常に出力）

        Args:
            *args: print関数と同様の引数
            **kwargs: print関数と同様のキーワード引数
        """
        if cls._log_func:
            cls._log_func(*args, **kwargs)
        else:
            print(*args, **kwargs)

    @classmethod
    def get_log_function(cls):
        """現在のロギング関数を取得"""
        return cls._log_func if cls._log_func else print


# 互換性のためのグローバル変数
log_print_func = None


def set_global_log_function(func, debug_mode=False):
    """グローバルロギング関数を設定（互換性用）

    Args:
        func: ログ出力に使用する関数
        debug_mode: デバッグモードのON/OFF
    """
    global log_print_func
    log_print_func = func
    BridgeLogger.set_log_function(func, debug_mode)
