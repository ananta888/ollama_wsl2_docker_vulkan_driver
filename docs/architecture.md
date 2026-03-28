# Architektur

## Leitlinien

- SOLID-Prinzipien durch kleine, klar abgegrenzte Module
- Clean Architecture mit Trennung von Domain, Application, Infrastructure und CLI
- ehrliche Diagnostik: keine impliziten GPU-Annahmen
- Dependency Injection ueber Protokolle und konfigurierbare Services
- sichere externe Befehlsausfuehrung ohne Shell-Injection aus Nutzereingaben

## Zusammenspiel

1. Die CLI laedt Konfiguration und erzeugt einen `InspectionService`.
2. Der `InspectionService` fuehrt die vier Kern-Probes aus.
3. Die `RecommendationEngine` leitet daraus Laufzeitbewertungen und eine Empfehlung ab.
4. `ReportRenderer`-Implementierungen serialisieren den Gesamtbericht als JSON oder Markdown.
5. Die Benchmark-Schicht ist bewusst separat gehalten, damit spaeter echte Modellmessungen ergaenzt werden koennen, ohne Probe- oder Reporting-Logik umzubauen.
