from ollama_env_audit.probes.ollama import parse_ollama_ps



def test_parse_ollama_ps_extracts_processor_column() -> None:
    raw = """NAME                ID              SIZE      PROCESSOR    UNTIL
llama3.1:8b         abc123          4.9 GB    100% GPU     4 minutes from now
phi4:latest         def456          8.1 GB    100% CPU     2 minutes from now
"""
    processes = parse_ollama_ps(raw)

    assert len(processes) == 2
    assert processes[0].name == "llama3.1:8b"
    assert processes[0].processor == "100% GPU"
    assert processes[1].processor == "100% CPU"
