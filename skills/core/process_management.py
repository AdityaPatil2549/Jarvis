"""
skills/core/process_management.py - Process management skill.
Handles: SYSTEM_INFO

Source of truth: Implementation_plan.md §4.6
"""

from typing import List

from models import Intent, IntentType, ExecutionResult, ErrorType, ConversationContext
from skills.base import BaseSkill
from utils.logger import JarvisLogger


logger = JarvisLogger()


class ProcessManagementSkill(BaseSkill):
    """Handles system information and process management."""

    name = "process_management"
    version = "1.0.0"
    description = "System information and process management"

    def initialize(self) -> bool:
        return True

    def get_handled_intents(self) -> List[IntentType]:
        return [IntentType.SYSTEM_INFO]

    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        if intent.type == IntentType.SYSTEM_INFO:
            return self._get_system_info(intent, context)
        return ExecutionResult(success=False, message="Unknown process operation")

    def _get_system_info(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Get CPU, RAM, and disk usage."""
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            msg = (
                f"CPU: {cpu}%, "
                f"RAM: {mem.percent}% ({mem.used // 1024**3}GB used), "
                f"Disk: {disk.percent}%"
            )

            return ExecutionResult(
                success=True,
                message=msg,
                data={
                    'cpu_percent': cpu,
                    'ram_percent': mem.percent,
                    'ram_used_gb': round(mem.used / 1024**3, 1),
                    'ram_total_gb': round(mem.total / 1024**3, 1),
                    'disk_percent': disk.percent,
                }
            )

        except ImportError:
            return ExecutionResult(
                success=False,
                message="psutil not installed. Run: pip install psutil",
                error_type=ErrorType.SYSTEM_ERROR
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"System info failed: {e}",
                error_type=ErrorType.EXECUTION_FAILED
            )
