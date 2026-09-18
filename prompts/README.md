# Prompts (提示词资产库)

本目录用于沉淀与管理个人沉淀的高价值 Prompt、系统角色定义（System Prompts）以及复杂任务的结构化指令模板。

---

## 目录组织

- `examples/`：精选的高质量通用 Prompt 范例，涵盖代码审查、架构设计、文本提炼、数据清洗等。
- 自定义 Prompts：可以直接在本目录下或新建分类子目录进行扩展。

---

## Prompt 编写与沉淀规范

为了确保 Prompt 在不同大模型（Claude、GPT-4o、Gemini 等）下均具备高稳定度与可复现性，推荐采用以下结构编写：

1. **Role（角色）**：清晰界定 AI 的专业身份与背景。
2. **Context（背景）**：交代输入数据来源或任务背景。
3. **Task & Constraints（任务与约束）**：明确必须做什么、严禁做什么。
4. **Format & Schema（输出格式规范）**：优先指定 Markdown 或 JSON Schema。
5. **Few-Shot Examples（少样本范例）**：提供 1~2 个规范输入/输出范例提升确定性。
