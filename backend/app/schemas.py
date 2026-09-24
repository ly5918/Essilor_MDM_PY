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
    # 提交人：审批详情「提交人」与流程跟踪「申请人」的数据源。
    # 前端未传时后端回落到默认业务角色（Business User），避免该列恒显示「-」。
    applicant_name: Optional[str] = None
    applicant_id: Optional[int] = None


class CustomerResubmit(BaseModel):
    """被退回申请的「修改重报」入参：全部字段可选，仅更新前端传入的非空项。

    业务口径（总设计两级审批）：BU Scope 初审退回 → 申请人（Business User）
    在「创建客户申请」修改后重报 → 再次进入 BU Scope 初审。重报时后端会
    用合并后的关键字段重新查重 / 重打 DQ 分，并同步重开审批任务与流程实例。
    """
    legal_name: Optional[str] = None
    legal_name_en: Optional[str] = None
    credit_code: Optional[str] = None
    short_name: Optional[str] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    remark: Optional[str] = None
    applicant_name: Optional[str] = None


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


class ChangeDiffItem(BaseModel):
    """字段级变更行（前端 ChangeRequestDialog 采集，camelCase 兼容）。

    Before 由服务端从主档当前值回填（与 UI 提示「服务端用主档当前值补全 Before」一致），
    前端只上传 fieldCode / fieldName / afterValue。
    """
    model_config = pydantic.ConfigDict(populate_by_name=True)

    field_code: str = Field(validation_alias=AliasChoices("fieldCode", "field_code"))
    field_name: Optional[str] = Field(None, validation_alias=AliasChoices("fieldName", "field_name"))
    after_value: str = Field("", validation_alias=AliasChoices("afterValue", "after_value"))


class ChangeSubmit(BaseModel):
    one_id: str
    change_type: str = "UPDATE"
    change_reason: Optional[str] = None
    bu_scope: Optional[str] = None
    target_status: Optional[str] = None
    is_key_change: Optional[str] = "N"
    effective_date: Optional[str] = None
    # 字段级变更明细：此前后端直接丢弃该入参，导致 cmd_change_diff 无数据、
    # 审批弹窗治理证据「没有修改的内容」（总设计要求 Before/After 证据链落库）。
    diffs: Optional[list[ChangeDiffItem]] = None


class ChangeResubmit(BaseModel):
    """被退回变更单「修改重报」入参（仅更新传入的非空字段）。"""
    change_reason: Optional[str] = None
    target_status: Optional[str] = None
    remark: Optional[str] = None
    applicant_name: Optional[str] = None


class MergeLaunch(BaseModel):
    survivor_one_id: str
    merged_one_id: str
    merge_type: Optional[str] = "MANUAL"
    reason: Optional[str] = None
