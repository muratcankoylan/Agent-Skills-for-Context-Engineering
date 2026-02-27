# Bağlam Mühendisliği için Ajan Yetenekleri (Agent Skills for Context Engineering)

[English](README.md) • [Türkçe](README.tr.md)

Üretim standartlarında yapay zeka ajan sistemleri oluşturmak için bağlam mühendisliği prensiplerine odaklanan, kapsamlı ve açık kaynaklı bir Ajan Yetenekleri koleksiyonu. Bu yetenekler, herhangi bir ajan platformunda ajan etkinliğini maksimize etmek için bağlamı (context) düzenleme sanatını ve bilimini öğretir.

## Bağlam Mühendisliği Nedir?

Bağlam mühendisliği, dil modelinin bağlam penceresini (context window) yönetme disiplinidir. Etkili talimatlar hazırlamaya odaklanan "İstem Mühendisliğinden (Prompt Engineering)" farklı olarak, bağlam mühendisliği modelin sınırlı dikkat bütçesine (attention budget) giren tüm bilgilerin bütünsel olarak düzenlenmesini ele alır: sistem istemleri, araç tanımları, alınan belgeler, mesaj geçmişi ve araç çıktıları.

Temel zorluk, bağlam pencerelerinin ham token kapasitesi ile değil, dikkat mekanikleriyle kısıtlı olmasıdır. Bağlam uzunluğu arttıkça modeller tahmin edilebilir bozulma (degradation) kalıpları sergiler: "ortada kaybolma (lost-in-the-middle)" fenomeni, U-şekilli dikkat eğrileri ve dikkat kıtlığı. Etkili bağlam mühendisliği, istenen sonuçların olasılığını maksimize eden, en yüksek sinyalli jetonların (high-signal tokens) olası en küçük kümesini bulmak demektir.

## Atıflar

Bu depo (repository), statik yetenek mimarisi üzerine temel bir çalışma olarak akademik araştırmalarda alıntılanmıştır:

> "Statik yetenekler iyi bilinse de [Anthropic, 2025b; Muratcan Koylan, 2025], MCE (Meta Bağlam Mühendisliği), manuel yetenek mühendisliği ile otonom kendi kendini geliştirme arasında köprü kurarak bunları dinamik olarak geliştiren ilk çalışmalardan biridir."

— [Meta Context Engineering via Agentic Skill Evolution](https://arxiv.org/pdf/2601.21557), Peking Üniversitesi Genel Yapay Zeka Devlet Anahtar Laboratuvarı (2026)

## Yeteneklere (Skills) Genel Bakış

### Temel Yetenekler (Foundational Skills)

Bu yetenekler, sonraki tüm bağlam mühendisliği çalışmaları için gerekli olan temel anlayışı kurar.

| Yetenek | Açıklama |
|---------|----------|
| [context-fundamentals](skills/context-fundamentals/) | Bağlamın ne olduğunu, neden önemli olduğunu ve ajan sistemlerinde bağlamın anatomisini anlayın |
| [context-degradation](skills/context-degradation/) | Bağlam hatası (context failure) kalıplarını tanıyın: ortada kaybolma (lost-in-middle), zehirlenme (poisoning), dikkat dağınıklığı (distraction) ve çakışma (clash) |
| [context-compression](skills/context-compression/) | Uzun süren oturumlar için sıkıştırma (compression) stratejileri tasarlayın ve değerlendirin |

### Mimari Yetenekler (Architectural Skills)

Bu yetenekler, etkili ajan sistemleri oluşturmak için mimari kalıpları (patterns) ve yapıları kapsar.

| Yetenek | Açıklama |
|---------|----------|
| [multi-agent-patterns](skills/multi-agent-patterns/) | Orkestratör (yönetici), eşler arası (peer-to-peer) ve hiyerarşik çoklu-ajan mimarilerinde ustalaşın |
| [memory-systems](skills/memory-systems/) | Kısa dönem (short-term), uzun dönem (long-term) ve grafik tabanlı hafıza mimarileri tasarlayın |
| [tool-design](skills/tool-design/) | Ajanların etkili bir şekilde kullanabileceği araçlar (tools) oluşturun |
| [filesystem-context](skills/filesystem-context/) | Dinamik bağlam keşfi, araç çıktısı boşaltma (offloading) ve plan sürekliliği (persistence) için dosya sistemlerini (filesystems) kullanın |
| [hosted-agents](skills/hosted-agents/) | **YENİ** Yalıtılmış VM'ler (sandbox), önceden oluşturulmuş imajlar, çoklu oyuncu (multiplayer) desteği ve çok istemcili arayüzler ile arka plan kodlama ajanları (background coding agents) oluşturun |

### Operasyonel Yetenekler (Operational Skills)

Bu yetenekler, ajan sistemlerinin devam eden operasyonu ve optimizasyonunu ele alır.

| Yetenek | Açıklama |
|---------|----------|
| [context-optimization](skills/context-optimization/) | Sıkıştırma (compaction), maskeleme (masking) ve önbelleğe alma (caching) stratejilerini uygulayın |
| [evaluation](skills/evaluation/) | Ajan sistemleri için değerlendirme (evaluation) çerçeveleri (frameworks) oluşturun |
| [advanced-evaluation](skills/advanced-evaluation/) | Bir-Yargıç-Olarak-Yapay-Zeka (LLM-as-a-Judge) tekniklerinde ustalaşın: doğrudan puanlama, ikili eşleştirmeli karşılaştırma (pairwise comparison), rubrik oluşturma ve önyargı azaltma (bias mitigation) |

### Geliştirme Metodolojisi (Development Methodology)

Bu yetenekler, LLM destekli projeler oluşturmak için üst düzey (meta) uygulamaları kapsar.

| Yetenek | Açıklama |
|---------|----------|
| [project-development](skills/project-development/) | Fikirden dağıtıma (deployment) kadar görev-model uyum analizi, ardışık düzen (pipeline) mimarisi ve yapılandırılmış çıktı tasarımı dâhil olmak üzere, LLM projeleri tasarlayın ve oluşturun |

### Bilişsel Mimari Yetenekler (Cognitive Architecture Skills)

Bu yetenekler, rasyonel ajan sistemleri için biçimsel (formal) bilişsel modellemeyi kapsar.

| Yetenek | Açıklama |
|---------|----------|
| [bdi-mental-states](skills/bdi-mental-states/) | **YENİ** Kararlı akıl yürütme (deliberative reasoning) ve açıklanabilirlik için resmi BDI ontoloji kalıplarını kullanarak, harici (external) RDF bağlamını ajanın zihinsel durumlarına (inançlar/beliefs, arzular/desires, niyetler/intentions) dönüştürün |

## Tasarım Felsefesi

### Kademeli Açığa Çıkarma (Progressive Disclosure)

Her yetenek, bağlam kullanımı açısından verimli olacak şekilde yapılandırılmıştır. Başlangıçta ajanlar yalnızca yetenek adlarını ve açıklamalarını yükler. Tüm içerik, ancak belirli görevler için yetenek tetiklendiğinde (aktive edildiğinde) yüklenir.

### Platform Bağımsızlığı (Platform Agnosticism)

Bu yetenekler, üreticiye özel (vendor-specific) uygulamalardan ziyade ajanlar arasında transfer edilebilir prensiplere odaklanır. Modeller Claude Code, Cursor ve yetenekleri (skills) veya özel komutları destekleyen herhangi bir ajan platformunda çalışır.

### Pratik Örneklerle Kavramsal Temel

Betikler (scripts) ve örnekler, farklı platformlarda, özellikli bağımlılık (dependency) kurulumları gerektirmeden çalışan Python sahte kodları (pseudocode) kullanılarak kavramları gösterir.

## Kullanım

### Claude Code ile Kullanım

Bu depo, Claude'un mevcut görev bağlamınıza göre otomatik olarak keşfettiği ve etkinleştirdiği bağlam mühendisliği yeteneklerini barındıran bir **Claude Code Plugin Marketplace (Eklenti Pazaryeri)**'dir.

### Kurulum

**Adım 1: Pazaryerini Ekle**

Bu depoyu eklenti (plugin) kaynağı olarak kaydetmek için Claude Code'da şu komutu çalıştırın:

```
/plugin marketplace add muratcankoylan/Agent-Skills-for-Context-Engineering
```

**Adım 2: İncele ve Yükle**

Seçenek A - Mevcut eklentileri tarama:
1. `Browse and install plugins` seçin
2. `context-engineering-marketplace` seçin
3. Bir eklenti (örneğin `context-engineering-fundamentals`, `agent-architecture`) seçin
4. `Install now` diyin

Seçenek B - Direkt komut ile yükleme:

```
/plugin install context-engineering-fundamentals@context-engineering-marketplace
/plugin install agent-architecture@context-engineering-marketplace
/plugin install agent-evaluation@context-engineering-marketplace
/plugin install agent-development@context-engineering-marketplace
/plugin install cognitive-architecture@context-engineering-marketplace
```

### Mevcut Eklentiler

| Eklenti (Plugin) | İçerdiği Yetenekler (Skills) |
|--------|-----------------|
| `context-engineering-fundamentals` | context-fundamentals, context-degradation, context-compression, context-optimization |
| `agent-architecture` | multi-agent-patterns, memory-systems, tool-design, filesystem-context, hosted-agents |
| `agent-evaluation` | evaluation, advanced-evaluation |
| `agent-development` | project-development |
| `cognitive-architecture` | bdi-mental-states |

### Yetenek Tetikleyicileri (Triggers)

| Yetenek | Ne zaman tetiklenir |
|-------|-------------|
| `context-fundamentals` | "understand context", "explain context windows", "design agent architecture" |
| `context-degradation` | "diagnose context problems", "fix lost-in-middle", "debug agent failures" |
| `context-compression` | "compress context", "summarize conversation", "reduce token usage" |
| `context-optimization` | "optimize context", "reduce token costs", "implement KV-cache" |
| `multi-agent-patterns` | "design multi-agent system", "implement supervisor pattern" |
| `memory-systems` | "implement agent memory", "build knowledge graph", "track entities" |
| `tool-design` | "design agent tools", "reduce tool complexity", "implement MCP tools" |
| `filesystem-context` | "offload context to files", "dynamic context discovery", "agent scratch pad", "file-based context" |
| `hosted-agents` | "build background agent", "create hosted coding agent", "sandboxed execution", "multiplayer agent", "Modal sandboxes" |
| `evaluation` | "evaluate agent performance", "build test framework", "measure quality" |
| `advanced-evaluation` | "implement LLM-as-judge", "compare model outputs", "mitigate bias" |
| `project-development` | "start LLM project", "design batch pipeline", "evaluate task-model fit" |
| `bdi-mental-states` | "model agent mental states", "implement BDI architecture", "transform RDF to beliefs", "build cognitive agent" |

<img width="1014" height="894" alt="Screenshot 2025-12-26 at 12 34 47 PM" src="https://github.com/user-attachments/assets/f79aaf03-fd2d-4c71-a630-7027adeb9bfe" />

### Cursor, Codex ve diğer IDE'ler İçin

Yetenek içeriklerini projenizdeki `.rules` dosyalarına veya projeye özel olarak oluşturduğunuz `Skills` klasörlerine kopyalayabilirsiniz. Yetenekler, etkili bir bağlam mühendisliği ve ajan tasarımı için ajana ihtiyaç duyduğu kuralları sağlar.

### Özel Implementasyonlar İçin

Dilerseniz herhangi bir yetenekteki prensipleri ve kalıpları (patterns) çıkarabilir ve bunları kendi ajan çerçevenizde/altyapınızda (framework) uygulayabilirsiniz. Yetenekler kasıtlı olarak platformlardan bağımsız yazılmıştır.

## Örnekler

[Örnekler (examples)](examples/) klasörü, çoklu yeteneklerin pratik sistemlerde birlikte nasıl çalıştığını gösteren eksiksiz sistem tasarımları içerir.

| Örnek | Açıklama | Kullanılan Yetenekler |
|---------|-------------|----------------|
| [digital-brain-skill](examples/digital-brain-skill/) | **YENİ** Kurucular ve yaratıcılar için kişisel işletim sistemi. 6 modül ve 4 otomasyon betiği de dâhil tam Claude Code yeteneği | context-fundamentals, context-optimization, memory-systems, tool-design, multi-agent-patterns, evaluation, project-development |
| [x-to-book-system](examples/x-to-book-system/) | X hesaplarını (Twitter) izleyen ve sentezlenmiş günlük kitaplar derleyen çoklu-ajan sistemi | multi-agent-patterns, memory-systems, context-optimization, tool-design, evaluation |
| [llm-as-judge-skills](examples/llm-as-judge-skills/) | Üretime hazır LLM değerlendirme araçları, TypeScript uygulaması ve başarıyla geçen 19 testi | advanced-evaluation, tool-design, context-fundamentals, evaluation |
| [book-sft-pipeline](examples/book-sft-pipeline/) | Herhangi bir yazarın üslubunda yazı yazması için LLM'leri eğitin. Pangram'da insan puanı olarak %70 alan Gertrude Stein vaka çalışmasını (case study) içerir (Sadece $2 toplam maliyet) | project-development, context-compression, multi-agent-patterns, evaluation |

Her bir örnek projede şunlar bulunur:
- Mimari kararların detaylarıyla yazıldığı Kapsamlı PRD (Ürün Gereksinim Belgesi)
- Hangi mimari karar için hangi yeteneklerin kullanıldığını gösteren eşleştirme
- Uygulama rehberi

### Digital Brain Skill (Dijital Beyin) Örneği

[digital-brain-skill](examples/digital-brain-skill/) örneği, kapsamlı yetenek uygulamasını (skills application) gösteren tam anlamıyla kişisel bir işletim sistemidir:

- **Kademeli Açığa Çıkarma (Progressive Disclosure)**: 3 seviyeli yükleme (SKILL.md → MODULE.md → data dosyaları)
- **Modül İzolasyonu**: 6 bağımsız modül (identity, content, knowledge, network, operations, agents)
- **Sadece-Eklenebilir (Append-Only) Hafıza**: Ajan dostu ve kolay okunabilirlik için satır başına tanımlanan şemalara (schema-first) sahip JSONL dosyaları
- **Otomasyon Betikleri (Automation Scripts)**: Birleştirilmiş 4 araç (weekly_review, content_ideas, stale_contacts, idea_to_draft)

Belirlenen mimari kararları, belirli yetenek kurallarıyla izleyen detaylı takip dokümanına [HOW-SKILLS-BUILT-THIS.md](examples/digital-brain-skill/HOW-SKILLS-BUILT-THIS.md) dosyasından ulaşılabilir.

### LLM-as-Judge Skills (Bir-Yargıç-Olarak-LLM Yetenekleri) Örneği

[llm-as-judge-skills](examples/llm-as-judge-skills/) örneği, TypeScript ile yazılmış tam bir implementasyondur:

- **Doğrudan Puanlama (Direct Scoring)**: Rubrik (taslak cevap destekleyici) ağırlıklı kriterlerle geri dönüşleri değerlendirin
- **İkili Karşılaştırma (Pairwise Comparison)**: Pozisyon önyargısı (bias) azaltma yöntemiyle iki farklı modeli/cevabı puanlayın
- **Rubrik Oluşturma**: Belirli standartlarda alanlara özgü (domain-specific) değerlendirmeler yapın
- **EvaluatorAgent (Değerlendirici Ajan)**: Karakterli ve üst düzey yetenekleri olan tam performans yargıçlık yeteneği barındıran değerlendirici ajan

### Kitap (SFT) Eğitim ve Veri İşleme (Pipeline) Örneği

[book-sft-pipeline](examples/book-sft-pipeline/) örneği ufak modelleri (8B) kullanarak yazarları üsluplarıyla taklit edebilmelerini sağlayan bir örnektir:

- **Akıllı Bölünme Teorisi (Intelligent Segmentation)**: Örtüşen eğitim kelime kümeleri oluşturabilme
- **Farklı İstekler Kullanımı (Prompt Diversity)**: 15+ ezberi önleyici öğrenim ve metin kalıbı taklidi istemleri 
- **Tinker Entegrasyonu**: Tamamiyle LoRA optimizasyonlarına uygun ve yalnızca $2'a eğitim workflowu
- **Onaylama Mekanizması Uygulamaları**: Modelin salt içeriği mi ezberlediğini, yoksa stil transferini (style transfer) başarıyla gerçekleştirip gerçekleştirmediğini modern test senaryolarıyla ispat eden değerlendirme süreci

Bağlam mühendisliği yetenekleri ile entegrasyonu: project-development, context-compression, multi-agent-patterns, evaluation.

## Yıldız Geçmişi (Star History)
<img width="3664" height="2648" alt="star-history-2026224" src="https://github.com/user-attachments/assets/b3bdbf23-4b6a-4774-ae85-42ef4d9b2d79" />

## Dizin Yapısı (Structure)

Her Yetenek (Skill), spesifikasyonlarına göre belirlenen kalıpta oluşturulur:

```text
skill-name/
├── SKILL.md              # ZORUNLU: talimatlar + meta veri (frontmatter)
├── scripts/              # OPSİYONEL: kavramları gösteren çalıştırılabilir scriptler
└── references/           # OPSİYONEL: ek dokümantasyon ve dış bağlantılar
```

Resmi ve daha detaylı Yetenek dosyası yapısını (skill structure) görmek için [template](template/) klasörünü inceleyebilirsiniz.

## Katılım Sağlamak (Contributing)

Bu depo, Ajan Yetenekleri (Agent Skills) için açık geliştirme modeli ile çalışmaktadır. Daha geniş bir ekosistemden destek almaya ve katkılara açıktır. Katkı sağlamadan önce lütfen şunlara dikkat edin:

1. Doğru "skill template" kalıbını ve dosya/klasör yapılarını kullanın
2. Oldukça temiz ve yapılabilir/tekrar edilebilir bilgi yönergeleri yazın
3. Olabildiğince pratikte kullanılabilir çalışan örnekler verin (scripts, references)
4. Dezavantajları (trade-offs) veya olası sorun risklerini dokümantasyonda belirtin
5. Yüksek performans garantisi için yarattığınız SKILL.md doyasını 500 satırın altında tutun

Görüşleriniz veya sorularınız için [Muratcan Koylan](https://x.com/koylanai) ile iletişime geçebilirsiniz.

## Lisans

MIT Lisansı - Daha fazla detay için LICENSE dosyasını inceleyebilirsiniz.

## Referanslar
Bu yeteneklerin barındırdığı kurallar, yapay zeka alanında kendini kanıtlamış geliştiricilerin/laboratuvarların gerçek üretim tecrübelerine / araştırma makalelerine dayandırılmaktadır. Çoğu Yetenek yapısının içinde o konuda kullanılan ilgili araştırmaların makalelerine ve örnek kullanım alanlarına erişebilirsiniz.
