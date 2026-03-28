# Architektur

## Leitlinien

- SOLID durch kleine, klar abgegrenzte Module
- Clean Architecture mit Trennung von Domain, Application, Infrastructure und CLI
- ehrliche Diagnostik ohne implizite GPU-Annahmen
- Dependency Injection ueber Protokolle und Service-Container
- sichere externe Befehlsausfuehrung ohne Shell-Injection aus Nutzereingaben

## Schichten

### Domain

`domain/` enthaelt reine Modelle, Enums, Exceptions und Protokolle. Hier liegen keine CLI- oder Infrastrukturdetails.

### Infrastructure

`SubprocessExecutor` kapselt externe Kommandos. `execute()` ist fuer idempotente Diagnostik, `spawn()` fuer bewusst gestartete Runtime-Prozesse.

### Probes

- `WindowsProbe`: Host-Version, CPU, RAM, GPUs, WSL- und Docker-Indizien
- `WSLProbe`: Distribution, Kernel, Device-Nodes, Tool-Evidenz, GPU-Naehe
- `DockerProbe`: Engine, Context, Runtimes, Smoke-Test, GPU-Kandidaten
- `OllamaProbe`: Binary, API, Modelle, Prozessliste, GPU-Indikatoren

### Runtime

Jeder Launcher hat genau eine Verantwortung: den Startplan eines Modus beschreiben und optional starten. Dadurch bleiben CLI und Benchmarking von Low-Level-Kommandos entkoppelt.

### Benchmark

`BenchmarkService` misst direkt ueber die Ollama-HTTP-API. Dadurch bleibt die Benchmark-Schicht reproduzierbar und austauschbar. Ein spaeterer Streaming- oder Multi-Prompt-Runner kann ueber dieselbe Abstraktion ergaenzt werden.

### Reporting

Renderer arbeiten ausschliesslich auf `AuditReport`-Modellen. JSON, Markdown und HTML sind dadurch austauschbare Ausgabeformen ohne Business-Logikduplikation.

### Application

`InspectionService`, `RuntimeService`, `BenchmarkService` und `LocalWebService` orchestrieren die Kernfaelle. Die CLI verdrahtet diese Services nur noch.
