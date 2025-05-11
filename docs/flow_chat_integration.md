# VizPromptチャットREPLへのフロー統合設計

## 概要
- チャットREPL開始時に新規フローを作成し、各ターンのノードを直列につなぐ。
- 分岐はサポートせず、一直線のログとしてconnectionsを構築する。
- `handle_chat`はノードIDを返す形に変更。

## 実装方針

### 1. REPL開始時
- `FlowManager`を生成し、`create_flow`で新規フローを作成。
- `prev_node_id = None`で初期化。

### 2. 各ターン
- `handle_chat`でノードを保存し、ノードIDを返す。
- 前回ノードID (`prev_node_id`) があれば `flow.connect(prev_node_id, curr_node_id)` で直列につなぐ。
- `flow.save()`でフローを保存。
- `prev_node_id`を更新。

### 3. handle_chat
- ノード保存後、そのノードIDを返すように変更。

## シーケンス図

```mermaid
flowchart TD
    Start([REPL開始])
    FlowMgr[FlowManager生成]
    FlowNew[新規フロー作成]
    prevID[prev_node_id=None]
    LoopStart{{入力ループ}}
    Chat[handle_chat→curr_node_id取得]
    Connect{prev_node_idあり?}
    FlowConnect[flow.connect(prev_node_id, curr_node_id)]
    FlowSave[flow.save()]
    UpdatePrev[prev_node_id=curr_node_id]
    End([終了])

    Start --> FlowMgr --> FlowNew --> prevID --> LoopStart
    LoopStart --> Chat --> Connect
    Connect -- Yes --> FlowConnect --> FlowSave --> UpdatePrev --> LoopStart
    Connect -- No --> UpdatePrev --> LoopStart
    LoopStart -- 終了条件 --> End
```

## 備考
- フロー名や説明は任意で設定可能。
- 今後分岐や履歴表示などの拡張も容易。
