"""
单词图谱 - 后端 API
优先从 wordmap.csv / words.txt 查找关系词与释义，未找到再调用 AI。
关系只保留：反义、近义、形近词。
"""
import csv
import json
import os
import random
import threading
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# 后端目录（wordmap.csv、words.txt、llm_config.json 所在目录）
BACKEND_DIR = Path(__file__).resolve().parent
WORDMAP_CSV = BACKEND_DIR / "wordmap.csv"
WORDS_TXT = BACKEND_DIR / "words.txt"
LLM_CONFIG_FILE = BACKEND_DIR / "llm_config.json"

# 大模型配置（可被设置面板修改，持久化到 llm_config.json）
DEFAULT_LLM_CONFIG = {
    "base_url": "https://api.siliconflow.cn/v1",
    "api_key": "sk-vpkcvhavxbiakutcmrtikekoxscnkwfeeuqrzefcleilcyaf",
    "model": "deepseek-ai/DeepSeek-V3",
}
_llm_config = dict(DEFAULT_LLM_CONFIG)
_llm_config_lock = threading.Lock()

# 本地数据：启动时加载
_words_definitions = {}   # word_lower -> definition 字符串
_wordmap = {}             # word_lower -> { synonyms, antonyms, spelling } 各为 list[str]
_file_write_lock = threading.Lock()  # 写文件时加锁，避免并发写乱


def _load_llm_config():
    """从 llm_config.json 加载大模型配置，不存在则用默认"""
    global _llm_config
    if not LLM_CONFIG_FILE.exists():
        return
    try:
        with open(LLM_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        with _llm_config_lock:
            for k in ("base_url", "api_key", "model"):
                if k in data and data[k] is not None and str(data[k]).strip():
                    _llm_config[k] = str(data[k]).strip()
    except Exception:
        pass


def _get_llm_config():
    """返回当前大模型配置副本"""
    with _llm_config_lock:
        return dict(_llm_config)


def _save_llm_config(updates: dict):
    """更新并持久化大模型配置。updates 可含 base_url, api_key, model。"""
    global _llm_config
    with _llm_config_lock:
        for k in ("base_url", "api_key", "model"):
            if k in updates and updates[k] is not None:
                _llm_config[k] = str(updates[k]).strip()
        try:
            with open(LLM_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(_llm_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _parse_csv_cell(cell: str) -> list:
    """解析 CSV 单元格为单词列表（逗号分隔，去空）"""
    if not cell or not str(cell).strip():
        return []
    return [w.strip() for w in str(cell).strip().split(",") if w.strip()]


def _load_words_txt():
    """加载 words.txt：word -> definition"""
    global _words_definitions
    _words_definitions = {}
    if not WORDS_TXT.exists():
        return
    with open(WORDS_TXT, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "\t" not in line:
                continue
            word, _, def_part = line.partition("\t")
            word = word.strip().lower()
            if word:
                _words_definitions[word] = def_part.strip()


def _load_wordmap_csv():
    """加载 wordmap.csv：word -> 各类关系词列表。用 utf-8-sig 避免 BOM 导致首列读不到 'word'。"""
    global _wordmap
    _wordmap = {}
    if not WORDMAP_CSV.exists():
        return
    with open(WORDMAP_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 兼容可能的 BOM 或首列名差异
            word = (row.get("word") or row.get("\ufeffword") or "").strip().lower()
            if not word:
                continue
            _wordmap[word] = {
                "synonyms": _parse_csv_cell(row.get("Synonyms", "")),
                "antonyms": _parse_csv_cell(row.get("Antonyms", "")),
                "spelling": _parse_csv_cell(row.get("spelling", "")),
            }


def _to_items(word_list: list) -> list:
    """将 [word, ...] 转为 [{word, definition}, ...]，definition 从 words.txt 取"""
    out = []
    for w in word_list:
        w = str(w).strip().lower()
        if not w:
            continue
        defn = _words_definitions.get(w, "")
        out.append({"word": w, "definition": defn})
    return out


def _normalize_items(items, default_def=""):
    """将 [str] 或 [{word, definition}] 统一为 [{word, definition}]"""
    if not items:
        return []
    out = []
    for x in items:
        if isinstance(x, dict):
            w = str(x.get("word", x.get("w", ""))).strip()
            d = str(x.get("definition", x.get("def", default_def))).strip()
            out.append({"word": w, "definition": d or _words_definitions.get(w.lower(), default_def)})
        else:
            w = str(x).strip().lower()
            if w:
                out.append({"word": w, "definition": _words_definitions.get(w, default_def)})
    return out


def _lookup_local(word: str) -> dict | None:
    """从 wordmap.csv + words.txt 查找。若 wordmap 中有该词则返回完整结果，否则返回 None。"""
    w = word.strip().lower()
    if not w:
        return None
    definition = _words_definitions.get(w, "")
    row = _wordmap.get(w)
    if row is None:
        return None
    return {
        "word": w,
        "definition": definition,
        "synonyms": _to_items(row["synonyms"]),
        "antonyms": _to_items(row["antonyms"]),
        "similar_spelling": _to_items(row["spelling"]),
    }


def _get_word_relations_from_ai(word: str) -> dict:
    """调用 AI 获取关系词（反义、近义、形近词）。若单词可能拼写错误则返回 error。"""
    prompt = f"""请针对英文单词 "{word}" 判断是否为常见英文单词，再按下面规则返回 JSON。

若该词不是标准英文单词或很可能拼写错误（如明显 typo、不存在的词），只返回：
{{"error": "单词可能拼写错误", "spell_error": true}}

若该词是合法英文单词，则返回以下完整 JSON，不要其他说明：
{{
  "word": "{word}",
  "definition": "该词的中文释义，一句话",
  "synonyms": [{{"word": "近义词1", "definition": "其释义"}}, {{"word": "近义词2", "definition": "其释义"}}],
  "antonyms": [{{"word": "反义词1", "definition": "其释义"}}, {{"word": "反义词2", "definition": "其释义"}}],
  "similar_spelling": [{{"word": "形近词1", "definition": "其释义"}}]
}}

合法词时的要求：
- definition: 该单词的简明中文释义，一句话内
- synonyms: 3-5 个常用近义词，每项 {{"word": "英文", "definition": "中文释义"}}
- antonyms: 2-4 个常用反义词，每项同上；若无反义词则 []
- similar_spelling: 拼写相近、易混淆的单词 0-3 个，每项同上；若没有则 []
只输出上述其中一种 JSON，不要 markdown 代码块。"""

    try:
        cfg = _get_llm_config()
        client = OpenAI(api_key=cfg.get("api_key") or "sk-", base_url=cfg.get("base_url") or "https://api.openai.com/v1")
        model = cfg.get("model") or "gpt-3.5-turbo"
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        if data.get("spell_error") or data.get("error"):
            return {
                "word": word,
                "definition": "",
                "synonyms": [],
                "antonyms": [],
                "similar_spelling": [],
                "error": data.get("error", "单词可能拼写错误"),
            }
        syn = data.get("synonyms", []) or data.get("近义词", [])
        ant = data.get("antonyms", []) or data.get("反义词", [])
        similar = data.get("similar_spelling") or data.get("similar_spelling_words") or []
        if not similar and isinstance(data.get("形近词"), list):
            similar = data["形近词"]
        return {
            "word": data.get("word", word),
            "definition": data.get("definition", ""),
            "synonyms": _normalize_items(syn),
            "antonyms": _normalize_items(ant),
            "similar_spelling": _normalize_items(similar),
        }
    except json.JSONDecodeError as e:
        return {"word": word, "definition": "", "synonyms": [], "antonyms": [], "similar_spelling": [], "error": str(e)}
    except Exception as e:
        return {"word": word, "definition": "", "synonyms": [], "antonyms": [], "similar_spelling": [], "error": str(e)}


def _words_from_items(items: list) -> str:
    """从 [{word, definition}, ...] 取出 word 列表，逗号拼接（供 CSV 写入）"""
    if not items:
        return ""
    return ",".join(str(x.get("word", x) if isinstance(x, dict) else x).strip() for x in items if x)


def _save_ai_result_to_files(result: dict) -> None:
    """将 AI 返回的结果追加保存到 wordmap.csv 和 words.txt（仅当无 error 时）。"""
    if result.get("error") or not result.get("word"):
        return
    with _file_write_lock:
        w = (result.get("word") or "").strip().lower()
        if not w:
            return
        # 若本地已有该词（如并发时另一请求已写入），不再追加，避免重复行
        if w in _wordmap:
            return
        # 1) 追加到 wordmap.csv（反义、近义、形近词）
        synonyms = _words_from_items(result.get("synonyms", []))
        antonyms = _words_from_items(result.get("antonyms", []))
        similar_spelling = _words_from_items(result.get("similar_spelling", []))
        need_header = not WORDMAP_CSV.exists() or WORDMAP_CSV.stat().st_size == 0
        row = [w, synonyms, antonyms, similar_spelling]
        if not need_header:
            with open(WORDMAP_CSV, "r", encoding="utf-8-sig") as f:
                first = f.readline().strip()
            cols = first.split(",")
            if len(cols) == 3:
                row = [w, synonyms, similar_spelling]
            elif len(cols) >= 7:
                row = [w, synonyms, antonyms, similar_spelling, "", "", ""]
        with open(WORDMAP_CSV, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if need_header:
                writer.writerow(["word", "Synonyms", "Antonyms", "spelling"])
            writer.writerow(row)
        # 写入内存，下次直接命中
        _wordmap[w] = {
            "synonyms": [x.get("word", x) if isinstance(x, dict) else x for x in result.get("synonyms", []) if x],
            "antonyms": [x.get("word", x) if isinstance(x, dict) else x for x in result.get("antonyms", []) if x],
            "spelling": [x.get("word", x) if isinstance(x, dict) else x for x in result.get("similar_spelling", []) if x],
        }
        # 2) 若释义不在 words.txt 则追加
        definition = (result.get("definition") or "").strip()
        if definition and w not in _words_definitions:
            with open(WORDS_TXT, "a", encoding="utf-8") as f:
                f.write(f"{w}\t{definition}\n")
            _words_definitions[w] = definition


def get_word_relations(word: str) -> dict:
    """先查本地 wordmap.csv + words.txt，没有再问 AI；AI 结果会保存到文件。"""
    w = word.strip().lower()
    if not w:
        return {
            "word": w,
            "definition": "",
            "synonyms": [],
            "antonyms": [],
            "similar_spelling": [],
            "error": "单词不能为空",
        }
    result = _lookup_local(w)
    if result is not None:
        return result
    result = _get_word_relations_from_ai(w)
    if not result.get("definition") and w in _words_definitions:
        result["definition"] = _words_definitions[w]
    if not result.get("error"):
        _save_ai_result_to_files(result)
    return result


# 常见单词池（随机一词用）；若有 words.txt 可从中采样
WORD_POOL = [
    "happy", "sad", "beautiful", "ugly", "big", "small", "fast", "slow",
    "love", "hate", "begin", "end", "create", "destroy", "brave", "cowardly",
    "bright", "dim", "calm", "anxious", "generous", "stingy", "honest", "dishonest",
    "back", "significant", "skill", "public", "go", "fish", "set", "table", "day",
]


@app.route("/api/word/<word>", methods=["GET"])
def word_relations(word):
    """获取指定单词的关系词（含名词、形容词、动词）"""
    word = word.strip().lower()
    if not word:
        return jsonify({"error": "单词不能为空"}), 400
    result = get_word_relations(word)
    return jsonify(result)


@app.route("/api/word/random", methods=["GET"])
def random_word():
    """随机返回一个单词及其关系"""
    if _words_definitions:
        pool = list(_words_definitions.keys())
        if pool:
            word = random.choice(pool)
        else:
            word = random.choice(WORD_POOL)
    else:
        word = random.choice(WORD_POOL)
    result = get_word_relations(word)
    return jsonify(result)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/llm-config", methods=["GET"])
def get_llm_config():
    """返回当前大模型配置（base_url, api_key, model）"""
    return jsonify(_get_llm_config())


@app.route("/api/llm-config", methods=["PUT"])
def put_llm_config():
    """更新大模型配置。body: { base_url?, api_key?, model? }"""
    data = request.get_json(silent=True) or {}
    updates = {}
    for k in ("base_url", "api_key", "model"):
        if k in data:
            updates[k] = data[k]
    if updates:
        _save_llm_config(updates)
    return jsonify(_get_llm_config())


# 启动时加载本地数据
_load_words_txt()
_load_wordmap_csv()
_load_llm_config()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
