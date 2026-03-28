# ollama-env-audit

`ollama-env-audit` ist ein Diagnose-, Benchmark- und Reporting-Toolkit fuer Windows 11 + WSL2 + Docker + Ollama Setups mit Fokus auf AMD Ryzen APUs und Radeon iGPUs.

Der Fokus liegt auf ehrlicher Analyse statt pauschaler GPU-Versprechen. Das Tool prueft explizit, welche Voraussetzungen auf dem aktuellen System vorhanden sind, welche Unsicherheiten bleiben und welcher Betriebsmodus sinnvoll erscheint.

## Zielsetzung

Das Projekt vergleicht diese Modi:

- `windows-native`
- `wsl-native`
- `docker-wsl`

Es beantwortet insbesondere diese Fragen:

- Ist GPU-Unterstuetzung auf diesem System ueberhaupt nachweisbar?
- Welche Voraussetzungen fehlen fuer WSL2- oder Docker-basierte GPU-Nutzung?
- Ist Ollama erreichbar und laeuft es mutmasslich auf CPU oder GPU?
- Welcher Betriebsmodus ist auf Basis der Befunde aktuell am sinnvollsten?

## Architekturueberblick

Das Projekt folgt einer klar getrennten, testbaren Architektur:

- `domain`: Domänenmodelle, Enums, Protokolle, Fehlerklassen
- `application`: Orchestrierung von Probes, Empfehlung und Reporting
- `infrastructure`: sichere Befehlsausfuehrung und Logging
- `probes`: Systempruefungen fuer Windows, WSL2, Docker und Ollama
- `recommendation`: transparente, regelbasierte Empfehlung
- `reporting`: Markdown- und JSON-Renderer
- `cli`: Typer-basierte Benutzeroberflaeche
- `benchmark`: reproduzierbare Benchmark-Schnittstelle fuer den Ausbau
- `runtime`: abstrahierte Runtime-Modi und deren Beschreibung

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

## CLI-Beispiele

```bash
ollama-env-audit inspect
ollama-env-audit recommend
ollama-env-audit report --format markdown --output report.md
```

## MVP-Status

Der aktuelle MVP liefert:

- Probe-Grundgerueste fuer Windows, WSL2, Docker und Ollama
- sichere Command-Execution-Abstraktion
- regelbasierte Empfehlung fuer Runtime-Modi
- JSON- und Markdown-Reports
- Tests fuer Parser, Renderer, Empfehlung, Executor und CLI

Noch nicht final umgesetzt:

- reproduzierbare End-to-End-Benchmarks mit Modellstart
- aktive Runtime-Orchestrierung fuer jeden Modus
- lokale WebUI
- tiefe GPU-Telemetrie innerhalb von Containern

## Troubleshooting

### Docker meldet keine GPU

Das Tool geht nicht davon aus, dass Docker unter WSL2 automatisch GPU-Zugriff hat. Wenn keine explizite Evidenz gefunden wird, wird `docker-wsl` als unsicher oder CPU-only markiert.

### WSL2 hat keine Geraete wie `/dev/dxg`

Dann wird GPU-Nutzung in WSL2 nicht behauptet. Der Report weist das explizit als fehlende Voraussetzung aus.

### Ollama API ist nicht erreichbar

Dann kann das Tool zwar den Installationsstatus pruefen, aber keine Laufzeitbeobachtung ueber laufende Modelle liefern.

## Entwicklung

```bash
pytest
```

Weitere Architekturdetails stehen in `docs/architecture.md`.
