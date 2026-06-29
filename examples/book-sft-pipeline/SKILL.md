---
name: book-sft-pipeline
description: "This skill should be used for book-to-SFT pipelines: ePub extraction, literary segmentation, author-voice dataset construction, style-transfer training, LoRA workflows, and model evaluation for voice replication."
version: 2.0.0
---

# Book SFT Pipeline

A complete system for converting books into SFT datasets and training style-transfer models. This skill teaches the pipeline from raw ePub to a model that writes in any author's voice.

## When to Activate

Activate this skill when:
- Building fine-tuning datasets from literary works
- Creating author-voice or style-transfer models
- Preparing training data for Tinker or similar SFT platforms
- Designing text segmentation pipelines for long-form content
- Training small models (8B or less) on limited data

## Core Concepts

### The Three Pillars of Book SFT

**1. Intelligent Segmentation**
Text chunks must be semantically coherent. Breaking mid-sentence teaches the model to produce fragmented output. Target: 150-400 words per chunk, always at natural boundaries.

**2. Diverse Instruction Generation**
Use multiple prompt templates and system prompts to prevent overfitting. A single prompt style leads to memorization. Use 15+ prompt templates with 5+ system prompts.

**3. Style Over Content**
The goal is learning the author's rhythm and vocabulary patterns, not memorizing plots. Synthetic instructions describe what happens without quoting the text.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                           │
│  Coordinates pipeline phases, manages state, handles failures   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┬───────────────┐
       ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  EXTRACTION  │ │ SEGMENTATION │ │  INSTRUCTION │ │   DATASET    │
│    AGENT     │ │    AGENT     │ │    AGENT     │ │   BUILDER    │
│ ePub → Text  │ │ Text → Chunks│ │ Chunks →     │ │ Pairs →      │
│              │ │ 150-400 words│ │ Prompts      │ │ JSONL        │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
┌──────────────┐               ┌──────────────┐
│   TRAINING   │               │  VALIDATION  │
│    AGENT     │               │    AGENT     │
│ LoRA on      │               │ AI detector  │
│ Tinker       │               │ Originality  │
└──────────────┘               └──────────────┘
```

## Phase 1: Text Extraction

### Critical Rules
1. **Always source ePub over PDF** - OCR errors become learned patterns
2. **Use paragraph-level extraction** - Extract from `<p>` tags to preserve breaks
3. **Remove front/back matter** - Copyright and TOC pollute the dataset

```python
# Extract text from ePub paragraphs
from epub2 import EPub
from bs4 import BeautifulSoup

def extract_epub(path):
    book = EPub(path)
    chapters = []
    for item in book.flow:
        html = book.get_chapter(item.id)
        soup = BeautifulSoup(html, 'html.parser')
        paragraphs = [p.get_text().strip() for p in soup.find_all('p')]
        chapters.append('\n\n'.join(p for p in paragraphs if p))
    return '\n\n'.join(chapters)
```

## Phase 2: Intelligent Segmentation

### Smaller Chunks + Overlap

Smaller chunks (150-400 words) produce more training examples and better style transfer than larger chunks (250-650).

```python
def segment(text, min_words=150, max_words=400):
    paragraphs = text.split('\n\n')
    chunks, buffer, buffer_words = [], [], 0
    
    for para in paragraphs:
        words = len(para.split())
        if buffer_words + words > max_words and buffer_words >= min_words:
            chunks.append('\n\n'.join(buffer))
            # Keep last paragraph for overlap
            buffer = [buffer[-1], para] if buffer else [para]
            buffer_words = sum(len(p.split()) for p in buffer)
        else:
            buffer.append(para)
            buffer_words += words
    
    if buffer:
        chunks.append('\n\n'.join(buffer))
    return chunks
```

### Expected Results

For an 86,000-word book:
- Old method (250-650 words): ~150 chunks
- New method (150-400 + overlap): ~300 chunks
- With 2 variants per chunk: 600+ training examples

## Phase 3: Diverse Instruction Generation

### The Key Insight

Using a single prompt template causes memorization. Diverse templates teach the underlying style.

```python
SYSTEM_PROMPTS = [
    "You are an expert creative writer capable of emulating specific literary styles.",
    "You are a literary writer with deep knowledge of classic prose styles.",
    "You are a creative writer skilled at emulating distinctive authorial voices.",
    "You write prose that captures the essence of modernist literature.",
    "You are a talented writer who can channel classic American authors.",
]

PROMPT_TEMPLATES = [
    "Write a passage in the style of {author}: {desc}",
    "Channel {author}'s voice to write about: {desc}",
    "In {author}'s distinctive prose style, describe: {desc}",
    "Write this scene as {author} would have: {desc}",
    "Using {author}'s repetitive technique, describe: {desc}",
    "Capture the rhythm of {author} in this passage: {desc}",
    "Write like {author}: {desc}",
    "In the voice of {author}, write: {desc}",
    "This is a literary exercise. Write like {author}: {desc}",
    "Can you write in {author}'s style? {desc}",
]
```

### Instruction Generation

```python
INSTRUCTION_PROMPT = """Describe what is happening in this excerpt in 2-3 sentences.
Focus on: characters present, actions, emotions, setting.
Do NOT quote the text directly.

Excerpt:
{text}
"""

# Use a fast, cheap LLM (e.g., Gemini Flash)
instruction = llm_call(INSTRUCTION_PROMPT.format(text=chunk))
```

## Phase 4: Dataset Construction

### Message Format

```json
{
    "messages": [
        {"role": "system", "content": "You are an expert creative writer..."},
        {"role": "user", "content": "Write in the style of Author: Scene description..."},
        {"role": "assistant", "content": "The actual book text from chunk..."}
    ]
}
```

### Multiple Variants Per Chunk

```python
def build_examples(chunk, instruction, author, variants=2):
    examples = []
    for i in range(variants):
        system = SYSTEM_PROMPTS[i % len(SYSTEM_PROMPTS)]
        template = PROMPT_TEMPLATES[(chunk.id + i) % len(PROMPT_TEMPLATES)]
        user = template.format(author=author, desc=instruction)
        examples.append({"messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": chunk.text}
        ]})
    return examples
```

## Phase 5: LoRA Training on Tinker

### Configuration

```python
CONFIG = {
    "model_name": "Qwen/Qwen3-8B-Base",  # Base, not instruct
    "lora_rank": 32,                      # 352MB adapter
    "learning_rate": 5e-4,                # Higher for LoRA
    "batch_size": 4,
    "epochs": 3,
}
```

### Why Base Model?

Use **base** (pretrained) models, not instruction-tuned versions:
- Base models are more malleable for new styles
- Instruct models have patterns that resist overwriting
- Style is a low-level pattern that base models capture better

### Training Loop

```python
import tinker
from tinker import types

training_client = await service_client.create_lora_training_client_async(
    base_model="Qwen/Qwen3-8B-Base",
    rank=32
)

for epoch in range(3):
    for batch in batches:
        await training_client.forward_backward_async(batch, loss_fn="cross_entropy")
        await training_client.optim_step_async(types.AdamParams(learning_rate=5e-4))

result = await training_client.save_weights_for_sampler_async(name="final")
```

## Phase 6: Validation

### Modern Scenario Test

Test with scenarios that couldn't exist in the original book:

```python
TEST_PROMPTS = [
    "Write about a barista making lattes",
    "Describe lovers communicating through text messages",
    "Write about someone anxious about climate change",
]
```

If the model applies style markers to modern scenarios, it learned **style**, not **content**.

### Originality Verification

```bash
# Search training data for output phrases
grep "specific phrase from output" dataset.jsonl
# Should return: No matches
```

### AI Detector Testing

Test outputs with GPTZero, Pangram, or ZeroGPT.

## Known Issues and Solutions

### Character Name Leakage

**Symptom**: Model uses original character names in new scenarios.
**Cause**: Limited name diversity from one book.
**Solution**: Train on multiple books or add synthetic examples.

### Model Parrots Exact Phrases

**Symptom**: Outputs contain exact sentences from training data.
**Cause**: Too few prompt variations or too many epochs.
**Solution**: Use 15+ templates, limit to 3 epochs.

### Fragmented Outputs

**Symptom**: Sentences feel incomplete.
**Cause**: Poor segmentation breaking mid-thought.
**Solution**: Always break at paragraph boundaries.

## Guidelines

1. **Always source ePub over PDF** - OCR errors become learned patterns
2. **Never break mid-sentence** - Boundaries must be grammatically complete
3. **Use diverse prompts** - 15+ templates, 5+ system prompts
4. **Use base models** - Not instruct versions
5. **Use smaller chunks** - 150-400 words for more examples
6. **Reserve test set** - 50 examples minimum
7. **Test on modern scenarios** - Proves style transfer vs memorization
8. **Verify originality** - Grep training data for output phrases

## Expected Results

| Metric | Value |
|--------|-------|
| Training examples | 500-1000 per book |
| Model | Qwen/Qwen3-8B-Base |
| LoRA rank | 32 |
| Adapter size | ~350 MB |
| Training time | ~15 min |
| Loss reduction | 90%+ |
| Style transfer success | ~50% perfect |

## Cost Estimate

| Component | Cost |
|-----------|------|
| LLM (instruction generation) | ~$0.50 |
| Tinker training (15 min) | ~$1.50 |
| **Total** | **~$2.00** |

## Integration with Context Engineering Skills

This example applies several skills from the Agent Skills for Context Engineering collection:

### project-development
The pipeline follows the staged, idempotent architecture pattern:
- **Acquire**: Extract text from ePub
- **Prepare**: Segment into training chunks
- **Process**: Generate synthetic instructions
- **Parse**: Build message format
- **Render**: Output Tinker-compatible JSONL
- **Train**: LoRA fine-tuning
- **Validate**: Modern scenario testing

Each phase is resumable and produces intermediate artifacts for debugging.

### context-compression
Segmentation is a form of context compression for training. The core insight from context-compression applies: information density matters more than information quantity. Smaller, coherent chunks (150-400 words) produce better style transfer than larger, diluted chunks.

The two-tier strategy mirrors context compression evaluation:
- Tier 1: Fast, deterministic compression
- Tier 2: LLM-assisted for edge cases

### multi-agent-patterns
The pipeline uses the **supervisor/orchestrator** pattern:
- Orchestrator coordinates phases and manages state
- Specialized agents (Extraction, Segmentation, Instruction, Builder) have isolated contexts
- Each agent receives only the information needed for its task

This matches the principle that sub-agents exist primarily to isolate context rather than simulate roles.

### evaluation
Validation follows the **end-state evaluation** pattern:
- Functional testing: Does output match expected style markers?
- Originality verification: Is content genuinely generated?
- External validation: AI detector scores

The "modern scenario" test is a form of out-of-distribution evaluation that proves generalization.

### context-fundamentals
Prompt diversity prevents attention collapse on single patterns. When training with identical prompt structures, the model memorizes the instruction-response mapping. Diverse templates force attention across the style patterns themselves.

## References

Internal references:
- [Segmentation Strategies](./references/segmentation-strategies.md) - Text chunking patterns
- [Tinker Format Specification](./references/tinker-format.md) - Datum structure
- [Tinker API Documentation](./references/tinker.txt) - Full API reference

Related skills from Agent Skills for Context Engineering:
- project-development - Pipeline architecture patterns
- context-compression - Compression strategies  
- multi-agent-patterns - Agent coordination
- evaluation - Evaluation frameworks
- context-fundamentals - Attention and information density

External resources:
- [Research Paper](https://arxiv.org/pdf/2510.13939) - Chakrabarty et al. 2025
- [Dataset on Hugging Face](https://huggingface.co/datasets/MuratcanKoylan/gertrude-stein-style-sft)
- [Gertrude Stein Case Study](./examples/gertrude-stein/) - Complete working example

---

## Skill Metadata

**Created**: 2025-12-26
**Last Updated**: 2025-12-28
**Author**: Muratcan Koylan
**Version**: 2.0.0
**Standalone**: Yes (separate from main context-engineering collection)
