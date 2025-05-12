'''VizPromptのコマンドラインインターフェース'''
import argparse

parser = argparse.ArgumentParser(description="VizPrompt CLI")
subparsers = parser.add_subparsers(dest="command", help='トップレベルコマンド', required=True)

# 'chat' サブコマンド
chat_command_parser = subparsers.add_parser("chat", help="LLMとチャットします")
chat_subparsers = chat_command_parser.add_subparsers(dest="service", help='チャットサービス', required=True)

# 'chat gemini' サブコマンド
gemini_parser = chat_subparsers.add_parser("gemini", help="Geminiとチャットします")
gemini_parser.add_argument("prompt", type=str, nargs="?", help="Geminiへのプロンプト")

# 'chat ollama' サブコマンド
ollama_parser = chat_subparsers.add_parser("ollama", help="Ollamaとチャットします")
ollama_parser.add_argument("prompt", type=str, nargs="?", help="Ollamaへのプロンプト")

# 'chat openai' サブコマンド
openai_parser = chat_subparsers.add_parser("openai", help="OpenAIとチャットします")
openai_parser.add_argument("prompt", type=str, nargs="?", help="OpenAIへのプロンプト")

# 'flow' サブコマンド
flow_command_parser = subparsers.add_parser("flow", help="フロー管理コマンド")
flow_subparsers = flow_command_parser.add_subparsers(dest="flow_command", help='フロー操作', required=True)

# 'flow list' サブコマンド
flow_list_parser = flow_subparsers.add_parser("list", help="フロー一覧を表示します")

# 'flow show' サブコマンド
flow_show_parser = flow_subparsers.add_parser("show", help="フローの詳細またはログを表示します")
flow_show_parser.add_argument("id_or_number", type=str, help="フロー番号またはUUID")

import sys, re
from ..core.node import NodeManager
from ..core.flow import FlowManager

base_dir = "project"
node_manager = NodeManager(base_dir=base_dir)
flow_manager = FlowManager(base_dir=base_dir)

def chat(manager, generator, prompt, history=None):
    prompt = prompt.rstrip()
    print(f"{generator.model}: ", end="", flush=True)
    for chunk in generator.generate(prompt, history=history):
        print(chunk, end="", flush=True)
    if not generator.text.endswith("\n"):
        print() # 最後に改行
    generator.show_statistics_short()
    response = generator.text.rstrip()

    # ノード保存処理
    node = manager.create_node(prompt, response, generator)
    print(f"チャット履歴をノードとして保存しました: {node.relpath} (ID: {node.id})")
    return node.id

commands = {
    "/q": "セッションを終了します",
    "/clear": "セッションをクリアします",
    "/flow list": "フロー一覧を表示します",
    "/flow show <id>": "フローの詳細またはログを表示します",
    "/flow select <id>": "フローを選択します",
    "/prev": "前のノードを表示します",
    "/?": "このヘルプを表示します"
}
commands_max = max(len(cmd) for cmd in commands)

def show_commands():
    print("コマンド一覧:")
    for cmd, desc in commands.items():
        print(f"  {cmd:{commands_max}}  {desc}")

def parse_command(line):
    if not line.startswith("/"):
        return None, None
    for command in commands:
        # <xx>の部分を取り除いたのがコマンド本体
        cmd = re.sub(r"<[^>]+>", "", command).rstrip()
        if line.startswith(cmd):
            # <xx>の部分を正規表現でマッチさせる
            # 例: /flow show <id> → /flow show ([^ ]+)
            pattern = re.sub(r"<[^>]+>", r"([^ ]+)", re.escape(command))
            if m := re.fullmatch(pattern, line):
                return cmd, list(m.groups())
            # 引数が間違っている場合
            return command, None
    return None, ["不明なコマンドです。"]

def repl(generator):
    flow = None
    prev_node_id = None
    while True:
        try:
            prompt = input("User: ")
            if prompt is None:
                return
            cmd, args = parse_command(prompt)
            if cmd:
                if args is None:
                    print("引数が違います:", cmd, file=sys.stderr)
                    show_commands()
                    continue
                match cmd:
                    case "/q":
                        return
                    case "/clear":
                        print("セッションをクリアしました。")
                        flow = None
                        continue
                    case "/flow list":
                        cmd_flow_list()
                        continue
                    case "/flow show":
                        print(args)
                        cmd_flow_show(args[0])
                        continue
                    case "/flow select":
                        try:
                            flow = get_flow(args[0])
                            prev_node_id = flow.nodes[-1] if flow.nodes else None
                            print("フローを選択しました:", flow.id, flow.relpath)
                        except Exception as e:
                            print(e, file=sys.stderr)
                        continue
                    case "/prev":
                        if prev_node_id is None:
                            print("前のノードはありません。", file=sys.stderr)
                        else:
                            node = node_manager.get_node(prev_node_id)
                            show_node(node)
                        continue
                    case "/?":
                        show_commands()
                        continue
            elif args:
                print(args[0])
                show_commands()
                continue
            if not flow:
                flow = flow_manager.create_flow(name="Chat Session")
            if prev_node_id is None:
                history_ids = []
            else:
                # 前のノードの履歴を取得
                history_ids = flow.get_history(prev_node_id) or [prev_node_id]
            history = node_manager.get_contents(history_ids)
            curr_node_id = chat(node_manager, generator, prompt, history)
            flow.connect(prev_node_id, curr_node_id)
            flow.save()
            prev_node_id = curr_node_id
            print()
        except EOFError:
            return
        except Exception as e:
            print(f"エラーが発生しました: {e}", file=sys.stderr)

def cmd_chat(args):
    generator = None
    if args.service == "gemini":
        from ..llm import gemini
        generator = gemini.GeminiGenerator()
    elif args.service == "ollama":
        from ..llm import ollama
        generator = ollama.OllamaGenerator()
    elif args.service == "openai":
        from ..llm import openai
        generator = openai.OpenAIGenerator()

    if generator:
        if args.prompt:
            print("User:", args.prompt)
            chat(node_manager, generator, args.prompt)
        else:
            repl(generator)
    else:
        chat_command_parser.print_help()

def cmd_flow(args):
    if args.flow_command == "list":
        cmd_flow_list()
    elif args.flow_command == "show":
        cmd_flow_show(args.id_or_number)
    else:
        flow_command_parser.print_help()

def cmd_flow_list():
    format = len(str(len(flow_manager.tsv_entries)))
    for idx, (_, (id, _)) in enumerate(flow_manager.tsv_entries.items(), 1):
        f = flow_manager.get_flow(id)
        print(f"{idx:{format}}.", f.updated, f.id, f.relpath, f.name, f"({len(f.nodes)})")

def get_flow(id_or_number):
    # 数字なら番号→UUID変換
    if re.fullmatch(r"\d+", id_or_number):
        idx = int(id_or_number)
        entries = list(flow_manager.tsv_entries.items())
        if 1 <= idx <= len(entries):
            id = entries[idx - 1][1][0]
        else:
            raise ValueError("指定された番号のフローは存在しません")
    else:
        id = id_or_number
    return flow_manager.get_flow(id)

def show_node(node):
    node_info = f"{node.timestamp} {node.id} {node.relpath}"
    print(node_info)
    print("-" * len(node_info))
    for j, content in enumerate(node.contents):
        if j:
            print()
        name = "user" if content["role"] == "user" else node.model
        text = content["text"].rstrip()
        print(f"{name}: {text}")
        c, d, r = content["count"], content["duration"], content["rate"]
        print(f"[{c} / {d:.2f} s = {r:.2f} tps]")

def cmd_flow_show(id_or_number):
    try:
        flow = get_flow(id_or_number)
    except Exception as e:
        print(e, file=sys.stderr)
        return
    print("Flow:", flow.updated, flow.id, flow.relpath)
    histories = flow.get_histories()
    for i, history in enumerate(histories, 1):
        print()
        print(f"======== 履歴 {i}/{len(histories)} ========")
        for node_id in history:
            node = node_manager.get_node(node_id)
            print()
            show_node(node)

def main():
    args = parser.parse_args()
    if args.command == "chat":
        cmd_chat(args)
    elif args.command == "flow":
        cmd_flow(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
