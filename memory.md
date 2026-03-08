# Memory — Combat System Implementation

## What's Done
| File | Status | What Changed |
|------|--------|-------------|
| `Entities/enemy_registry.py` | ✅ | 6 enemies, Vine Drain = 15% max HP drain. Encounter: Easy×2→Med×2→Hard→Boss. |
| `Entities/enemies.py` | ✅ | Enemy class with per-enemy attacks, miss, heal, tier-colored draw. |
| `Frame/battle_messages.py` | ✅ | Typewriter message queue, color-coded types Pokémon-style. |
| `Frame/game_state.py` | ✅ | Turn state, revival, stacking debuffs (blindness_chance, confusion_chance, apply_quiz_debuff). |
| `Frame/deck_selector.py` | ✅ | Scans FlashcardUploads/ for JSON decks. |
| `Frame/stage_manager.py` | ✅ | All stages incl. REVIVAL_QUIZ. |
| `Frame/core.py` | ✅ | Turn-based with status effects. |
| `question_wave/question_generator.py` | ✅ | MC-only, 3 random Qs. |
| `question_wave/question_logic.py` | ✅ | Performance tiers, wrong-Q tracking to game_state. |
| `question_wave/question_renderer.py` | ✅ | Word-wrapped text, dynamic box heights, hover effects. |
| `question_wave/question_controller.py` | ✅ | MC-only, always→CARD_REWARD. |
| `Cards/All_cards.py` | ✅ | Sand Throw 6-10, Stick Poke 8-12. |
| `main.py` | ✅ | Full wiring: tiered rewards, no-dupe cards, debuffs, revival, blindness/confusion. |

## Enemies
| Enemy | Tier | HP | Attacks |
|-------|------|----|---------|
| Sludge | Easy | 20 | Slime Throw (12, skip 1), Disgust (0, halve atk) |
| Natbat | Easy | 25 | Sky Dive (15, 20% miss), Bite (10, 20% miss) |
| Vexshroom | Medium | 35 | Doze (0, skip 1), Vine Drain (15% max HP, heals self) |
| Tombworm | Medium | 40 | Coffin Slam (25), Confusion (0, skip 2) |
| The Warden | Hard | 120 | Iron Maiden (35), Key Throw (20) |
| The Cube | Boss | 180 | Corner Jab (40), Flatten (50, 30% miss), Rotate (0, halve dmg) |

## Starter Cards
| Card | Damage | Type |
|------|--------|------|
| Sand Throw / Rock Throw | 6-10 | Ranged |
| Stick Poke / Eye Poke | 8-12 | Physical |

## Card Reward System
- Pool: 60% common, 30% rare, 10% super rare
- Global tracking: The game remembers all cards offered across multiple quizzes and will **never offer the same card twice** until the pool is empty.
- 3/3 correct (Perfect) → pick **2** cards
- 2/3 correct (Great) → pick **1** card
- 1/3 correct (Okay) → **0** cards, game continues (no debuff)
- 0/3 correct (Poor) → **0** cards + stacking debuffs applied

## Game Flow
- **Sequential Combat Text**: The enemy will patiently wait for the player's attack text/effect messages to finish displaying before taking their turn, making combat feel much cleaner.
```
DECK_SELECT → OVERWORLD (3s) → BATTLE (turn-based + messages)
→ POST_BATTLE_WALK (2s) → QUESTION_WAVE (3 MC questions)
→ CARD_REWARD (tier-based picks) → NEXT_STAGE → loop to OVERWORLD
```

## Stacking Debuffs (0/3 quiz, cumulative)
| Debuff | Per Fail | Cap |
|--------|----------|-----|
| Enemy damage multiplier | ×2 (doubles) | ×4 |
| Blindness (player miss chance) | +20% | 60% |
| Confusion (involuntary skip chance) | +20% | 60% |

## Revival System
- On death + revival available + has wrong Qs → REVIVAL_QUIZ
- Answer ALL past wrong questions, 70%+ → revive (HP ≥50, deck restored)
- One-time only. Second death = GAME_OVER.
- HUD shows "♥ Revival available" / "♥ Revival used"
