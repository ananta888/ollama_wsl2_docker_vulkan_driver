from __future__ import annotations

from ollama_env_audit.probes.wsl import WSLProbe


def test_parse_vulkan_summary_detects_dozen_device() -> None:
    raw = """
deviceType         = PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU
deviceName         = Microsoft Direct3D12 (AMD Radeon(TM) 780M)
driverName         = Dozen
"""

    device_name, driver_name, uses_cpu = WSLProbe._parse_vulkan_summary(raw)

    assert device_name == "Microsoft Direct3D12 (AMD Radeon(TM) 780M)"
    assert driver_name == "Dozen"
    assert uses_cpu is False


def test_parse_vulkan_summary_detects_llvmpipe_cpu_fallback() -> None:
    raw = """
deviceType         = PHYSICAL_DEVICE_TYPE_CPU
deviceName         = llvmpipe (LLVM 20.1.2, 256 bits)
driverName         = llvmpipe
"""

    device_name, driver_name, uses_cpu = WSLProbe._parse_vulkan_summary(raw)

    assert device_name == "llvmpipe (LLVM 20.1.2, 256 bits)"
    assert driver_name == "llvmpipe"
    assert uses_cpu is True
