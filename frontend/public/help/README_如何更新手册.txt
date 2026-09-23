【操作手册更新方法】
1. 手册最新版在 docs/Essilor_CMD_POC_全功能操作手册.html（由 docs/manual-kit/build_manual.py 生成）。
2. 把它复制覆盖本目录的 cmd-poc-manual.html 即可，系统顶栏「操作手册」按钮和头像下拉里的「操作手册」菜单会立即展示新版（生产构建时该文件会随 dist 一起发布）。
3. 不需要改任何前端代码。

（注：以上路径相对 frontend/ 目录，即 frontend/docs/、frontend/docs/manual-kit/。）


【用户手册（Python 版）更新方法】
用户手册是脚本生成的，不要手写 HTML，改脚本后重新生成：

1. 生成脚本：项目根目录 _build_user_manual.py
2. 输出文件：frontend/public/help/cmd-poc-user-manual.html（头像下拉「用户手册」入口，URL /help/cmd-poc-user-manual.html）
3. 截图目录：manual-src/shots/*.jpg（playwright 走查脚本实拍；压缩后的网页版缓存在 manual-src/shots_web/）
4. 运行命令（必须用装了 Pillow 的解释器，cmdpy venv 没有 PIL 会 ModuleNotFoundError）：

   cd D:/Code/2026AI/AIA_MDM/Essilor_MDM_PY
   "C:/Users/Leo/.workbuddy/binaries/python/envs/default/Scripts/python.exe" _build_user_manual.py

5. 结构约定（与《全功能操作手册》版式一致）：
   - 用 part('partN', '标题', '导语') 开一章，用 sub('partN-M', 'M. 小节标题', ...blocks) 加小节；
     侧栏两级目录与正文由同一份 PARTS 结构自动生成，不需要手工维护目录。
   - 正文里加图片用 fig('截图文件名.jpg', '图注')，加表格用 table([表头], [[单元格...]])，
     加提示条用 tip() / warn() / info()，内联示意图用 svg_fig(svg代码, '图注')。
6. 版式要点（对齐操作手册，勿随意改）：
   - 配色 --brand:#14508c / --brand2:#1d6ab5，深色侧栏 #0f2c49（300px，sticky）。
   - <img> 必须带 width/height（fig() 已自动写入）：懒加载图片未解码时高度为 0，
     会让目录锚点跳转落点偏移。
   - 锚点只能设 scroll-margin-top（section/.sec-title/.body-h2 已设 64px），
     不要再给 html 加 scroll-padding-top，两者会叠加成双倍偏移。

【手册渲染自检】
改动手册后建议跑一遍渲染校验（打开页面、点目录、量落点、查控制台报错）：

   export NODE_PATH="C:/Users/Leo/.workbuddy/binaries/node/workspace/node_modules"
   cd D:/Code/2026AI/AIA_MDM/Essilor_MDM_PY && "D:/Code/nodejs/node.exe" _probe_manual_v4.cjs

期望：5 个目录链接点击后目标标题都停在视口 64px 处、active 高亮项与点击项一致、errs 为空。
