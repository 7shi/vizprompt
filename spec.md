# VizPrompt 設計仕様書

## 1. 概要

VizPromptは、チャット履歴をフローとして管理するノードベースのインターフェースです。再試行やプロンプト修正により生じる分岐を視覚化し、履歴を動的につなぎなおすことができる点が特徴です。

### 1.1 目的
- チャット履歴の分岐を視覚的に管理する
- トークン消費を最適化しながら関連コンテキストを効率的に参照する
- 履歴の動的な再構成を可能にする

### 1.2 主要コンセプト
- プロンプトと回答をペアとして一つのノードで管理
- 会話はデフォルトで直線的に継続し、再試行や編集で分岐
- 必要に応じてノード間のつなぎ直しが可能
- 要約とタグによる効率的なコンテンツ参照

## 2. アーキテクチャ選択

フレームワークと実装アプローチについては、VizPromptの特殊なユースケースに合わせた独自実装を採用します。

### 2.1 LLM連携
- OpenAI互換、Gemini、Ollamaの初期サポート
- 各LLMプロバイダー用の専用コネクタを実装
- 共通インターフェースによるプロバイダー切り替え

### 2.2 実装アプローチ
- 各LLM APIの特性を最大限に活用
- 将来の拡張を容易にするモジュール設計
- ライブラリとしての提供と、多様なインターフェースのサポート

## 3. システム構成

### 3.1 ファイルシステム構造
```
project/
├── nodes/                           # ノードディレクトリ
│   ├── index.tsv                    # ノードファイルパス・UUID・タイムスタンプのマッピング (TSV形式)
│   ├── 000/                         # 最初のノード格納ディレクトリ (最大1000ファイルだが、100ずつ使用)
│   │   ├── 000.xml                  # 連番でファイル名を管理
│   │   ├── 001.xml
│   │   └── ...
│   ├── 001/                         # 101個目以降のノード格納ディレクトリ
│   │   └── ...
│   └── ...                          # 必要に応じて増加
├── flows/                           # フローディレクトリ
│   ├── index.tsv                    # フローIDとファイルパスのマッピング (TSV形式)
│   ├── 000/                         # 最初のフロー格納ディレクトリ (最大1000ファイルだが、100ずつ使用)
│   │   ├── 000.yaml                 # 連番でファイル名を管理 (YAML形式)
│   │   ├── 001.yaml
│   │   └── ...
│   ├── 001/                         # 101個目以降のフロー格納ディレクトリ
│   │   └── ...
├── metadata/                        # メタデータファイル
│   ├── tags.yaml                    # タグ一覧 (YAML形式)
│   └── index.yaml                   # ノード検索用インデックス (YAML形式)
└── config.yaml                      # 設定ファイル (YAML形式)
```

### 3.2 データ形式
- ノードデータ: XML形式（CDATAセクションで改行保持）
- メタデータ: YAML形式
- マッピング: TSV形式
- 設定: YAML形式

### 3.3 データ永続化方針

VizPromptでは、データ永続化に際して、一般的なORM（Object-Relational Mapper）やデータベースシステムではなく、テキストベースのファイル形式（XML, YAML, TSV）を採用しています。この選択には以下の理由があります。

- **可読性と編集の容易性**: テキストファイルは人間が直接読み書きしやすく、特別なツールなしに内容を確認・編集できます。これにより、デバッグや手動でのデータ修正が容易になります。
- **バージョン管理との親和性**: テキストベースのデータはGitのようなバージョン管理システムと非常に相性が良いです。変更履歴の追跡、差分確認、ブランチ運用などが容易に行え、データの変更管理を堅牢にします。
- **ポータビリティと透明性**: 特定のデータベースエンジンやORMライブラリへの依存を避けることで、システムのポータビリティを高めます。データはプレーンなファイルとして存在するため、異なる環境への移行や、他のツールとの連携が容易になります。
- **シンプルさ**: プロジェクトの初期段階や小〜中規模のデータ量においては、データベースシステムの導入・管理コストよりも、テキストファイルによるシンプルな管理の方が効率的な場合があります。
- **GitHub連携**: 「10. GitHub連携の考慮」で詳述するように、テキストベースのファイルはGitHubなどのプラットフォームでの共有や共同編集に適しています。

これらの理由から、VizPromptはデータの透明性、管理の容易さ、そして開発の柔軟性を重視し、テキストベースの永続化戦略を選択しました。

## 4. ノード構造

ノードの`<contents>`内の`<text>`要素は、プロンプトや応答の生ログに近い形で保存することを目的としています。XMLのCDATAセクションを利用することで、改行を含む複数行のテキストをそのままの形で保持でき、可読性が向上します。JSONやYAMLでは文字列としてエスケープ処理が必要となり、元のフォーマットが失われやすいため、XML形式を採用しました。

- タイムスタンプはISO 8601形式で表現します。
- ノードはUUIDを使用して識別されますが、同じUUIDでバージョン違いのノードが存在することを許容します。UUIDがuniqueでなくなるため積極的には使いませんが、何らかの不整合でそのようなケースが発生しても、問題を最小限に抑えることを意図しています。

### 4.1 ノードXMLファイル形式

```xml
<?xml version="1.0" encoding="utf-8"?>
<node id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" timestamp="2025-05-09T06:48:06.533720+09:00">
<contents>
<text role="user" count="6" duration="1.20" rate="4.99"><![CDATA[
プロンプト内容をここに記載...
（改行やフォーマットを保持）
]]></text>
<text role="assistant" count="14" duration="0.08" rate="179.49"><![CDATA[
応答内容をここに記載...
（改行やフォーマットを保持）
]]></text>
</contents>
<metadata>
<model>gemini-2.0-flash-001</model>
<summary updated="false" last_built="2025-05-09T06:48:06.533720+09:00"><![CDATA[
ノードの要約内容
]]></summary>
<tags>
<tag>タグ1</tag>
<tag>タグ2</tag>
<tag>タグ3</tag>
</tags>
</metadata>
</node>
```

### 4.2 ノード属性説明

- **id**: ノード識別子（タイムスタンプベース）
- **timestamp**: ノード作成日時
- **contents**: ノードの内容
  - **text**: プロンプトと応答の内容（CDATA内）
    - **role**: 発話者の役割（user: ユーザー, assistant: モデル）
    - **count**: トークン数
    - **duration**: 処理時間（秒）
    - **rate**: トークン/秒のレート
- **metadata**: ノードに関するメタ情報
  - **model**: 使用したLLMモデル名（例: gemini-2.0-flash-001）
  - **summary**: ノードの要約（プロンプトと応答を含む）
  - **updated**: 要約更新フラグ（編集後未ビルド時はtrue）
  - **last_built**: 最後に要約を生成した時刻
  - **tags**: ノードに関連するタグ（複数可）
    - **tag**: タグ名

※ ノード間の接続情報（connections）はノードXMLには含めず、フロー定義ファイルで一元管理する

### 4.3 ノードマッピング (nodes/index.tsv)

```
relpath	uuid	timestamp
00/00.xml	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	2025-05-09T06:48:06.533720+09:00
00/01.xml	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	2025-05-09T06:49:10.123456+09:00
00/02.xml	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	2025-05-09T06:50:22.654321+09:00
...
01/00.xml	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	2025-05-09T07:01:00.000000+09:00
...
```

### 4.4 UUID衝突への対処法

ノードの編集や手動コピーなどの操作により、UUID衝突が発生する可能性があります。以下の手順でこれを検出し対処します：

1. **UUID衝突の検出**
   - システム起動時またはインデックス再構築時に全ノードをスキャン
   - 同一UUID複数発見時に衝突と判断

2. **衝突解決アルゴリズム**
   - タイムスタンプが新しいノードを優先
   - タイムスタンプが同一の場合、ディレクトリ走査で後から発見されたノードを優先
   - マップ構造ではUUIDをキーとしたリストを保持することで複数候補の管理を可能に

3. **競合処理手順**
   - 最新または優先ノードをリストの先頭に置くことで、正規ノードを表現
   - 他の競合ノードは優先度順にリストに配置

これによりUUID衝突が発生した場合でも、システムの一貫性を保ちながら適切に対応します。

## 5. フロー構造

単一の巨大なフローファイルで全ての情報を管理するのではなく、フローを複数のファイルに分割して管理することが可能です。これにより、以下のようなメリットがあります。

- **可読性の向上**: 関連性の高いノード群を個別のフローファイルにまとめることで、各ファイルの内容が理解しやすくなります。
- **管理の容易性**: 特定の機能や実験に対応するフローを個別に管理・編集できます。
- **パフォーマンス**: 大規模なフローの場合、必要な部分だけをロードすることで、アプリケーションの起動時間や動作の応答性を改善できる可能性があります。

各フローファイルは「5.1 フロー定義」で示されるYAML形式に従います。システムは `flows/index.tsv` (「5.2 フローマッピング」参照) を用いて、各フローIDと対応するファイルパスを解決します。これにより、複数のフローファイルが存在する場合でも、システム全体として一貫したフロー情報を扱うことができます。

例えば、メインの会話フローとは別に、特定のトピックに関する詳細な調査や実験のためのサブフローを作成し、それぞれ別のYAMLファイルとして保存することができます。これらのフローは、必要に応じてメインフローから参照されたり、独立して利用されたりします。

**注意**：フロー内の循環（サイクル）は原則禁止です。connect時に循環が発生する場合は例外で拒否されます。手動編集や不整合時を想定した検出機構は備えますが、通常運用では循環を許容しません。

### 5.1 フロー定義

フロー定義ファイルは、主に構造化された短いテキスト情報を扱います。YAML形式は人間にとって可読性が高く、階層構造も表現しやすいため、このような設定情報や関連情報の記述に適しています。TOMLと比較しても、本ケースではYAMLの簡潔さがより適していると判断しました。

```yaml
id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
name: メインフロー
created: 2025-05-07T10:00:00+09:00
updated: 2025-05-08T13:55:22+09:00
description: フローの説明
# このフローに含まれる全てのノードのIDのリスト（順序ではない）
nodes:
  - index: 1
    id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  - index: 2
    id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  - index: 3
    id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  - index: 4
    id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# ノード間の接続情報（分岐や合流の情報を定義）
connections:
  # 分岐の例: Node 1からNode 2とNode 3に接続
  - from: 1
    to: 2
  - from: 1
    to: 3
  # 合流の例: Node 2とNode 3からNode 4に接続
  - from: 2
    to: 4
  - from: 3
    to: 4
```

### 5.2 フローマッピング (flows/index.tsv)

```
relpath	uuid	timestamp
00/00.yaml	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	2025-05-09T06:48:06.533720+09:00
00/01.yaml	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	2025-05-09T06:49:10.123456+09:00
00/02.yaml	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	2025-05-09T06:50:22.654321+09:00
...
01/00.yaml	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	2025-05-09T07:01:00.000000+09:00
...
```

## 6. メタデータ管理

### 6.1 タグ定義 (metadata/tags.yaml)

```yaml
updated: 2025-05-08T13:55:22+09:00
tags:
  タグ名1:
    - xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    - xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  タグ名2:
    - xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    - xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 6.2 インデックス (metadata/index.yaml)

```yaml
updated: 2025-05-08T13:55:22+09:00
nodes:
  xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:
    timestamp: 2025-05-08T12:30:45+09:00
    keywords: キーワード1,キーワード2,キーワード3
    summary: インデックス用要約
  xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:
    timestamp: 2025-05-08T12:45:12+09:00
    keywords: キーワード2,キーワード4
    summary: 別のノードの要約
```

### 6.3 設定ファイル (config.yaml)

```yaml
version: "1.0"
created: 2025-05-07T10:00:00+09:00
updated: 2025-05-08T13:55:22+09:00
settings:
  max_files_per_folder: 100
  default_llm_provider: openai
  default_model: gpt-4
  summary_token_limit: 50
providers:
  openai:
    api_key_env: OPENAI_API_KEY
  gemini:
    api_key_env: GEMINI_API_KEY
  ollama:
    host: http://localhost:11434
```

## 7. コアモジュール設計

```
vizprompt/
├── core/
│   ├── base.py          # 基本インターフェース
│   ├── node.py          # ノード管理
│   ├── flow.py          # フロー管理
│   ├── metadata.py      # メタデータ管理
│   └── storage.py       # ファイルシステム操作
├── llm/
│   ├── base.py          # 基本インターフェース
│   ├── openai.py        # OpenAI互換コネクタ
│   ├── gemini.py        # Geminiコネクタ
│   └── ollama.py        # Ollamaコネクタ
├── services/
│   ├── summarizer.py    # 要約生成
│   ├── tagger.py        # タグ付け
│   └── context.py       # コンテキスト構築
├── server/
│   ├── websocket.py     # WebSocketサーバー実装
│   ├── api.py           # APIエンドポイント定義
│   └── events.py        # イベント発行/購読
├── cli/
│   └── commands.py      # コマンドラインインターフェース
└── ui/
    └── ...              # UIコンポーネント
```

### 7.1 基本操作フロー

1. **新規ノード作成**
   - NodeManagerがノードオブジェクト生成
   - NodeStorageがファイル保存とノードマップ更新
   - FlowManagerがフロー定義に追加
   - MetadataManagerがインデックス更新
   - イベントを発行して関連クライアントに通知

2. **ノード編集**
   - NodeManagerがノード内容更新
   - メタデータの`updated`属性を`true`に設定
   - 変更イベントを発行

3. **ビルド（要約生成）実行**
   - NodeManagerが`updated="true"`のノードを検索
   - LLMProviderを使って要約とタグを生成
   - NodeStorageがノードファイル更新と`updated="false"`に設定
   - MetadataManagerがタグファイルとインデックスファイル更新
   - 更新イベントを発行

4. **接続変更**
   - NodeManagerが関連ノードの`connections`セクション更新
   - FlowManagerがフロー定義ファイル更新
   - フロー更新イベントを発行

### 7.2 LLMプロンプト例（要約生成）

```
あなたは会話ノードの要約とタグ付けを行う専門家です。
以下のプロンプトと回答のペアを分析し、簡潔な要約とタグを生成してください。

[プロンプト]
{プロンプト全文}

[回答]
{回答全文}

以下の形式で出力してください：
要約: [30-50単語程度の簡潔な説明]
タグ: [3-7個の重要キーワードをカンマ区切り]
```

### 7.3 コンテキスト構築（LLM利用時）

```
[システムプロンプト]
以下の情報を参照して回答してください：

1. 現在のフロー:
[現在のノードのプロンプト]

2. 会話の流れ:
[前のノード1の要約]
[前のノード2の要約]
...
[現在のノードの直前のノード（全文）]

3. 参照情報:
[参照ノードA]: [要約] [#タグ1 #タグ2]
[参照ノードB]: [要約] [#タグ3 #タグ4]
...

詳細情報が必要な場合は「[ノードID]の詳細を知りたい」と指示できます。
```

## 8. 性能と拡張性の考慮事項

### 8.1 ファイルシステム最適化
- 最初はフォルダあたり100ファイルの制限を設定、一巡したら上限を段階的に1000まで増加
- フォルダは000から連番で増加（10進数表記）
- ノードIDとファイルパスのマッピングをTSVで管理

### 8.2 パフォーマンス考慮
- メモリキャッシュによる頻繁なメタデータアクセスの最適化
- インデックスファイルによる検索効率化
- 非同期処理による要約生成などのバックグラウンド処理

### 8.3 拡張性
- モジュール化された設計によるコンポーネント差し替え
- 新LLMプロバイダー追加の容易さ
- 外部ツールとの連携のためのAPIデザイン

### 8.4 将来対応
- ノード数の上限（フォルダ方式で約100万ノード）は現状許容
- 将来的に必要であれば階層的なフォルダ構造への拡張も可能
- 分散ストレージや外部データベースとの連携も検討可能

## 9. ライブラリとしての利用

### 9.1 基本使用例

```python
from vizprompt.core import VizPromptManager

# 任意のディレクトリでVizPromptを初期化
manager = VizPromptManager("/path/to/data")

# 新しいノードを作成
node = manager.create_node(prompt="質問内容", response="回答内容")

# フローにノードを追加
manager.add_node_to_flow("main", node.id)

# 要約を生成
manager.build_summary(node.id)
```

### 9.2 ヘッドレス操作

UIに依存せずに、コマンドラインやその他のアプリケーションからVizPromptの機能を利用できるAPIを提供します。これにより、様々なフロントエンドやツールからの利用が可能になります。

```python
# 例: プログラムからの利用
from vizprompt import VizPrompt

# 初期化
vp = VizPrompt(data_dir="/path/to/storage")

# ノード操作
node_id = vp.create_node(prompt="質問", response="回答")
nodes = vp.search_nodes(tags=["タグ1", "タグ2"], keywords=["キーワード"])
node = vp.get_node(node_id)

# フロー操作
vp.connect_nodes(source_id, target_id, branch_name="分岐名")
vp.rebuild_flow("main", [node_id1, node_id2, node_id3])
```

## 10. GitHub連携の考慮

- すべてのデータをテキストベース（XML/YAML/TSV）で保存
- ファイル数を適切に制限し、GitHubでの管理を容易に
- バイナリファイルを使用せず、差分管理を最適化
- ユーザーが任意でデータディレクトリをGitリポジトリとして管理可能

## 11. 実装優先順位

1. **コアデータ構造**
   - ファイル形式と保存構造
   - 基本的なノード/フロー管理

2. **LLM連携**
   - 初期サポートプロバイダー実装
   - トークンカウントと要約生成

3. **基本機能**
   - 会話フロー管理
   - 要約・タグ付け

4. **分岐機能**
   - 分岐作成と視覚化
   - フロー再定義

5. **高度な機能**
   - コンテキスト最適化
   - 検索と参照機能

## 12. API・インターフェース設計

### 12.1 コマンドラインインターフェース

基本的な操作をコマンドラインから実行可能にするCLIを提供します。UUIDの直接指定が必要となる操作もあるため、複雑な操作はGUIフロントエンドからの利用を推奨します。

```bash
# 基本的な使用例
$ vizprompt create-node --prompt-file input.txt --response-file output.txt
$ vizprompt search --tags "タグ1,タグ2"
$ vizprompt serve --port 8080
```

```python
class VizPromptCLI:
    def __init__(self):
        self.vp = VizPrompt()
    
    def run(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        
        # create-nodeサブコマンド
        create_parser = subparsers.add_parser("create-node")
        create_parser.add_argument("--prompt", required=True)
        create_parser.add_argument("--response", required=True)
        
        # serveサブコマンド
        serve_parser = subparsers.add_parser("serve")
        serve_parser.add_argument("--port", type=int, default=8080)
        
        # コマンド実行
        args = parser.parse_args()
        if args.command == "create-node":
            self.create_node(args)
        elif args.command == "serve":
            self.serve(args)
    
    def create_node(self, args):
        node_id = self.vp.create_node(args.prompt, args.response)
        print(f"Created node: {node_id}")
    
    def serve(self, args):
        print(f"Starting WebSocket server on port {args.port}")
        # WebSocketサーバー起動コード
```

### 12.2 WebSocketサーバー

フロントエンドとの通信にはWebSocketを使用します。これにより、リアルタイムな双方向通信と状態更新通知が可能になります。

```python
# サーバー実装例
async def websocket_handler(websocket, path):
    async for message in websocket:
        data = json.loads(message)
        action = data.get('action')
        
        if action == 'create_node':
            node_id = vp.create_node(
                prompt=data['data']['prompt'], 
                response=data['data']['response']
            )
            await websocket.send(json.dumps({
                'status': 'success',
                'node_id': node_id
            }))
            
        elif action == 'subscribe':
            # イベント購読の処理
            # ...
```

WebSocketを通じて以下のような操作を提供します：
- ノードの作成/取得/更新/削除
- フロー操作（接続/分岐/リンク）
- 検索/フィルタリング
- リアルタイムイベント通知

### 12.3 フロントエンド設計

フロントエンドはVanilla JSで実装され、WebSocketを通じてバックエンドと通信します。
HTML/CSS/JSのみで構成し、必要に応じて少数の軽量ライブラリ（D3.js、Cytoscape.jsなど）を使用します。

```javascript
// クライアント側の通信例
const socket = new WebSocket('ws://localhost:8080');

// メッセージ送信
socket.send(JSON.stringify({
  action: 'create_node',
  data: {
    prompt: '質問内容',
    response: '回答内容'
  }
}));

// レスポンス受信
socket.onmessage = (event) => {
  const response = JSON.parse(event.data);
  if (response.status === 'success') {
    // 作成されたノードIDなどの利用
    console.log('Created node:', response.node_id);
  }
};

// フロー更新を購読
socket.send(JSON.stringify({
  action: 'subscribe',
  data: {
    event: 'flow_updated',
    flow_id: 'main'
  }
}));
```

フロントエンドは疎結合設計のため、将来的に別のフレームワークやアプローチによる実装も容易に行えます。重要な要素として：

1. **グラフ可視化**: ノード間の関係を視覚的に表示するための軽量ライブラリ（例：cytoscape.js, d3.js）
2. **リアルタイム更新**: WebSocketを通じて変更を即座に反映
3. **モジュール化**: 機能ごとに分割された小さなJSモジュール
4. **最小限の依存関係**: CDN経由で少数の信頼できるライブラリのみ使用

### 12.4 WebSocket API プロトコル

クライアントとサーバー間で交換されるメッセージの基本構造：

```javascript
// クライアントからサーバーへのメッセージ
{
  "action": "action_name",  // 実行するアクション
  "data": {                 // アクションに必要なデータ
    // アクション固有のパラメータ
  }
}

// サーバーからクライアントへのレスポンス
{
  "status": "success",      // "success" または "error"
  "data": {                 // レスポンスデータ
    // アクション結果
  },
  "error": {                // エラー時のみ
    "code": "error_code",
    "message": "エラー詳細"
  }
}

// サーバーからクライアントへのイベント通知
{
  "event": "event_name",    // イベント名
  "data": {                 // イベントデータ
    // イベント固有の情報
  }
}
```

基本的なアクション一覧：

1. **ノード操作**
   - `create_node`: 新規ノード作成
   - `get_node`: ノード取得
   - `update_node`: ノード更新
   - `delete_node`: ノード削除

2. **フロー操作**
   - `get_flow`: フロー情報取得
   - `update_flow`: フロー更新
   - `connect_nodes`: ノード間接続
   - `create_branch`: 分岐作成

3. **検索/フィルタリング**
   - `search_nodes`: ノード検索
   - `list_tags`: タグ一覧取得
