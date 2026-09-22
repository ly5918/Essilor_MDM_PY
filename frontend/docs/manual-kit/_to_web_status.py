# -*- coding: utf-8 -*-
"""把本轮「客户状态更新（逻辑停用）」走查截图压成 web/*.jpg（宽 ≤1280 / q80），供手册内嵌。

命名使用 dact_ 前缀（与手册既有 39_/45_/52_ 等图号区分，避免与后续图重号）。
"""
import os
from PIL import Image

SRC = r"D:\Code\2026AI\AIA_MDM\Essilor_MDM\cmd-poc-e2e\shots_status"
WEB = r"D:\Code\2026AI\AIA_MDM\Essilor_MDM\plus-ui\docs\manual-kit\web"

PAIRS = [
    ("05_deactivate_approved.png", "dact_01_effect_button"),
    ("06_effect_confirm.png", "dact_02_effect_confirm"),
    ("08_customer_list_inactive.png", "dact_03_customer_inactive"),
]

# 清理上一轮误用的 54_/55_/56_ 前缀文件
for stale in ("54_deactivate_effect_pending.jpg", "55_deactivate_effect_confirm.jpg", "56_deactivate_customer_inactive.jpg"):
    p = os.path.join(WEB, stale)
    if os.path.exists(p):
        os.remove(p)
        print("removed stale", stale)

for src, name in PAIRS:
    im = Image.open(os.path.join(SRC, src)).convert("RGB")
    if im.width > 1280:
        im = im.resize((1280, int(im.height * 1280 / im.width)), Image.LANCZOS)
    out = os.path.join(WEB, name + ".jpg")
    im.save(out, "JPEG", quality=80, optimize=True)
    print("written", name + ".jpg", os.path.getsize(out) // 1024, "KB", im.size)
