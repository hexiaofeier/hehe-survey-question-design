# 2026.11.02：问卷阅读版与交付规则更新

这次更新保留原有八步问卷设计、变量库、专项题组和三稿交付，将Word阅读格式与复杂逻辑处理同步到公开版。

- Word采用A4竖版：题干10.5磅加粗、选项9.5磅原生表格、说明8.5磅灰字；矩阵保留完整行列，检查题干和选项的分页关系。
- Markdown建卷稿继续使用题干加简短标签、逐行选项；导入稿继续只含平台文本题目。
- 动态引用保留原代码，明确多分支命中、无可用选项及跳转目标显示条件。材料、样本来源、计样单位和产品比较顺序更清楚地落到底稿。
- 文件交付完成后即可结束；平台导入、在线设置、发布、回收或目标受访者预试由用户另行要求。

## 新示例

[新能源汽车公共充电问卷](../examples/public-charging/questionnaire-design.md)有29题、六个部分，Word共8页；26张普通选项表格和1张六行矩阵均可编辑。按近期成功使用与未使用分流，并分别询问费用、最近一次满意度、近30天问题和优先改进事项。配额和样本量未预设。

[Word阅读详稿](../examples/public-charging/questionnaire-design.docx) · [MD导入稿](../examples/public-charging/questionnaire-import.md) · [PDF预览](../examples/public-charging/reading-preview.pdf)

本例做过三稿同文、静态逻辑和实际Word分页检查，未进行平台上线或真人预试。旧版适老化示例继续保留。

## 更新安装

替换整个 `skills/hehe-survey-question-design/` 文件夹，包含全部references，再新开会话。Word由Agent当前可用的文档工具生成，本仓库不绑定某个付费插件或另一项必装Skill。
