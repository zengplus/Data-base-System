import sqlite3
import traceback

class StateMachine:
    """管理车辆状态流转：IDLE, PICKUP, OCCUPIED, REBALANCING"""
    VALID_TRANSITIONS = {
        'IDLE': ['PICKUP', 'REBALANCING'],
        'PICKUP': ['OCCUPIED', 'IDLE'], # 可以被取消变回IDLE
        'OCCUPIED': ['IDLE'],
        'REBALANCING': ['IDLE']
    }

    @classmethod
    def can_transition(cls, current_status, new_status):
        if current_status == new_status:
            return True
        return new_status in cls.VALID_TRANSITIONS.get(current_status, [])

    @classmethod
    def is_available_for_dispatch(cls, status):
        """只有纯粹的 IDLE 状态才可以接单"""
        return status == 'IDLE'

    @classmethod
    def is_available_for_rebalance(cls, status):
        """只有纯粹的 IDLE 状态才可以被重平衡"""
        return status == 'IDLE'
