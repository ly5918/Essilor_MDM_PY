"""营业执照 OCR 识别服务层 — 与 Java 版 CmdOcrServiceImpl 完全对齐。

POC 阶段未接入真实 OCR 引擎：识别结果按测试素材（营业执照 license_01~08.png）
预置，上传哪张测试图就返回对应的识别结果，保证演示时「执照图片内容 ↔ 识别结果」一致；
文件名未匹配到测试图时回退默认素材（license_01），不会报错。

与 Java 版一致：recognize **不落库**（cmd_ocr_result 为空是预期行为，
流程轨迹的 OCR 步骤展示的是主档实际回填值，见 flow trace 服务）。
后续接入真实 OCR（阿里 / 百度 / 腾讯云等）时，只需替换本模块的识别实现，
Router 与前端契约无需改动。
"""
from __future__ import annotations

from typing import Dict, List, Optional


class _Sample:
    """测试素材原始数据（与 Java 版 CmdOcrServiceImpl.Sample 一一对应）。"""

    __slots__ = ("name", "credit_code", "type", "address", "province", "city",
                 "address_conf", "city_conf")

    def __init__(self, name: str, credit_code: str, type_: str, address: str,
                 province: str, city: str, address_conf: int, city_conf: int):
        self.name = name
        self.credit_code = credit_code
        self.type = type_
        self.address = address
        self.province = province
        self.city = city
        self.address_conf = address_conf
        self.city_conf = city_conf


# 默认测试图（文件名去扩展名），文件名未匹配到时返回该图的识别结果
DEFAULT_KEY = "license_01"

# 测试素材识别结果：文件名（去扩展名，小写）→ 素材数据（与 Java 版完全一致）
_SAMPLES: Dict[str, _Sample] = {
    "license_01": _Sample(
        "上海清视眼镜有限公司", "91310106MA1FL2X78K", "有限责任公司（自然人投资或控股）",
        "上海市静安区南京西路1266号恒隆广场二期28层", "上海市", "上海市", 93, 91),
    "license_02": _Sample(
        "苏州新视野光学科技有限公司", "91320594MA20TQ531H", "有限责任公司（自然人投资或控股）",
        "江苏省苏州工业园区星湖街328号创意产业园6栋A座", "江苏省", "苏州市", 95, 93),
    "license_03": _Sample(
        "广州明眸医疗器械有限公司", "91440101MA9UYB6L3D", "有限责任公司（自然人投资或控股）",
        "广东省广州市天河区天河路228号正佳广场东塔19层", "广东省", "广州市", 88, 90),
    "license_04": _Sample(
        "深圳星曜视光科技有限公司", "91440300MA5GQR8T2N", "有限责任公司（自然人投资或控股）",
        "广东省深圳市南山区海德三道199号天利中央广场A座22层", "广东省", "深圳市", 92, 94),
    "license_05": _Sample(
        "杭州澄明眼镜贸易有限公司", "91330106MA2B0X7K5W", "有限责任公司（自然人独资）",
        "浙江省杭州市滨江区江南大道588号恒鑫大厦15层", "浙江省", "杭州市", 94, 92),
    "license_06": _Sample(
        "南京视界供应链管理有限公司", "91320115MA1WC3Q9H3", "有限责任公司（自然人投资或控股）",
        "江苏省南京市建邺区江东中路108号万达中心B座9层", "江苏省", "南京市", 89, 91),
    "license_07": _Sample(
        "成都睛彩光学科技有限公司", "91510100MA6CQX2V8M", "有限责任公司（自然人投资或控股）",
        "四川省成都市高新区天府大道北段1700号环球中心E2区16层", "四川省", "成都市", 91, 93),
    "license_08": _Sample(
        "重庆朗目视光医疗管理有限公司", "91500103MA60J5D4R7", "有限责任公司（自然人投资或控股）",
        "重庆市渝中区邹容路68号大都会广场5栋18层", "重庆市", "重庆市", 93, 95),
}


def normalize_key(file_name: Optional[str]) -> str:
    """归一化文件名：去掉路径与扩展名后转小写（与 Java 版 normalizeKey 语义一致）。

    注意：用原生 rfind/切片而不是 os.path 工具，保证「无路径的文件名」不被误清空。
    """
    if not file_name or not file_name.strip():
        return ""
    name = file_name.strip().replace("\\", "/")
    slash = name.rfind("/")
    if slash >= 0:
        name = name[slash + 1:]
    dot = name.rfind(".")
    if dot > 0:
        name = name[:dot]
    return name.lower()


def _build_result(sample: _Sample) -> Dict[str, object]:
    """由测试素材构造识别结果（字段名与客户模型元数据 field_name 一致，供前端回填表单）。

    返回结构（snake_case，由 CamelCaseResponseMiddleware 统一转 camelCase）：
        {license: {credit_code, name, type, address},
         fields: [{code, field, value, confidence}]}
    """
    fields: List[Dict[str, str]] = [
        {"code": "legal_name", "field": "客户法定名称", "value": sample.name, "confidence": "98%"},
        {"code": "credit_code", "field": "统一社会信用代码", "value": sample.credit_code, "confidence": "99%"},
        {"code": "address", "field": "注册地址", "value": sample.address, "confidence": f"{sample.address_conf}%"},
        {"code": "province", "field": "省份", "value": sample.province, "confidence": "96%"},
        {"code": "city", "field": "城市", "value": sample.city, "confidence": f"{sample.city_conf}%"},
    ]
    license_vo = {
        "credit_code": sample.credit_code,
        "name": sample.name,
        "type": sample.type,
        "address": sample.address,
    }
    return {"license": license_vo, "fields": fields}


def recognize(file_name: Optional[str] = None) -> Dict[str, object]:
    """识别营业执照：按文件名匹配预置素材，未匹配到回退默认素材（license_01）。"""
    sample = _SAMPLES.get(normalize_key(file_name)) or _SAMPLES[DEFAULT_KEY]
    return _build_result(sample)


def recognize_of_customer(legal_name: Optional[str] = None,
                          credit_code: Optional[str] = None) -> Optional[Dict[str, object]]:
    """按客户反查预置素材（流程轨迹 OCR 步骤展示置信度用，与 Java 版语义一致）。

    优先按法定名称精确匹配，其次按统一社会信用代码；都未命中返回 None。
    """
    if legal_name:
        for sample in _SAMPLES.values():
            if legal_name == sample.name:
                return _build_result(sample)
    if credit_code:
        for sample in _SAMPLES.values():
            if credit_code == sample.credit_code:
                return _build_result(sample)
    return None
