# Native Runner Qualification Report

Date: 2026-07-13  
Decision: `NATIVE_RUNNER_ALIGNMENT_COMPLETE`

## Objective evidence

| Native platform | Qualified runner | Workflow run | Exact source SHA | Result | Artifact evidence |
| --- | --- | --- | --- | --- | --- |
| Apple | `djconnect-apple-macos` (`macOS`, `ARM64`, `self-hosted`, `internal-release`, `qualification`, `apple`) | [29246454969](https://github.com/pcvantol/djconnect-app/actions/runs/29246454969) | `2fdfd8a2106f4ed35f54b82bde0bc1fa1271400f` | Success; 67 seconds; no startup failure | `DJConnect-macOS-unsigned.zip`, SHA-256 `f874e410fa49e16b307223f7fbd6f80ca932cadd22fcfba3c720b7c2c1a02a1a` |
| Windows | `djconnect-windows11-parallels` (`Windows`, `X64`, `self-hosted`, `internal-release`, `qualification`, `windows11`, `parallels`) | [29246684022](https://github.com/pcvantol/djconnect-windows/actions/runs/29246684022) | `ac4265c2f0d006a8d614e83bf5d3c2d72019a3eb` | Success; 113 seconds; no startup failure | `DJConnect-Windows-x64-unsigned.zip`, SHA-256 `4e70dfd9b9442c9d99f5427d66a55e180779b240cad45f9140148e10a480c24a` |

Apple evidence records Xcode 26.6 and Swift 6.3.3. Windows evidence records
.NET SDK 10.0.301. Both artifacts and redacted runner evidence JSON files were
uploaded by their workflows.

## Alignment result

- Apple native build/release workflows select the qualified self-hosted macOS
  runner. The ordinary CI job is guarded from fork pull requests and emits
  unsigned artifact plus runner evidence.
- Windows native build and artifact-sanity jobs select the qualified
  self-hosted Windows runner. The public unsigned Windows build has the same
  selector. The runner workflow uses the available Windows PowerShell with an
  explicit non-interactive execution policy and produces a qualified artifact.
- Software Assurance and Trusted Delivery remain certified platform inputs;
  this increment did not change either system.

The successful qualification workflows provide the required native runner
planning, toolchain, artifact and upload evidence. No Apple or Windows build
executed in Codex or on GitHub-hosted Linux.
