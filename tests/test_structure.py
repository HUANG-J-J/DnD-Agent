import subprocess
import sys


def test_engine_does_not_import_openai():
    # 开一个新的 Python 进程，sys.modules 是干净的，结果才可信
    code = (
        "import sys, engine.character, engine.dice, engine.state; "
        "assert 'openai' not in sys.modules, 'engine 不应依赖 openai'"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_agent_importable_without_api_key(monkeypatch):
    # 模拟 CI：没有 API key 时，import 不应该崩
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    import agent.loop_raw  # noqa: F401
