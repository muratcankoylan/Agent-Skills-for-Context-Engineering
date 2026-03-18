# TTS Engine Optimization (Settings Card)

Reference settings for getting the best output from Modern TTS engines (ElevenLabs, OpenAI).

## 📊 Generic Tuning Parameters

| Parameter       | Recommended (Solo) | Why?                                                        |
| :-------------- | :----------------- | :---------------------------------------------------------- |
| **Stability**   | 0.5 - 0.6          | Prevents "Monotone" while keeping it professional.          |
| **Similarity**  | 0.8                | Keeps the unique voice profile distinct.                    |
| **Style Exag.** | 0.0 - 0.2          | Solo brands usually benefit from "Natural" over "Dramatic." |

## 🎙 Recommended Voice Profiles

### For "The Strategist" (Authoritative)

- **ElevenLabs**: "Brian" or "Adam"
- **OpenAI**: "Onyx"

### For "The Support Coach" (Empathetic)

- **ElevenLabs**: "Rachel" or "Lily"
- **OpenAI**: "Nova"

## 🛠 Advanced Tuning

If the AI mispronounces your brand name:

1.  **Phonetic Spelling**: Use `Claw-d` instead of `Claude`.
2.  **Parentheses**: Group words to force pacing `(The strategic) (framework)`.
3.  **Caps**: Use ALL CAPS for acronyms to ensure they are spelled out (e.g., SIRET).
