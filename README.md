# ollama-env-audit

`ollama-env-audit` ist ein Diagnose-, Benchmark-, Reporting- und Runtime-Toolkit fuer Windows 11 + WSL2 + Docker + Ollama Setups mit Fokus auf AMD Ryzen APUs und Radeon iGPUs.

Das Projekt behauptet GPU-Nutzung nicht pauschal. Es sammelt stattdessen reproduzierbare Evidenz, markiert Unsicherheiten offen und leitet daraus eine begruendete Empfehlung fuer `windows-native`, `wsl-native` oder `docker-wsl` ab.

## Architekturueberblick

Das Projekt folgt einer modularen Clean-Architecture-Struktur:

- `domain`: Modelle, Enums, Protokolle und Fehlerklassen
- `infrastructure`: sichere externe Befehlsausfuehrung und Logging
- `probes`: ehrliche Analyse fuer Windows, WSL2, Docker und Ollama
- `runtime`: startbare Runtime-Launcher pro Modus
- `benchmark`: reproduzierbare API-basierte Benchmarks
- `application`: Orchestrierung von Inspection, Runtime und Web-Ansicht
- `recommendation`: transparente regelbasierte Entscheidung
- `reporting`: JSON-, Markdown- und HTML-Renderer
- `cli`: Typer-basierte Kommandos

## Repository-Struktur

```text
project-root/
  src/
    ollama_env_audit/
      application/
      benchmark/
      cli/
      config/
      domain/
      infrastructure/
      probes/
      recommendation/
      reporting/
      runtime/
  tests/
  docs/
  examples/
  README.md
  pyproject.toml
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## CLI

```bash
ollama-env-audit inspect
ollama-env-audit recommend
ollama-env-audit report --format markdown --output report.md
ollama-env-audit benchmark --mode wsl-native --model llama3.2:3b
ollama-env-audit run --mode docker-wsl --dry-run
ollama-env-audit run --mode docker-wsl --execute
ollama-env-audit serve-web --host 127.0.0.1 --port 8765
```

## Was der aktuelle Stand kann

- Windows-, WSL-, Docker- und Ollama-Probes mit expliziter Unsicherheitskommunikation
- tiefere WSL- und Docker-Evidenzsammlung fuer GPU-nahe Voraussetzungen
- Runtime-Launcher fuer `windows-native`, `wsl-native` und `docker-wsl`
- API-basierte Benchmarks mit Latenz-, Dauer- und Tokens/Sekunde-Metriken
- Reports in JSON, Markdown und HTML
- lokale Web-Ansicht mit Live-Inspection und `/report.json`
- Tests fuer Executor, Benchmarking, Renderer, CLI und Recommendation Engine

## Wichtige Einschraenkungen

- Docker-GPU-Support wird weiterhin nur dann als wahrscheinlich markiert, wenn sowohl Host-GPU-Geraetekandidaten sichtbar sind als auch Containerstart nachweisbar funktioniert. Das ist bewusst konservativ.
- `run --execute` startet bewusst nur klar definierte Kommandos und nutzt keine dynamisch zusammengebauten Shell-Strings.
- Ein erfolgreicher Runtime-Start beweist noch keine GPU-Beschleunigung. Diese Aussage entsteht erst aus kombinierter Evidenz und Benchmarking.

## Reporting

- `--format json` fuer maschinenlesbare Reports
- `--format markdown` fuer reproduzierbare Issue- oder Gist-Berichte
- `--format html` fuer lokale Browseransicht oder Web-Archivierung

## Troubleshooting

### Docker meldet keine GPU

Das Tool nimmt nicht an, dass Docker unter WSL2 automatisch GPU-Zugriff hat. Wenn nur Device-Kandidaten, aber keine starke Laufzeitevidenz vorliegen, bleibt die Bewertung bewusst vorsichtig.

### WSL2 hat keine `/dev/dxg`-, `/dev/kfd`- oder `/dev/dri`-Devices

Dann wird GPU-Nutzung in WSL2 nicht behauptet. Der Report weist das explizit als fehlende Voraussetzung aus.

### Benchmark scheitert trotz erreichbarer API

Dann sind haeufig Modellname, Laufzeitmodus oder Serverzustand das Problem. Der Benchmark-Report gibt HTTP-Status, Beobachtungen und die genutzte Ziel-URL aus.

## Entwicklung

```bash
pytest
```
