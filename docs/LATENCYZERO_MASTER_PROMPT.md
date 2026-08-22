# MASTER ARCHITECTURE & IMPLEMENTATION PROMPT: LatencyZero Pro

Act as a Principal Systems Engineer, Windows Kernel Specialist, and Senior UI/UX Designer. Build "LatencyZero Pro", an ultra-low latency Windows optimization and workstation performance tuning suite.

LatencyZero must be safe, reversible, modular, and natively protected by the KeyForge cryptographic licensing framework.

---

## 1. Product Vision & Core Architecture

* **Product Name**: LatencyZero Pro
* **Category**: Windows Performance, Gaming, and Real-Time Workstation Optimizer
* **Target Audience**: Competitive Gamers, Audio Engineers (DAW/ASIO), Video Editors, Streamers, and Power Users.
* **Tech Stack Options** (Choose the most robust):
  * **Frontend/GUI**: Modern C# WPF (.NET 8) with Fluent UI / Custom Dark theme OR Tauri + React (TypeScript) for a lightweight footprint (< 15 MB RAM).
  * **Engine/Backend**: Native Windows API (P/Invoke), PowerShell Core, and Windows Registry / Service management.
  * **Licensing**: KeyForge Universal Client SDK (Offline Ed25519 + Online REST Activation).

---

## 2. Safety First: System Restore & Zero-Risk Rollback Engine

Before any tweak or registry alteration is executed, LatencyZero must:
1. **Automated System Restore Point**: Call Windows System Restore (`Checkpoint-Computer` / `SRSetRestorePoint`) before modifying system state.
2. **Snapshot & Backup Registry**: Save before/after registry snapshots (`.reg` backup) to `%APPDATA%\LatencyZero\Backups\`.
3. **1-Click "Restore Factory Defaults"**: A dedicated emergency button that reverts every applied tweak back to stock Windows defaults.

---

## 3. Deep System Optimization Modules

### Module A: CPU & Scheduling Engine
* **High-Precision Timer Resolution**: Force global 0.5ms (5000ns) timer resolution (`NtSetTimerResolution`) to minimize input polling delay.
* **Win32PrioritySeparation**: Optimize foreground thread responsiveness (Mask `0x26` / Short, Variable, 3:1 ratio).
* **Core Unparking & C-States**: Configure power schema to disable aggressive core parking on high-performance desktop CPUs.
* **Multimedia Class Scheduler Service (MMCSS)**: Optimize `SystemResponsiveness = 0` and prioritize gaming/audio threads (`NetworkThrottlingIndex = 0xFFFFFFFF`).

### Module B: GPU & Display Latency
* **Message Signaled Interrupts (MSI Mode)**: Tool to verify and safely switch GPU and NVMe controllers to MSI mode with High priority.
* **Hardware-Accelerated GPU Scheduling (HAGS)**: Toggle and optimize HAGS registry state.
* **DWM & Fullscreen Exclusive Optimizations**: Disable Fullscreen Optimizations (FSO) flag toggles for competitive titles.
* **NVIDIA/AMD Driver Profile Cleaners**: Strip background telemetry from display drivers.

### Module C: Network & TCP/IP Optimization
* **Nagle's Algorithm Disabling**: Set `TcpAckFrequency = 1` and `TCPNoDelay = 1` on active network adapters for zero packet buffering.
* **Network Throttling Elimination**: Adjust `NetworkThrottlingIndex` to eliminate bandwidth caps during high CPU load.
* **DNS Benchmarking & Flushing**: Automatic 1-click flush and recommendation for Cloudflare (1.1.1.1) or Google DNS.

### Module D: DPC Latency & Real-Time Audio
* **Real-Time DPC Latency Monitor**: Live in-app monitor displaying kernel execution spikes (using ETW / Event Tracing for Windows).
* **Power Throttling Disable**: Ensure real-time audio threads never drop to efficiency cores during active sessions.

### Module E: Windows Debloat & Telemetry Reducer
* **Telemetry & Diagnostics**: Disable Connected User Experiences and Telemetry service (`DiagTrack`).
* **Cortana & Bing Search in Start Menu**: Disable background web search processes.
* **GameDVR & Background Recording**: Toggle off background game clip capture to reclaim 5–10% GPU overhead.

---

## 4. KeyForge Licensing & Feature Gating

Integrate the **KeyForge Client SDK** (`https://key-forge-lac.vercel.app`):
* **Product ID**: `latency-zero`
* **Public Verification Key**: Embedded Ed25519 Public Key (PEM format).

### Feature Tiers:
* **Free Edition**:
  * Basic Temp File / Cache Wiper
  * Simple Network Flush
  * Real-Time Latency Meter
* **Pro Edition (`pro` Feature Gate)**:
  * 0.5ms High-Precision Kernel Timer
  * MSI Mode & GPU Scheduling Tuner
  * TCP Nagle & Sub-millisecond Ping Optimizer
  * 1-Click "Competitive Mode" Profile Switcher
  * Core Unparking & MMCSS Priority Tuning

### Offline Validation Logic:
```csharp
// Example KeyForge Gate in C#
if (KeyForgeClient.HasFeature("kernel_timer_tweak")) {
    KernelTimer.SetResolution(5000); // 0.5ms
} else {
    ShowProUpgradeModal("High-Precision Timer Resolution is a Pro feature.");
}
```

---

## 5. UI/UX Design System (Linear / Raycast Dark Aesthetic)

* **Design Language**: Deep Slate background (`#090d16`), elevated card containers (`#111827`), 1px subtle borders (`rgba(255, 255, 255, 0.08)`), electric cyan/indigo accents (`#38bdf8` / `#6366f1`).
* **Iconography**: 100% Vector SVGs (Lucide style). **Zero emojis**.
* **Real-Time Telemetry Bar**:
  * Live DPC Latency (Microseconds gauge: `< 50µs` = Emerald Green, `> 500µs` = Amber/Red).
  * Current Timer Resolution (`0.500 ms` indicator).
  * Active Power Plan badge.
* **Actions**:
  * Big Primary Button: **"⚡ 1-Click Optimize (Competitive Preset)"**
  * Granular Accordion Tabs: **CPU | GPU | Network | Audio | Windows Clean**
  * Backup & Rollback Drawer: **"↺ Revert System to Stock"**

---

## 6. Deliverables & Code Structure

Provide the complete, production-ready codebase structured as follows:
```
LatencyZero/
├── src/
│   ├── Core/
│   │   ├── RestorePoint.cs       # Windows System Restore wrapper
│   │   ├── RegistryManager.cs    # Transactional registry modifier with rollback
│   │   ├── TimerResolution.cs    # NtSetTimerResolution P/Invoke wrapper
│   │   ├── NetworkOptimizer.cs   # TCPNoDelay & adapter tuning
│   │   ├── GpuOptimizer.cs       # MSI Mode & HAGS manager
│   │   └── DpcMonitor.cs         # Real-time kernel latency sampler
│   ├── Licensing/
│   │   └── KeyForgeClient.cs     # KeyForge SDK integration (Ed25519 + Online/Offline)
│   ├── UI/
│   │   ├── MainWindow.xaml       # Modern Linear-inspired Dark UI
│   │   ├── MainWindow.xaml.cs
│   │   ├── Components/           # Telemetry Gauges, Toggle Cards, Toast Alerts
│   │   └── Styles/               # Brushes, Animations, Glassmorphic effects
│   └── App.xaml
├── assets/                       # Vector SVGs, App Icon (.ico)
├── installer/                    # Inno Setup / WiX installer script
├── tests/                        # Unit tests for registry backups and licensing
└── README.md                     # Documentation, build instructions, and changelog
```

Generate clean, robust, thoroughly commented code with comprehensive error handling for all administrative permissions (`requireAdministrator` UAC manifest).
