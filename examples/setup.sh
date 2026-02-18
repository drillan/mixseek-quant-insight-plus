#!/usr/bin/env bash
set -euo pipefail

# ワークスペースのセットアップスクリプト
# 使い方: ./setup.sh /path/to/workspace

WORKSPACE="${1:?Usage: ./setup.sh /path/to/workspace}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== quant-insight-plus ワークスペースセットアップ ==="
echo "Workspace: ${WORKSPACE}"

# Step 1: ワークスペース基本構造を作成
echo "[1/4] ワークスペース初期化..."
mixseek init "${WORKSPACE}" 2>/dev/null || true

# Step 2: configs をコピー
echo "[2/4] 設定ファイルをコピー..."
mkdir -p "${WORKSPACE}/configs/agents/members" "${WORKSPACE}/configs/agents/teams"
cp -r "${SCRIPT_DIR}/configs/"* "${WORKSPACE}/configs/"

# Step 3: DuckDB スキーマ初期化
echo "[3/4] DuckDB スキーマ初期化..."
MIXSEEK_WORKSPACE="${WORKSPACE}" quant-insight db init

# Step 4: データディレクトリを作成
echo "[4/4] データディレクトリを作成..."
mkdir -p "${WORKSPACE}/data/inputs/ohlcv"
mkdir -p "${WORKSPACE}/data/inputs/returns"
mkdir -p "${WORKSPACE}/data/inputs/master"

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "次のステップ:"
echo "  1. データファイルを配置してください:"
echo "     ${WORKSPACE}/data/inputs/ohlcv/  (ohlcv.parquet)"
echo "     ${WORKSPACE}/data/inputs/returns/ (returns.parquet)"
echo "     ${WORKSPACE}/data/inputs/master/  (master.parquet)"
echo ""
echo "  2. データを分割:"
echo "     MIXSEEK_WORKSPACE=${WORKSPACE} quant-insight data split --config ${WORKSPACE}/configs/competition.toml"
echo ""
echo "  3. 環境変数を設定:"
echo "     export MIXSEEK_WORKSPACE=${WORKSPACE}"
echo "     export ANTHROPIC_API_KEY=sk-ant-xxx"
echo ""
echo "  4. 実行:"
echo "     qip team \"データ分析タスク\" --config ${WORKSPACE}/configs/agents/teams/claudecode_team.toml"
