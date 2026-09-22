"""共享 DTO 与 RuoYi 风格响应信封 R.ok / R.fail。"""
from __future__ import annotations

from typing import Any, Optional
import pydantic
from pydantic import AliasChoices, BaseModel, Field


class R(BaseModel):
    code: int = 200
    msg: str = ""
    data: Any = None

    @classmethod
    def ok(cls, data: Any = None, msg: str = "操作成功") -> "R":
        return cls(code=200, msg=msg, data=data)

    @classmethod
    def fail(cls, msg: str = "操作失败", code: int = 500) -> "R":
        return cls(code=code, msg=msg, data=None)


# ---------- 客户提交 ----------
class CustomerSubmit(BaseModel):
    legal_name: str
    legal_name_en: Optional[str] = None
    credit_code: Optional[str] = None
    short_name: Optional[str] = None
    tax_no: Optional[str] = None
    customer_type: Optional[str] = None
    customer_level: Optional[str] = None
    product_line: Optional[str] = None
    bu_scope: Optional[str] = None
    payer_id: Optional[str] = None
    gc_scope_flag: Optional[str] = "N"
    country: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    source_system: Optional[str] = "MANUAL"
    cross_bu: Optional[bool] = False
    remark: Optional[str] = None


class ApprovalAction(BaseModel):
    """审批动作入参：兼容前端 camelCase（taskId/actionType）与后端 snake_case。

    前端 submitApprovalAction 发送 {taskId, actionType, opinion}，键名经
    AliasChoices 双风格绑定；动作值统一在路由层转小写（approve/reject/…）。
    """
    model_config = pydantic.ConfigDict(populate_by_name=True)

    task_no: str = Field(validation_alias=AliasChoices("task_no", "taskId", "task_id"))
    action: str = Field(validation_alias=AliasChoices("action", "actionType", "action_type"))
    actor: str = "demo"
    role: Optional[str] = None
    opinion: Optional[str] = None


class ChangeSubmit(BaseModel):
    one_id: str
    change_type: str = "UPDATE"
    change_reason: Optional[str] = None
    bu_scope: Optional[str] = None
    target_status: Optional[str] = None
    is_key_change: Optional[str] = "N"


class MergeLaunch(BaseModel):
    survivor_one_id: str
    merged_one_id: str
    merge_type: Optional[str] = "MANUAL"
    reason: Optional[str] = None
