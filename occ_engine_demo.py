#!/usr/bin/env python3
"""
OCC Emotion Engine — 可运行示例（开源发布版）

OCC 认知情感模型 × 工程控制论 融合架构的 Python 实现。
纯标准库，无第三方依赖，直接运行即可体验。

用法：
    python3 occ_engine_demo.py              # 交互模式
    python3 occ_engine_demo.py --demo       # 自动演示脚本

设计来源：
    - Ortony-Clore-Collins 认知情感模型（OCC, 1988）
    - 钱学森工程控制论（反馈控制/系统层次/稳态调节）
"""

import math
import sys
import time


# ============================================================
# 1. 变量系统（单向依赖链：慢 → 快 → 即时）
# ============================================================

class EmotionState:
    """情感状态容器：Attachment（慢）→ Affection（快）→ Mood（即时）"""

    def __init__(self, attachment=50, affection=60):
        self.attachment = attachment      # 依恋度 0~100（慢变量，日级）
        self.affection = affection        # 好感度 -100~100（快变量，对话级）
        self.valence = -0.1 + (attachment / 100) * 0.3   # 效价 -1~1（初始=基线）
        self.arousal = 0.2                # 唤起度 0~1（即时）
        self.pending_events = []          # PendingEvent 时序队列
        self.last_u = 0.0                 # 上一回合反应强度（PID D 项用）

    # --- 基线 ---
    @property
    def valence_baseline(self):
        """效价自然基线：依恋越深，情绪底色越暖"""
        return -0.1 + (self.attachment / 100) * 0.3

    @property
    def arousal_baseline(self):
        return 0.2

    # --- 自适应阈值 ---
    @property
    def adaptive_threshold(self):
        """阈值随依恋度自适应：关系越深越容易触发正面情感"""
        return 0.3 * (1.5 - self.attachment / 100)

    # --- 衰减 ---
    def decay(self, dt_minutes=1.0):
        """情感指数衰减回基线（负面情感粘性更强）"""
        lam = 0.15 if self.valence >= 0 else 0.08   # 正 λ=0.15/min，负 λ=0.08/min
        mu = 0.20
        self.valence = self.valence_baseline + (self.valence - self.valence_baseline) * math.exp(-lam * dt_minutes)
        self.arousal = self.arousal_baseline + (self.arousal - self.arousal_baseline) * math.exp(-mu * dt_minutes)

    # --- VA 标签 ---
    def top_emotions(self, k=3):
        """按重叠评分 = 1/L2距离，取 top-k 情感标签（阈值 1.2 防中性误触发）"""
        scores = []
        for name, center in EMOTION_REGIONS.items():
            dist = math.sqrt((self.valence - center[0]) ** 2 + (self.arousal - center[1]) ** 2)
            score = 1.0 / dist if dist > 0 else 99.0
            if score >= 1.2:  # 距离 ≤ 0.83 才触发
                scores.append((name, score))
        scores.sort(key=lambda x: -x[1])
        return scores[:k]

    # --- PendingEvent ---
    def add_pending(self, description, etype, intensity, expected_valence):
        """加入时序事件（Hope/Fear），支持跨回合情感追踪"""
        if len(self.pending_events) >= 5:  # 容量 ≤5
            self.pending_events.sort(key=lambda e: e["intensity"])
            self.pending_events.pop(0)
        self.pending_events.append({
            "description": description,
            "type": etype,
            "intensity": intensity,
            "expected_valence": expected_valence,
            "created_at": time.time(),
            "timeout": 3600.0,
        })

    def resolve_pending(self, actual_valence):
        """解析时序事件：符号相同→Satisfaction/FearsConfirmed；相反→Relief/Disappointment"""
        results = []
        now = time.time()
        remaining = []
        for e in self.pending_events:
            if now - e["created_at"] > e["timeout"]:
                results.append(("超时", e))
                continue
            same_sign = (actual_valence >= 0) == (e["expected_valence"] >= 0)
            if e["type"] == "hope":
                results.append(("Satisfaction" if same_sign else "Disappointment", e))
            else:
                results.append(("FearsConfirmed" if same_sign else "Relief", e))
        self.pending_events = remaining
        return results


# ============================================================
# 2. VA 区域表（情感空间）
# ============================================================

EMOTION_REGIONS = {
    "平静":             (0.05, 0.15),
    "Joy":               (0.45, 0.30),
    "Distress":          (-0.45, 0.20),
    "Admiration":        (0.40, 0.20),
    "Reproach":          (-0.30, 0.35),
    "Gratitude":         (0.55, 0.45),
    "Anger":             (-0.65, 0.45),
    "Relief":            (0.45, -0.10),
    "Disappointment":    (-0.40, 0.00),
    "Remorse":           (-0.55, 0.30),
    "Pride":             (0.30, 0.15),
    "Shame":             (-0.35, 0.20),
    "Satisfaction":      (0.50, 0.05),
    "FearsConfirmed":    (-0.60, 0.40),
    "Hope":              (0.20, 0.40),
    "Fear":              (-0.20, 0.50),
    "Love":              (0.35, 0.20),
}

# 行为映射表（模板——角色可换自己的动作库）
BEHAVIOR_LOW = {
    "平静": "神色平静", "Joy": "嘴角微扬", "Distress": "垂眼", "Admiration": "专注注视",
    "Reproach": "嘴角下撇", "Hope": "歪头、眼睛亮一下", "Fear": "略显不安",
    "Pride": "挺胸", "Shame": "目光躲闪", "Love": "温柔注视",
    "Gratitude": "微笑靠近", "Anger": "鼓脸、抱臂", "Relief": "松一口气",
    "Disappointment": "耳朵耷拉", "Remorse": "低头",
}
BEHAVIOR_HIGH = {
    "平静": "平静如常", "Joy": "笑容绽放、眼睛弯成月牙", "Distress": "缩成一团、眼眶湿润",
    "Admiration": "星星眼、身体前倾", "Reproach": "鼓脸、扭头",
    "Hope": "身体前倾、眼睛发亮", "Fear": "贴紧、眼神闪躲",
    "Pride": "昂首挺胸", "Shame": "把脸埋进手里",
    "Love": "整个人挂上去", "Gratitude": "眼眶微红、用力点头",
    "Anger": "跺脚、转身", "Relief": "整个人软下来",
    "Disappointment": "默默缩到角落", "Remorse": "小声抽噎、伸手想碰又缩回",
}


# ============================================================
# 3. 三层评价器（OCC）
# ============================================================

def appraise_event(state, desirability):
    """事件评价：关乎目标——合意性（Desirability）"""
    thr = state.adaptive_threshold
    if desirability >= thr:
        return ("Joy", 0.45, 0.30)          # V+, A+
    elif desirability <= -thr:
        return ("Distress", -0.45, 0.20)    # V-, A+
    return None


def appraise_action(state, praiseworthiness, actor="other"):
    """行动评价：关乎标准——可称赞性（Praiseworthiness）"""
    thr = state.adaptive_threshold
    if actor == "core":  # 核心关系对象加权
        praiseworthiness *= 2.0
    if praiseworthiness >= thr:
        return ("Admiration", 0.40, 0.20)
    elif praiseworthiness <= -thr:
        return ("Reproach", -0.30, 0.35)
    return None


def appraise_object(state, appealingness, is_core=False):
    """对象评价：关乎品味——吸引力（Appealingness）"""
    if is_core:
        appealingness = max(appealingness, 0.4)  # 核心对象保护下限
    thr = state.adaptive_threshold
    if appealingness >= thr:
        return ("Love", 0.35, 0.20)
    elif appealingness <= -thr:
        return ("Dislike", -0.25, 0.15)
    return None


# ============================================================
# 4. PID 反馈控制器（非对称：有升必须有降）
# ============================================================

def pid_feedback(state, polarity, valence_effect):
    """PID 简化式 + 非对称反馈（负向放大 ×1.5）"""
    Kp, Ki, Kd = 3.0, 0.3, 5.0
    u = polarity
    # 积分项（演示简化：本回合不累积历史，实际场景可累计长期偏差）
    integral = 0.0
    d_term = u - state.last_u
    delta = Kp * u * 0.4 + Ki * integral + Kd * d_term * 0.02 + valence_effect
    # 非对称：负向放大 1.5 倍
    if delta < 0:
        delta *= 1.5
    delta = max(-2.0, min(2.0, delta))
    state.last_u = u
    state.affection = max(-100, min(100, state.affection + delta))
    # 依恋度双向漂移（慢变量）
    if state.affection > 55:
        state.attachment = min(100, state.attachment + 0.05)
    elif state.affection < 45:
        state.attachment = max(0, state.attachment - 0.05)


# ============================================================
# 5. 行为仲裁器
# ============================================================

def arbitrate(state):
    """多情感冲突解决：强度排序 + 行为合成"""
    top = state.top_emotions(3)
    if not top:
        return "平静", "无特殊情感输出", 0.0
    strongest_name, strongest_score = top[0]
    # 强度分档
    if strongest_score > 0.6:
        behavior = BEHAVIOR_HIGH.get(strongest_name, strongest_name)
        intensity = "high"
    else:
        behavior = BEHAVIOR_LOW.get(strongest_name, strongest_name)
        intensity = "low"
    # 亲密度
    intimacy = 0.3 + 0.5 * abs(state.valence) + 0.2 * (state.attachment / 100)
    # 复合标签
    labels = "+".join(n for n, s in top)
    return labels, behavior, intimacy


# ============================================================
# 6. 极性分析（简易中文情感词表 + 否定处理）
# ============================================================

POSITIVE_PHRASES = ["真好", "太好了", "好棒", "好喜欢", "真棒", "厉害", "爱你", "想你",
                    "谢谢", "辛苦了", "乖", "可爱", "聪明", "漂亮", "帅", "谢谢您", "好厉害",
                    "不错", "真不错"]
NEGATIVE_PHRASES = ["不好", "不对", "不行", "废物", "闭嘴", "滚蛋", "讨厌", "恨你",
                    "气死", "烦死", "别烦", "别吵", "不想理", "丢人", "白痴", "笨蛋",
                    "蠢货", "不喜欢", "不理你", "滚"]
NEGATION_WORDS = ["不", "没", "别", "不许", "不要", "懒得", "不想"]


def polarity_of(text):
    """返回 -1~1 的极性分（负面词表驱动 + 否定词处理）"""
    score = 0.0
    for p in POSITIVE_PHRASES:
        if p in text:
            # 检查前面是否有否定词（"不错"是正面词，不受"不"否定影响）
            idx = text.find(p)
            prefix = text[max(0, idx - 2):idx]
            # 否定词只作用于"好/棒/喜欢/想/理"等可被否定的词
            if any(n in prefix for n in NEGATION_WORDS) and p not in ("不错", "真不错"):
                score -= 1
            else:
                score += 1
    for n in NEGATIVE_PHRASES:
        if n in text:
            score -= 1
    return max(-1.0, min(1.0, score / 2.0))


# ============================================================
# 7. 主引擎
# ============================================================

class EmotionEngine:
    """OCC 情感引擎主类：一句话进来，情感状态 + 行为输出"""

    def __init__(self, character_name="AI", attachment=50, affection=60):
        self.state = EmotionState(attachment, affection)
        self.character = character_name

    def process(self, user_text):
        """处理用户输入，返回 (情感标签, 行为描述, 状态摘要)"""
        st = self.state

        # 1. 极性分析 → 事件评价输入
        polarity = polarity_of(user_text)

        # 2. 三层评价（演示：按输入关键词触发不同评价类型）
        if any(k in user_text for k in ["期待", "希望", "答应", "说好"]):
            st.add_pending(user_text[:20], "hope", 0.6, 0.3)
            va = (0.20, 0.40)  # Hope
        elif any(k in user_text for k in ["怕", "担心", "会不会"]):
            st.add_pending(user_text[:20], "fear", 0.5, -0.3)
            va = (-0.20, 0.50)  # Fear
        else:
            ev = appraise_event(st, polarity)
            if ev:
                va = (ev[1], ev[2])
            elif abs(polarity) < 0.2:
                # 中性输入：不触发情感（回到基线即可）
                va = (st.valence_baseline - st.valence, 0.0)
            else:
                va = (polarity * 0.3, 0.2)

        # 3. 汇入 VA 空间（负向增量放大 1.5 倍，与 PID 非对称一致——凶比夸影响大）
        if va[0] < 0:
            va = (va[0] * 1.5, va[1] * 1.2)
        st.valence = max(-1.0, min(1.0, st.valence + va[0]))
        st.arousal = max(0.0, min(1.0, st.arousal + va[1]))
        st.decay(0.5)  # 模拟 30 秒衰减

        # 4. 解析时序事件
        resolved = st.resolve_pending(st.valence)
        for kind, ev in resolved:
            if kind == "超时":
                pass
            elif ev["type"] == "hope":
                va2 = (0.3, -0.1) if kind == "Satisfaction" else (-0.4, 0.0)
                st.valence = max(-1.0, min(1.0, st.valence + va2[0]))
                st.arousal = max(0.0, min(1.0, st.arousal + va2[1]))

        # 5. PID 反馈（有升有降）
        pid_feedback(st, polarity, va[0] * 0.8)

        # 6. 行为仲裁
        labels, behavior, intimacy = arbitrate(st)

        summary = (f"[{self.character}] 好感={st.affection:+.1f} 依恋={st.attachment:.1f} "
                   f"V={st.valence:+.2f} A={st.arousal:.2f}")
        return labels, behavior, summary, intimacy


# ============================================================
# 8. 交互与演示
# ============================================================

DEMO_LINES = [
    ("你好呀", "打招呼"),
    ("你真棒，做得好！", "夸奖"),
    ("今天天气不错呢", "中性闲聊"),
    ("期待你明天带我去玩！", "建立希望"),
    ("我有点担心事情会搞砸", "表达担忧"),
    ("哼，你真讨厌，我不想理你了", "生气/凶"),
    ("对不起，我说错话了", "道歉"),
    ("明天带你去玩，说好了！", "希望兑现"),
]


def run_demo():
    print("=" * 60)
    print("OCC Emotion Engine — 自动演示")
    print("=" * 60)
    engine = EmotionEngine("AI-chan")
    for text, note in DEMO_LINES:
        labels, behavior, summary, intimacy = engine.process(text)
        print(f"\n【{note}】{text}")
        print(f"  → 情感: {labels}")
        print(f"  → 行为: {behavior}（亲密度 {intimacy:.2f}）")
        print(f"  → 状态: {summary}")
        time.sleep(0.3)
    print("\n" + "=" * 60)
    print("演示结束。观察要点：")
    print("1. 夸奖 → 好感上升；凶 → 好感下降（非对称反馈，降得更多）")
    print("2. 期待 → Hope；兑现 → Satisfaction；爽约 → Disappointment")
    print("3. 依恋度随长期互动漂移（慢变量）")
    print("=" * 60)


def run_interactive():
    print("OCC Emotion Engine — 交互模式（输入 q 退出）")
    print("试试：夸奖、凶、期待、担心、道歉……")
    engine = EmotionEngine("AI-chan")
    while True:
        try:
            text = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("q", "quit", "exit"):
            break
        labels, behavior, summary, intimacy = engine.process(text)
        print(f"AI-chan > 情感: {labels} | 行为: {behavior} | 亲密度: {intimacy:.2f}")
        print(f"          {summary}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    else:
        run_interactive()
