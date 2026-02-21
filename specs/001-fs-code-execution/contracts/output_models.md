# Contract: output_models module

**Module**: `src/quant_insight_plus/agents/output_models.py`

## Models

### FileSubmitterOutput

```python
class FileSubmitterOutput(BaseModel):
    """submission-creator の構造化出力。

    コード本体はファイルに存在する。
    構造化出力はファイルパスのみを含み、コードの二重管理を排除する。
    """
    submission_path: str
    description: str
```

**Invariants**:
- `submission_path` は絶対パスであること
- `description` は Markdown 形式のテキスト

---

### FileAnalyzerOutput

```python
class FileAnalyzerOutput(BaseModel):
    """train-analyzer の構造化出力。

    分析レポートはファイルとモデルの両方に存在する
    （report はリーダーへの主要な報告内容として使用）。
    """
    analysis_path: str
    report: str
```

**Invariants**:
- `analysis_path` は絶対パスであること
- `report` は Markdown 形式のテキスト
