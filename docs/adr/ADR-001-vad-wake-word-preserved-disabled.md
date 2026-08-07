# ADR-001: VAD and Wake Word — Preserved but Disabled

**Date**: 2026-08-06  
**Status**: Active  
**Component**: `services/vad_service.py`, `services/wake_word_service.py`

## Context

The current production deployment uses **Push-to-Talk only** (microphone never listens automatically).
VADService and WakeWordService were candidates for deletion during the production audit.

## Decision

The services are **preserved but disabled via configuration**. They are NOT deleted.

**Rationale**: Raspberry Pi deployments may need hands-free, automatic voice activation in the future.
The services are production-quality and have no failures.

## Configuration Flags (settings.py)

`enable_vad: false`            -- Set true on Pi for auto voice activation  
`enable_wake_word: false`      -- Set true on Pi for Hey Helpdesk detection  
`wake_word_phrase: Hey Helpdesk`  
`wake_word_sensitivity: 0.5`

## Current Default Behaviour (Push-to-Talk Mode)

- ENABLE_VAD=false    -> VADService NOT started. Microphone is silent.  
- ENABLE_WAKE_WORD=false -> WakeWordService NOT started.  
- PUSH_TO_TALK=true   -> All recording initiated by user button press.

## To Enable on Pi (Future)

Set: ENABLE_VAD=true, ENABLE_WAKE_WORD=true, PUSH_TO_TALK=false

WARNING: Do not run PTT and VAD simultaneously -- conflicting microphone ownership.

## Consequences

- No regression: PTT-only deployments unaffected.
- No code to redevelop: future Pi activation is config-only.
