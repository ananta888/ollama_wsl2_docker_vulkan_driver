# Windows PowerShell handoff

## Current state

- Project path: `C:\Users\pst\IdeaProjects\ollama_wsl2_docker_vulkan_driver`
- WSL distro under test: Ubuntu 24.04.4 on WSL2
- Goal: get Ollama to use the AMD iGPU from WSL2 and then from Docker-in-WSL

## What was verified already

- WSL sees `/dev/dxg`
- Docker test containers can also see `/dev/dxg` when started with `--device /dev/dxg`
- Ollama model cache is now reusable via Docker volume:
  - `ollama-env-audit-model-cache`
- Cached model confirmed reusable without re-download:
  - `qwen2.5:0.5b`

## Important findings

- Native WSL Ollama used `100% CPU`
- Docker Ollama used `100% CPU`
- `OLLAMA_VULKAN=true` still used CPU only
- `vulkaninfo --summary` inside WSL reported:
  - `deviceType = PHYSICAL_DEVICE_TYPE_CPU`
  - `deviceName = llvmpipe`
- That means WSL currently does **not** expose a usable GPU compute path to Ollama

## Most likely blocker

The blocker appears to be on the Windows/WSL graphics stack, not in the Ollama app logic:

- AMD driver / WSL graphics integration
- WSL GPU/Vulkan exposure from Windows into Ubuntu
- possibly missing or broken host-side D3D12/Vulkan translation path

## Recommended next checks in elevated Windows PowerShell

Run these from **Administrator PowerShell**:

```powershell
wsl --status
wsl --version
wsl --update
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterCompatibility
```

Optional deeper checks:

```powershell
dxdiag /t "$env:TEMP\\dxdiag.txt"
Get-Content "$env:TEMP\\dxdiag.txt" | Select-String "Card name","Driver Version","Feature Levels"
```

## After Windows-side checks

Re-enter WSL and re-run:

```bash
vulkaninfo --summary
PYTHONPATH=src python3 -m ollama_env_audit.cli.app inspect --json
```

The target is to stop seeing `llvmpipe` and instead see a real AMD/Radeon/D3D12-backed GPU device.

## Useful local assets

- Reusable model cache volume:
  - `ollama-env-audit-model-cache`
- Extracted test binary used in WSL:
  - `/tmp/ollama-wsl-test`

## Expected success signal

Success is not just "container starts". Success should look like:

- `vulkaninfo --summary` shows a real GPU, not `llvmpipe`
- Ollama startup logs stop saying only `id=cpu`
- `ollama ps` shows GPU instead of `100% CPU`
