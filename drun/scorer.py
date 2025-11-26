"""
Case scoring system for Drun test cases.

Evaluates test case quality based on:
- Step level: validators, extract, retry
- Case level: parameters, hooks, invoke
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from drun.models.case import Case
from drun.models.step import Step


@dataclass
class StepScore:
    """Score for a single step."""
    name: str
    validators: int = 0      # 断言得分
    extract: int = 0         # 提取得分
    retry: int = 0           # 重试得分
    total: int = 0           # 步骤总分
    validator_count: int = 0 # 断言数量
    extract_count: int = 0   # 提取数量
    suggestions: List[str] = field(default_factory=list)


@dataclass
class CaseScore:
    """Score for a test case."""
    name: str
    steps: List[StepScore] = field(default_factory=list)
    parameters: int = 0      # 参数化得分
    hooks: int = 0           # Hooks得分
    invoke: int = 0          # 复用得分
    step_avg: int = 0        # 步骤平均分
    total: int = 0           # 用例总分
    grade: str = "D"         # A/B/C/D
    suggestions: List[str] = field(default_factory=list)


class CaseScorer:
    """Evaluates test case quality."""
    
    def score_step(self, step: Step, step_idx: int) -> StepScore:
        """Score a single step."""
        score = StepScore(name=step.name)
        
        # 1. 断言得分 (50%)
        validator_count = len(step.validators) if step.validators else 0
        score.validator_count = validator_count
        if validator_count == 0:
            score.validators = 0
            score.suggestions.append(f"步骤{step_idx}: 缺少断言，建议添加状态码和响应体验证")
        elif validator_count == 1:
            score.validators = 60
        elif validator_count == 2:
            score.validators = 80
        else:
            score.validators = 100
        
        # 2. 变量提取得分 (30%)
        extract_count = len(step.extract) if step.extract else 0
        score.extract_count = extract_count
        if extract_count == 0:
            score.extract = 0
            # Only suggest for request steps, not invoke
            if step.request is not None:
                score.suggestions.append(f"步骤{step_idx}: 未提取变量，建议提取关键字段供后续使用")
        else:
            score.extract = 100
        
        # 3. 重试机制得分 (20%)
        if step.retry and step.retry > 0:
            score.retry = 100
        else:
            score.retry = 60  # 基础分
        
        # 计算步骤总分
        score.total = int(
            score.validators * 0.50 +
            score.extract * 0.30 +
            score.retry * 0.20
        )
        
        return score
    
    def score_case(self, case: Case) -> CaseScore:
        """Score a test case."""
        case_name = case.config.name or "Unnamed"
        score = CaseScore(name=case_name)
        
        # Score each step
        has_invoke = False
        for idx, step in enumerate(case.steps, 1):
            step_score = self.score_step(step, idx)
            score.steps.append(step_score)
            if step.invoke is not None:
                has_invoke = True
        
        # Calculate step average (70% of total)
        if score.steps:
            score.step_avg = int(sum(s.total for s in score.steps) / len(score.steps))
        else:
            score.step_avg = 0
        
        # Case-level scoring (30% of total)
        
        # 1. 参数化得分 (50% of case-level)
        if case.parameters:
            score.parameters = 100
        else:
            score.parameters = 0
            score.suggestions.append("用例: 未使用参数化，建议添加多组测试数据")
        
        # 2. Hooks得分 (30% of case-level)
        has_hooks = (
            (case.setup_hooks and len(case.setup_hooks) > 0) or
            (case.teardown_hooks and len(case.teardown_hooks) > 0) or
            any(
                (s.setup_hooks and len(s.setup_hooks) > 0) or
                (s.teardown_hooks and len(s.teardown_hooks) > 0)
                for s in case.steps
            )
        )
        if has_hooks:
            score.hooks = 100
        else:
            score.hooks = 60  # 基础分
        
        # 3. 用例复用得分 (20% of case-level)
        if has_invoke:
            score.invoke = 100
        else:
            score.invoke = 60  # 基础分
        
        # Calculate case-level score
        case_level = int(
            score.parameters * 0.50 +
            score.hooks * 0.30 +
            score.invoke * 0.20
        )
        
        # Total score = step_avg(70%) + case_level(30%)
        score.total = int(score.step_avg * 0.70 + case_level * 0.30)
        
        # Determine grade
        if score.total >= 90:
            score.grade = "A"
        elif score.total >= 70:
            score.grade = "B"
        elif score.total >= 50:
            score.grade = "C"
        else:
            score.grade = "D"
        
        # Collect step suggestions
        for step_score in score.steps:
            score.suggestions.extend(step_score.suggestions)
        
        return score
    
    def get_grade_color(self, grade: str) -> str:
        """Get color for grade."""
        colors = {
            "A": "#1a7f37",
            "B": "#0969da",
            "C": "#9a6700",
            "D": "#cf222e",
        }
        return colors.get(grade, "#6e7781")
    
    def get_grade_bg(self, grade: str) -> str:
        """Get background color for grade."""
        colors = {
            "A": "#dafbe1",
            "B": "#ddf4ff",
            "C": "#fff8c5",
            "D": "#ffebe9",
        }
        return colors.get(grade, "#f6f8fa")
