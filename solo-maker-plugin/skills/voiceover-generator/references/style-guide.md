# Professional Voice & Audio Masterclass

In a product demo, audio is 50% of the experience. This guide teaches you how to engineer AI-generated voiceovers that sound authoritative, empathetic, and human.

---

## 1. The Solo Voice Archetypes

Match your voice selection to your `business-profile.json` brand personality.

| Archetype          | Tone Characteristics                               | Ideal For...                                    |
| :----------------- | :------------------------------------------------- | :---------------------------------------------- |
| **The Strategist** | Mature, resonant, slow pacing, neutral accent.     | PRDs, Business Strategy, Investor updates.      |
| **The Enthusiast** | High pitch variance, rapid pacing, vibrant energy. | Social media ads, "Build in Public" teasers.    |
| **The Mentor**     | Warm, breathy, empathetic pauses, "Smiling" tone.  | Onboarding tutorials, customer success stories. |

---

## 2. Advanced Audio Engineering (SSML & Hints)

Don't just provide text. Provide "Performance Instructions" to the AI.

- **The "Strategic Pause"**: Use `<break time="1s"/>` or `(pause)` after a major benefit.
  - _Example_: "Solo OS saves you 10 hours a week. (pause) Imagine what you could do with that time."
- **The "Pitch Pivot"**: Raise the pitch for the "Reveal" phase.
  - _Example_: "Introducing... [Higher Pitch] The Solo OS."
- **The "Whisper Insight"**: Lower volume for a high-value secret or tip.
  - _Example_: "[whisper] Most people ignore this, but you shouldn't."

---

## 3. Writing for the "The Ear" (Audio Copywriting)

- **Short Sentences**: 1 idea per sentence. 15 words max.
- **Contractions**: "Don't," "You're," "Can't." Avoid formal "Do not" unless you want to sound like a machine.
- **Phonetic Spelling**: If the AI mispronounces your brand or niche jargon, spell it phonetically.
  - _Example_: Use "Saas" (rhymes with glass) instead of spelling out S-A-A-S.

---

## 4. Audio Quality Standards

- **Bitrate**: Export at 320kbps for master files.
- **Background Music**: Use a ducking effect (Ref: `Remotion` audio rules). Music should drop by -15dB whenever the voiceover is active.
- **Silence**: Always include 0.5s of "Room Tone" or silence at the beginning and end of the audio file to avoid abrupt starts/stops.

---

## 5. Integration with Prototype-to-Video

1.  **Script**: Generate the script using the `storyboard-workbook.md` narrative.
2.  **Generate**: Use the `voiceover-generator` with the `Prosody Hints` above.
3.  **Sync**: Ensure the `remotion-video-generator` timestamps align with the key visual transitions.
