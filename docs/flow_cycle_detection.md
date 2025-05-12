# フロー循環検出の設計案

## 要件
- connect時に循環が発生する場合は例外で拒否する（原則禁止）
- 手動編集やバグ時のため、全体検査用の循環検出メソッドも用意
- 既存の履歴取得系メソッドは循環許容のまま維持

---

## 循環検出アルゴリズム詳細

### connect時の循環検出
新たなエッジ (from_id, to_id) を追加する際、「to_id から from_id へ到達可能か」を深さ優先探索（DFS）で調べる。到達可能なら循環が発生するため、例外を投げて拒否する。

### 全体検査用の循環検出
connections全体を使い、各ノードからDFSで探索。探索中に「訪問中」のノードに再度到達した場合は循環と判定する。

### 疑似コード例

```python
def would_create_cycle(connections, from_id, to_id):
    # 仮想的に (from_id, to_id) を追加
    graph = defaultdict(list)
    for f, t in connections:
        graph[f].append(t)
    graph[from_id].append(to_id)

    # to_id から from_id へ到達可能かDFS
    stack = [to_id]
    visited = set()
    while stack:
        node = stack.pop()
        if node == from_id:
            return True
        if node not in visited:
            visited.add(node)
            stack.extend(graph[node])
    return False
```

---

## 実装計画
1. Flowクラスに循環検出メソッド（DFSベース）を追加
2. connectメソッドで循環検出を行い、循環時は例外を投げる
3. 既存の履歴取得・循環許容の仕組みは維持
4. テスト・検証