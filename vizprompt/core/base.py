import os, re, uuid
from datetime import datetime

class UUIDTimestampManager:
    """
    UUIDとタイムスタンプでファイルを管理するベースクラス
    """

    def __init__(self, data_dir, ext):
        self.data_dir = data_dir
        self.map_path = os.path.join(data_dir, "index.tsv")
        self.ext = ext
        os.makedirs(self.data_dir, exist_ok=True)
        self.tsv_entries = {}  # relpath -> (uuid, timestamp)
        self.uuid_map = {}     # uuid -> [relpath]
        self.check_and_update_map()

    def add_entry(self, relpath, uuid, timestamp):
        """
        エントリを追加
        """
        self.tsv_entries[relpath] = (uuid, timestamp)
        lst = self.uuid_map.setdefault(uuid, [])
        # タイムスタンプ降順（新しい順）で挿入、同一なら先頭
        for i, rp in enumerate(lst):
            ts = self.tsv_entries[rp][1]
            if timestamp >= ts:
                lst.insert(i, relpath)
                return
        lst.append(relpath)

    def check_and_update_map(self):
        """
        TSVファイルとディレクトリの整合性チェック・自動修正
        """
        self.tsv_entries = {}
        self.uuid_map = {}
        if os.path.exists(self.map_path):
            with open(self.map_path, encoding="utf-8") as f:
                first = True
                for line in f:
                    if first:
                        if line.strip().lower().startswith("relpath"):
                            first = False
                            continue
                        first = False
                    parts = line.strip().split("\t")
                    if len(parts) == 3:
                        relpath, uuid, timestamp = parts
                        try:
                            dt = datetime.fromisoformat(timestamp)
                        except Exception:
                            dt = datetime.now().astimezone()
                        self.add_entry(relpath, uuid, dt)

        # ディレクトリ配下の全ファイルを列挙しつつ不足分を即時追加
        changed = False
        for folder in os.listdir(self.data_dir):
            folder_path = os.path.join(self.data_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            regex = re.compile(r"[0-9a-f]+\." + re.escape(self.ext))
            for fname in os.listdir(folder_path):
                if regex.match(fname):
                    relpath = f"{folder}/{fname}"
                    if relpath not in self.tsv_entries:
                        path = os.path.join(self.data_dir, folder, fname)
                        uuid, timestamp = self.get_uuid_and_timestamp_from_file(path)
                        self.add_entry(relpath, uuid, timestamp)
                        changed = True

        # 過剰分を削除
        all_uuid_relpaths = set()
        for relpaths in self.uuid_map.values():
            all_uuid_relpaths.update(relpaths)
        for relpath in list(self.tsv_entries.keys()):
            if relpath not in all_uuid_relpaths:
                self.tsv_entries.pop(relpath)
                changed = True

        # 変更があればTSV書き直し
        if changed:
            self.save_index()

    def save_index(self):
        """
        TSVファイル全体を保存
        """
        with open(self.map_path, "w", encoding="utf-8") as f:
            f.write("relpath\tuuid\ttimestamp\n")
            for relpath, (uuid, timestamp) in self.tsv_entries.items():
                print(relpath, uuid, timestamp.isoformat(), sep="\t", file=f)

    def append_index(self, relpath, uuid, timestamp):
        """
        エントリをTSVに追加
        """
        if os.path.exists(self.map_path):
            with open(self.map_path, "a", encoding="utf-8") as f:
                print(relpath, uuid, timestamp.isoformat(), sep="\t", file=f)
        else:
            # TSVファイルが存在しない場合は新規作成
            self.save_index()

    def get_next_relpath_and_folder(self):
        """
        空きのrelpathを探す
        """
        used = set(self.tsv_entries.keys())
        for i in range(256):
            folder = f"{i:02x}"
            folder_path = os.path.join(self.data_dir, folder)
            os.makedirs(folder_path, exist_ok=True)
            for idx in range(256):
                filename = f"{idx:02x}.{self.ext}"
                relpath = f"{folder}/{filename}"
                if relpath not in used:
                    path = os.path.join(folder_path, filename)
                    if os.path.exists(path):
                        uuid, timestamp = self.get_uuid_and_timestamp_from_file(path)
                        self.add_entry(relpath, uuid, timestamp)
                        with open(self.map_path, "a", encoding="utf-8") as f:
                            f.write(f"{relpath}\t{uuid}\t{timestamp.isoformat()}\n")
                    else:
                        return relpath
        raise Exception("保存上限に達しました")

    def generate_uuid(self):
        """
        重複しないUUIDを生成
        """
        node_id = str(uuid.uuid4())
        while node_id in self.uuid_map:
            node_id = str(uuid.uuid4())
        return node_id

    def get_uuid_and_timestamp_from_file(self, path):
        """
        ファイルからUUIDとタイムスタンプを取得（なければゼロUUIDと現在時刻）
        サブクラスでオーバーライド推奨
        """
        return str(uuid.UUID(int=0)), datetime.now().astimezone()
