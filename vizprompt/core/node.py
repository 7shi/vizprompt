import os
import datetime
import uuid

import xml.etree.ElementTree as ET

def normalize(text, cdata=False):
    """文字列を正規化する関数"""
    text = text.rstrip().replace("\r\n", "\n").replace("\r", "\n")
    if cdata:
        # CDATA内に ']]>' が含まれている場合は分割して複数のCDATAセクションにする
        text = text.replace("]]>", "]]]]><![CDATA[>")
    return text

def _get_uuid_from_xml(path):
    """XMLファイルのルート要素id属性からUUIDを取得（プル型パーサー使用）。なければゼロUUIDを返す"""
    try:
        for _, elem in ET.iterparse(path, events=("start",)):
            if elem.tag == "node":
                uuid_str = elem.attrib.get("id")
                if uuid_str:
                    return uuid_str
                else:
                    break
    except Exception:
        pass
    return str(uuid.UUID(int=0))

class Node:
    """
    XMLノード情報と一対一対応するデータクラス
    """
    def __init__(
        self,
        id: str,
        timestamp: str,
        prompt: str,
        response: str,
        model: str,
        user_stats: dict,
        assistant_stats: dict,
        summary: dict,
        tags: list,
        path: str,
    ):
        self.id = id
        self.timestamp = timestamp
        self.prompt = prompt
        self.response = response
        self.model = model
        self.user_stats = user_stats
        self.assistant_stats = assistant_stats
        self.summary = summary
        self.tags = tags
        self.path = path

    def to_xml(self) -> str:
        """
        NodeインスタンスをXML文字列に変換
        """
        prompt = normalize(self.prompt, cdata=True)
        response = normalize(self.response, cdata=True)
        # user_stats, assistant_stats, summary, tagsはdict/list前提
        user = self.user_stats
        assistant = self.assistant_stats
        summary = self.summary
        tags = self.tags
        xml = f'''<?xml version="1.0" encoding="utf-8"?>
<node id="{self.id}" timestamp="{self.timestamp}">
<prompt><![CDATA[
{prompt}
]]></prompt>
<response><![CDATA[
{response}
]]></response>
<metadata>
<model>{self.model}</model>
<stats role="user" count="{user.get("count",0)}" duration="{user.get("duration",0):.2f}" rate="{user.get("rate",0):.2f}" />
<stats role="assistant" count="{assistant.get("count",0)}" duration="{assistant.get("duration",0):.2f}" rate="{assistant.get("rate",0):.2f}" />
<summary updated="{summary.get("updated","false")}" last_built="{summary.get("last_built",self.timestamp)}" />
<tags>{''.join(f'<tag>{t}</tag>' for t in tags)}</tags>
</metadata>
</node>
'''.lstrip()
        return xml

    def save(self):
        """
        NodeインスタンスをXMLファイルに保存
        """
        xml = self.to_xml()
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(xml)

class NodeManager:
    def __init__(self, base_dir="project"):
        self.base_dir = base_dir
        self.nodes_dir = os.path.join(base_dir, "nodes")
        self.map_path = os.path.join(base_dir, "metadata", "node_map.tsv")
        os.makedirs(self.nodes_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.map_path), exist_ok=True)
        self.tsv_entries = []
        self.uuid_map = {}
        self._check_and_update_node_map()

    # Nodeファイルとnode_map.tsvの整合性チェック・自動修正
    def _check_and_update_node_map(self):
        # 1. node_map.tsvの読み込み＋キャッシュ初期化
        self.tsv_entries = []
        self.uuid_map = {}
        tsv_set = set()
        if os.path.exists(self.map_path):
            with open(self.map_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) == 3:
                        uuid, folder, fname = parts
                        self.tsv_entries.append((folder, fname))
                        self.uuid_map[(folder, fname)] = uuid
                        tsv_set.add((folder, fname))

        # 2. nodes_dir配下の全XMLファイルを列挙しつつ不足分を即時追加
        file_entries = []
        changed = False
        for folder in os.listdir(self.nodes_dir):
            folder_path = os.path.join(self.nodes_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            for fname in os.listdir(folder_path):
                if fname.endswith(".xml") and len(fname) == 6:
                    entry = (folder, fname)
                    file_entries.append(entry)
                    if entry not in tsv_set:
                        xml_path = os.path.join(self.nodes_dir, folder, fname)
                        uuid = _get_uuid_from_xml(xml_path)
                        while uuid in self.uuid_map.values():
                            # UUID重複時は新しいUUIDを生成
                            uuid = str(uuid.uuid4())
                        self.tsv_entries.append(entry)
                        self.uuid_map[entry] = uuid
                        changed = True
        file_set = set(file_entries)

        # 3. 過剰エントリ削除
        for entry in list(self.tsv_entries):
            if entry not in file_set:
                self.tsv_entries.remove(entry)
                self.uuid_map.pop(entry, None)
                changed = True

        # 4. フラグが立っていればTSV書き直し
        if changed:
            with open(self.map_path, "w", encoding="utf-8") as f:
                for folder, fname in self.tsv_entries:
                    uuid = self.uuid_map.get((folder, fname), "")
                    f.write(f"{uuid}\t{folder}\t{fname}\n")

    def _get_next_folder_and_filename(self):
        # TSVキャッシュベースで空きを探す
        used = set(self.tsv_entries)
        for i in range(256):
            folder = f"{i:02x}"
            folder_path = os.path.join(self.nodes_dir, folder)
            os.makedirs(folder_path, exist_ok=True)
            for idx in range(256):
                filename = f"{idx:02x}.xml"
                key = (folder, filename)
                xml_path = os.path.join(folder_path, filename)
                if key not in used:
                    # 空きが見つかった場合、既存ファイルがあればUUIDを取得してキャッシュ・TSVに追記
                    if os.path.exists(xml_path):
                        uuid = _get_uuid_from_xml(xml_path)
                        self.tsv_entries.append(key)
                        self.uuid_map[key] = uuid
                        # TSV追記
                        if os.path.exists(self.map_path):
                            with open(self.map_path, "a", encoding="utf-8") as f:
                                f.write(f"{uuid}\t{folder}\t{filename}\n")
                        else:
                            with open(self.map_path, "w", encoding="utf-8") as f:
                                f.write(f"{uuid}\t{folder}\t{filename}\n")
                    return folder, filename, folder_path
        raise Exception("ノード保存上限に達しました")

    def _generate_node_id(self):
        # UUIDベースのノードID
        node_id = str(uuid.uuid4())
        uuid_set = set(self.uuid_map.values())
        # 既存のUUIDと重複しないようにする
        while node_id in uuid_set:
            node_id = str(uuid.uuid4())
        return node_id

    def save_node(self, prompt, response, g):
        prompt = normalize(prompt, cdata=True)
        response = normalize(response, cdata=True)
        folder, filename, folder_path = self._get_next_folder_and_filename()
        node_path = os.path.join(folder_path, filename)

        # 新規作成
        node_id = self._generate_node_id()
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        node = Node(
            id=node_id,
            timestamp=timestamp,
            prompt=prompt,
            response=response,
            model=g.model,
            user_stats={
                "count": getattr(g, "prompt_count", 0),
                "duration": getattr(g, "prompt_duration", 0.0),
                "rate": getattr(g, "prompt_rate", 0.0),
            },
            assistant_stats={
                "count": getattr(g, "eval_count", 0),
                "duration": getattr(g, "eval_duration", 0.0),
                "rate": getattr(g, "eval_rate", 0.0),
            },
            summary={
                "updated": "false",
                "last_built": timestamp,
            },
            tags=[],
            path=node_path,
        )
        node.save()

        # キャッシュ・TSV追記
        self.tsv_entries.append((folder, filename))
        self.uuid_map[(folder, filename)] = node_id
        with open(self.map_path, "a", encoding="utf-8") as f:
            f.write(f"{node_id}\t{folder}\t{filename}\n")

        return node
