"""Import all ORM model modules so relationship strings resolve.

Import this ONCE at app startup, before any DB usage.
"""
from src.modules.auth import models as _auth_models          # noqa: F401
from src.modules.student import models as _student_models    # noqa: F401
from src.modules.operator import models as _operator_models  # noqa: F401
from src.modules.admin import models as _admin_models        # noqa: F401