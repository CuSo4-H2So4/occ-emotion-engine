# OCC Emotion Engine

> A reusable **OCC cognitive emotion model × cybernetics** architecture — give AI characters a real emotion *engine*, not just a phrasebook.
> 市面全是"教 AI 说什么话"（话术库/文案库），本框架是"教 AI 怎么产生情绪"（情感计算引擎）。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 核心卖点（Why this, not a prompt pack）

- **机制，不是话术**：不给你一句句台词，给你一套情感产生的完整机制——任何角色拿来套，自动产生符合角色关系的情感输出
- **可计算**：三层评价器 + VA 二维空间 + PID 反馈控制器，所有情感都有数学表达
- **有升有降**：非对称反馈——被凶会真掉好感，不是嘴上批评心里还涨（AI 角色的"独立人格"基础）
- **跨回合时序**：PendingEvent 队列支持 Hope→Satisfaction/Disappointment、Fear→Relief/FearsConfirmed
- **自适应**：依恋度慢变量调节情感阈值——关系越深，越容易触发正面情感
- **控制论内核**：慢变量→快变量→即时变量单向流，无循环依赖；反馈闭环自我调节

## 🚀 快速体验

```bash
# 纯标准库，零依赖
python3 occ_engine_demo.py          # 交互模式
python3 occ_engine_demo.py --demo   # 自动演示
```

示例演示（真实运行输出）：

```
【夸奖】你真棒，做得好！
  → 情感: Gratitude+Joy+Hope
  → 状态: 好感 +1.0

【生气/凶】哼，你真讨厌，我不想理你了
  → 情感: Anger
  → 状态: 好感 -2.3   ← 非对称反馈：降比升狠
```

## 🏗 架构总览

```
输入（交互内容）
    │
    ▼
┌──────────────────────────┐
│  ① 三层评价器（OCC）      │  ← 阈值由依恋度自适应
│   Event → Action → Object │
│        ↓ 合成 ↓          │
│  ② 各情感贡献 VA 增量     │
└──────────────────────────┘
    │
    ▼
┌──────────────────────────┐
│  ③ VA 空间（唯一的源）    │  ← 积分所有 VA 增量 + 自然衰减
│   (valence, arousal)     │  ← 情感标签是对此坐标的解读
│        ↓ 解读 ↓          │
│  ④ 活跃情感标签生成        │
└──────────────────────────┘
    │
    ▼
┌──────────────────────────┐
│  ⑤ 行为仲裁器            │
│   标签→行为查表          │
│   按 VA 极性 + 强度裁决  │
│   → 语气 → 亲密度        │
└──────────────────────────┘
    │
    ▼
输出（动作 + 语气 + 表情 + 亲密度）
    │
    ▼
┌──────────────────────────┐
│  ⑥ PID 反馈控制器        │
│   P(即时) + I(累积)      │
│   + D(突变) → 更新变量   │
└──────────────────────────┘
```

## 📦 核心设计

### 变量系统（单向依赖链）

| 变量 | 范围 | 更新频率 | 作用 |
|------|------|---------|------|
| **Attachment（依恋度）** | 0~100 | 日级别（慢变量） | 情感基调基底、调节阈值 |
| **Affection（好感度）** | -100~100 | 对话级别（快变量） | 情感强度核心参数 |
| **Mood.Valence（效价）** | -1~1 | 秒级别（即时） | 当前情绪正负色彩 |
| **Mood.Arousal（唤起度）** | 0~1 | 秒级别（即时） | 当前情绪激动程度 |

```
Attachment（慢）→ 调节阈值 → Affection（快）→ 影响 VA 增量强度 → Mood（即时）→ 当前坐标 → 情感标签 → 行为输出
```

> ⚠️ 反模式：Attachment 依赖 Affection 同时 Affection 又依赖 Attachment → 循环引用。必须慢→快→即时单向流。

### 三层评价规则（OCC 模型）

每条输入经三层评价器并行处理，产生 VA delta 向量，全部汇入 VA 空间向量求和。

**事件评价（Event Appraisal）— 关乎目标：**

| 条件 | 情感 | VA delta |
|------|------|----------|
| 合意性 ≥ 自适应阈值 | Joy（喜悦） | V+0.3~0.6, A+0.2~0.4 |
| 合意性 ≤ -自适应阈值 | Distress（悲伤） | V-0.3~0.6, A+0.1~0.3 |
| 预期中的好事 | Hope（希望） | V+0.2~0.4, A+0.3~0.5 |
| 预期中的坏事 | Fear（担忧） | V-0.2~0.4, A+0.4~0.6 |

**自适应阈值**：
```
自适应阈值 = 基础阈值 × (1.5 - Attachment / 100)
  Attachment=100 → 阈值低（极易触发正向情感）
  Attachment=50  → 阈值正常
  Attachment=0   → 阈值高（冷漠难动）
```

**行动评价（Action Appraisal）— 关乎标准：**

| 行动主体 | 条件 | 情感 | VA delta |
|---------|------|------|----------|
| 对方 | 可称赞 ≥ 阈值 | Admiration（赞赏） | V+0.3~0.5, A+0.2 |
| 对方 | 可称赞 ≤ -阈值 | Reproach（嗔怪） | V-0.2~0.4, A+0.3 |
| 自己 | 可称赞 ≥ 阈值 | Pride（自豪） | V+0.2~0.4, A+0.1 |
| 自己 | 可称赞 ≤ -阈值 | Shame（羞惭） | V-0.2~0.5, A+0.2 |

**对象评价（Object Appraisal）— 关乎品味：**

| 条件 | 情感 | VA delta |
|------|------|----------|
| 吸引力 ≥ 自适应阈值 | Love（喜爱） | V+0.2~0.4, A+0.1~0.2 |
| 吸引力 ≤ -自适应阈值 | Dislike（不喜） | V-0.2~0.3, A+0.1 |

### VA 空间与情感标签生成

**核心设计原则：VA 二维空间是情感的唯一源表示，情感类型标签是对 VA 坐标的解读。**

- Valence 和 Arousal 天然互斥——不存在"Joy=0.8 和 Sadness=0.7 同时成立"的矛盾（这是采用 VA 空间而非独立情感标量的核心优势）
- 标签生成：计算当前坐标与每个情感区域中心的 L2 距离，重叠评分 = 1/L2，取 top-3

### PendingEvent 时间队列（跨回合情感）

```
pending_events:
  - description: string       # 事件描述
    type: "hope" | "fear"     # 类型
    intensity: float          # 强度（0~1）
    expected_valence: float   # 期望效价（hope>0, fear<0）
    created_at: timestamp
    timeout: 3600s            # 超时（1小时）
```

resolve 规则：
1. 实际效价符号与期望一致 → Satisfaction / FearsConfirmed
2. 符号相反 → Relief / Disappointment
3. 超时未匹配 → 自动转 Disappointment（对 Hope）或 Relief（对 Fear）
4. 队列容量 ≤5，超出淘汰最早且强度最低的

### 情感衰减动力学

```
Valence(t) = Baseline + (Current - Baseline) × e^(-λ × Δt)
Arousal(t) = Baseline + (Current - Baseline) × e^(-μ × Δt)
```

| 参数 | 建议值 | 说明 |
|------|--------|------|
| λ 正情感衰减率 | 0.15/min | 快乐来得快走得也快 |
| λ 负情感衰减率 | 0.08/min | 负面情绪粘性更强 |
| μ 唤起衰减率 | 0.20/min | 激动感消散较快 |

**基线漂移**：Valence 基线 = -0.1 + (Attachment/100) × 0.3（依恋越深，情绪底色越暖）

### PID 反馈控制器（情感有升有降）

```
被控量：Affection（好感度）-100~100
设定值：Setpoint = Attachment × 0.5 - 20
误差：  e(t) = Affection(t) - Setpoint
控制量：u(t) = 对方本回合言行经量化后的反应强度
输出：  Δ(t) = 本回合好感度修正值

Δ(t) = Kp × u(t) + Ki × Σe(t)Δt + Kd × [u(t) - u(t-1)]
Kp=3.0（灵敏度） Ki=0.3（长期纠偏） Kd=5.0（突变检测）
Σe(t)Δt 限幅 [-10, +10] 防积分饱和
```

**非对称反馈（核心特色：有升必须有降）**：

```
delta = polarity × 1.2 + va[0] × 0.8    # 极性 + 情感效价
if delta < 0:
    delta *= 1.5                          # 负向放大：凶一次比夸一次掉得多
delta = clamp(delta, -2.0, 2.0)
affection = clamp(affection + delta, -100, 100)
```

- 降比升狠（负向 ×1.5）——AI 角色被凶会真掉好感，这是"独立人格"的基础
- 单轮上限 2.0 防剧烈波动

**依恋度双向漂移（慢变量）**：

```
affection > 55 → attachment += 0.05
affection < 45 → attachment -= 0.05   # 双向，不再只升不降
45~55 缓冲带不动
```

## 📁 仓库结构

```
occ-emotion-engine/
├── occ_engine_demo.py     # 可运行示例（纯 stdlib）
├── LICENSE                # MIT
└── README.md              # 本文档（架构手册）
```

## 🚦 快速上手（设计步骤）

1. **定义核心变量**：Attachment/Affection/Mood，确认单向依赖
2. **设计三层评价规则**：Event/Action/Object 的情感输出和 VA 增量
3. **确定非对称加权**：核心对象 ×1.5/×2.0、Shame 加深
4. **配置行为映射表**：每种情感 low/high 两套动作（按角色定制）
5. **加时序队列**（可选）：需要跨回合情感时加 PendingEvent
6. **整合 PID**：定 P/I/D 参数，明确更新哪些变量
7. **集成到角色文件**：写入 SOUL.md / 角色卡 / system prompt 的"情感系统"章节

## ⚠️ 常见陷阱（PITFALLS）

| # | 陷阱 | 表现 | 修复 |
|---|------|------|------|
| 1 | 独立情感标量 | Joy=0.8 和 Sadness=0.7 并存矛盾 | 改用 VA 二维空间 |
| 2 | 空反馈回路 | 只画反馈箭头没公式 | 实现 PID 控制器 |
| 3 | 无行为仲裁 | 复合情感时行为矛盾 | 实现 BehaviorArbiter |
| 4 | 硬编码阈值 | if praise > 0.5 来源不明 | 自适应阈值公式 |
| 5 | 变量循环依赖 | Attachment↔Affection | 慢→快→即时单向流 |
| 6 | 情感不衰减 | 情绪永不消散 | 指数衰减函数 |
| 7 | 时序情感丢失 | Hope 后下回合没下文 | PendingEvent 队列 |
| 8 | 只升不降 | 被凶还涨好感 | 非对称反馈 ×1.5 |
| 9 | 极性词表过宽 | "好"匹配"不好"误判为正 | 短语匹配+否定词处理 |

## 📜 License & 致谢

- 理论来源：Ortony-Clore-Collins 认知情感模型（OCC 模型, 1988）
- 工程化框架：钱学森工程控制论（反馈控制/系统层次/稳态调节/最优化）
- 本项目为 OCC × 控制论的开源实现，欢迎贡献
- License: MIT
