"""
轻量日志模块 — 对应 C++ 的 Log/MiniLog.h
"""

import logging
import sys

_logger = logging.getLogger("OpenAR")
_logger.setLevel(logging.DEBUG)

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter(
    "[%(levelname)-5s] %(asctime)s | %(message)s",
    datefmt="%H:%M:%S"
))
_logger.addHandler(_handler)

def set_level(level: str):
    """设置日志级别: debug / info / warn / error"""
    _logger.setLevel(getattr(logging, level.upper(), logging.INFO))

def log_debug(msg: str):
    _logger.debug(msg)

def log_info(msg: str):
    _logger.info(msg)

def log_warn(msg: str):
    _logger.warning(msg)

def log_error(msg: str):
    _logger.error(msg)
