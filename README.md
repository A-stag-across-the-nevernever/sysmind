# Sysmind

A local-AI companion for managing your Linux (Parrot OS) machine — updates, disk space,
security, services — in your own language. Ask in English, Urdu, Arabic, whatever you
think in, and it replies in kind. Commands stay valid shell, always.

## Two minds, not one

Sysmind runs **two models in two slots**, because no small model is good at both speaking
Urdu and writing correct shell:

| Slot | Job | Speaks |
|------|-----|--------|
| **conscious** | reasoning, explanation, talking to you | your language |
| **unconscious** | shell, configs, system commands | code |

They hand off to each other. The conscious slot turns your request into a task for the
unconscious slot, which writes the command; the conscious slot then explains that command
back to you in your language.

The unconscious slot can be a **pure code model with no natural language at all** — a base
coder that only completes code. It is prompted with comment headers rather than
instructions, so instruction-tuned and base models both work.

**The command you are shown is the command the coder wrote.** The conscious model writes
prose around it and never gets to write the command itself — that is enforced in code, not
asked for in a prompt. It cannot narrate one thing and run another.

Each slot is independently **local or API**:

```json
"slots": {
  "conscious":   {"backend": "ollama", "model": "qwen3:8b"},
  "unconscious": {"backend": "openai", "model": "qwen2.5-coder",
                  "base_url": "https://your-endpoint/v1",
                  "api_key_env": "YOUR_KEY_VAR"}
}
```

Keys are read from the named environment variable — never stored in the config file.
With both slots local, nothing leaves your machine.

## Install

```bash
cd sysmind
./setup.sh
```

Runs a health check, then asks a few questions: how hands-off, how much RAM (picks the
model pair), reply language, scan depth, notifications, launch method.

Then calibrate the pair and go:

```bash
sysmind-sync calibrate
sysmind
```

## Calibration

`sysmind-sync calibrate` runs both models through the same probes at the same moment and
works out which one belongs in which slot. **You don't declare which is which — it
measures.** Put them in backwards and it swaps them.

It checks that the conscious slot can actually produce prose *in your language* (by script,
not by English keywords), and that the unconscious slot produces shell that actually parses.
A model that produces no natural language is barred from the conscious slot outright.

```bash
sysmind-sync calibrate   # run the handshake
sysmind-sync status      # show the current profile
```

## The four modes

| Mode | What happens |
|------|--------------|
| **Advisor** | AI explains, you copy/paste commands yourself |
| **Assistant** | AI suggests, you approve each command |
| **Autopilot** | Anything you've permitted runs; everything else asks |
| **Full Auto** | Dashboard only; opens the menu on demand |

## How permission works

Anything sysmind has not been told about **asks**. Nothing runs unbidden, ever. When it
asks, you have four answers:

```
Execute? [Y/n/always/never]
```

| | this time | remembered |
|---|---|---|
| `Y` | runs | no — asks again |
| `n` | doesn't run | no — asks again |
| `always` | runs | **allow list** |
| `never` | doesn't run | **block list** |

`always` and `never` are how you make something known. `Y` and `n` are one-off answers.

**Allow list** — narrow and exact. Permitting `apt` does *not* unlock `apt remove`; each
thing earns its own permission. When you say `always`, you choose the breadth yourself:
this exact command, or the whole `apt:install` family.

**Block list** — broad. Refusing `rm` catches `rm -rf /`, `/bin/rm`, `sudo rm`, and
`$(rm ...)`. Refusing a specific command also catches its variants with extra flags. It
ships seeded with `rm`, `dd`, `mkfs` and friends; `blocklist_enabled: false` drops those
defaults but **never** drops entries you declared yourself.

A `never` outranks an `always`. Both are editable in `~/.config/sysmind/config.json`.

Sysmind also remembers how often you approved or rejected each thing, and shows you before
asking again:

```
Run: apt install htop
  history: this exact command: 0x approved, 3x rejected  |  'apt:install': 0x approved, 3x rejected
```

If you keep approving the same family one-off, it offers to permit it properly. That offer
counts **your approvals only** — never the machine's own repetitions — and never appears on
the automatic path, which stays silent.

## Safety

- Every suggested command is parsed with `bash -n` before you are offered it. Invalid shell
  is discarded, never shown as runnable.
- A fenced block is **one** command, however many lines it spans. A `for` loop runs as a
  loop, not as three broken fragments.
- Only `bash`/`sh`/`shell`/`zsh`/`console` fences are treated as runnable. A bare fence is not.

## Commands

```bash
sysmind                  # the main menu
sysmind-sync calibrate   # calibrate the model pair
sysmind-sync status      # show the sync profile
sysmind-doctor           # health check
sysmind-scan low         # refresh the system snapshot
```

## Model pairs

The installer picks a pair from your RAM. `qwen3` handles language (strong Urdu,
Apache-2.0); `qwen2.5-coder` handles shell.

| RAM | conscious | unconscious |
|-----|-----------|-------------|
| 4 GB | `qwen3:1.7b` | `qwen2.5-coder:1.5b` |
| **8 GB** | **`qwen3:8b`** | **`qwen2.5-coder:7b`** |
| 16 GB | `qwen3:14b` | `qwen2.5-coder:14b` |
| 24–32 GB | `qwen3:32b` | `qwen3-coder:30b` |

Bigger `qwen3` speaks better Urdu, so size up the conscious slot if RAM allows. Two models
on 8 GB is tight — Ollama swaps them on demand, or point one slot at an API endpoint.

**Dedicated Urdu open-weights** (Cohere's Tiny Aya, Alif 1.0 8B) are on Hugging Face but
**not** in the Ollama library — using them means a manual GGUF import via `ollama create`,
not a one-line pull. Tiny Aya is CC-BY-NC (non-commercial; fine for personal use) and is
better at explaining than at precise reasoning — a reasonable conscious slot, never an
unconscious one. **Aya Expanse** is on Ollama but does **not** cover Urdu.

## Status

The logic is covered by tests. **It has not yet been run against real models on a real
Parrot box** — treat the first run as a shakedown.

Tests write to a throwaway directory and never touch your real config:

```bash
python3 -m pytest tests/
```

## Licence

AGPLv3 — see [LICENSE](LICENSE).
