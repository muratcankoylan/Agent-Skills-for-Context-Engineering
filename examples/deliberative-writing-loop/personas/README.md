# Personas

A persona is compiled from a corpus directory of `.txt` or `.md` files containing one
writer's prose. Recommended corpus size: 3,000 to 20,000 words. Below ~1,500 words the
stylometric profile is noisy and the tacit-knowledge extraction overgeneralizes.

```
personas/<name>/corpus/*.txt   # you provide these
personas/<name>/persona.json   # compiled artifact (gitignored; contains corpus text)
```

Compile:

```bash
dwl compile-persona --name orwell --corpus personas/orwell/corpus --provider anthropic
```

`--provider none` computes only the deterministic layers (stylometry, exemplars, slop
reference). The tacit-knowledge layer needs a model and materially changes results;
compile with a real provider for any serious run.

## Sample persona

`sample-essayist/` is an original synthetic corpus written for this repository so tests
run without third-party text. It is deliberately voice-heavy (aphoristic, concrete,
skeptical) so stylometric distances are visible in small tests.

## Using real writers

Drop any writer's text into a corpus directory. For public-domain writers, Project
Gutenberg is the clean source:

```bash
# Mark Twain, "How to Tell a Story and Other Essays" (PG 3250)
mkdir -p personas/twain/corpus
curl -L https://www.gutenberg.org/cache/epub/3250/pg3250.txt -o personas/twain/corpus/essays.txt

# Virginia Woolf, "The Common Reader" (PG 64457, pre-1929 US public domain)
mkdir -p personas/woolf/corpus
curl -L https://www.gutenberg.org/cache/epub/64457/pg64457.txt -o personas/woolf/corpus/common-reader.txt
```

Strip the Gutenberg license header/footer before compiling; it is boilerplate, not the
author, and it will contaminate both the stylometry and the slop reference distribution.

For living writers, use text you have the right to process, and treat the persona
artifact as private material: `persona.json` embeds the corpus verbatim (it is the slop
profiler's reference distribution), which is why compiled personas are gitignored.

## Ethics

Persona compilation is for style transfer with consent or for writers whose work is in
the public domain. Do not compile personas to impersonate living people without their
permission. Detector scores (Pangram) are diagnostics in the benchmark, never an
optimization target; see `src/dwl/adapters/pangram.py` for the enforced policy.
