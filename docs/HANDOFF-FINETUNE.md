# HANDOFF: OpenAI Fine-Tuned Model — TimeVision

**Datum:** 2026-02-13 | **Verze:** v1.29.0

---

## Stav

Fine-tuning **DOKONČEN**. Model nasazen v produkci.

| Co | Hodnota |
|----|---------|
| Model | `ft:gpt-4o-2024-08-06:kovo-rybka:gestima-v1:D8oakyjH` |
| Base model | `gpt-4o-2024-08-06` |
| Trénovací data | 55 příkladů, `gestima_ft_55_samples.jsonl` (34.8 MB) |
| Training loss | 0.037 (step 165) |
| Training accuracy | ~97% |
| Cena tréninku | $6.42 |
| OpenAI File ID | `file-Fw2WQDA1rRGPcrRCjBuLQq` |
| OpenAI Job ID | `ftjob-m1pQY7gnSuzTUHC7aF5hr5Q2` |

---

## Architektura

```
PDF → 300 DPI PNG → Fine-tuned GPT-4o vision → JSON odhad → DB
                     ↑
                     Kompaktní prompt (bez tabulek — naučené z tréninku)
```

**Prompt switching:** Automatické podle `is_fine_tuned_model()`:
- Fine-tuned → `OPENAI_FT_SYSTEM` + `build_openai_ft_prompt()` (~200 tokenů)
- Base → `OPENAI_VISION_SYSTEM` + `build_openai_vision_prompt()` (~2000+ tokenů)

**Provider tracking:** `ai_provider` v DB:
- `"openai"` = base model odhady
- `"openai_ft"` = fine-tuned model odhady

---

## Klíčové soubory

| Soubor | Popis |
|--------|-------|
| `app/services/openai_vision_service.py` | OPENAI_MODEL konstanta, PDF render, API call, prompt switching |
| `app/services/openai_vision_prompts.py` | Kompaktní FT prompt + plný base prompt |
| `app/routers/time_vision_router.py` | `/process-openai` (SSE), `/model-info`, `/export-training` |
| `gestima_ft_55_samples.jsonl` | Trénovací data (55 vzorků, 34.8 MB) |
| `frontend/src/stores/timeVision.ts` | Store: modelInfo, processFileOpenAI() |
| `frontend/src/components/modules/timevision/TimeVisionOpenAIPanel.vue` | UI s model indikátorem |

---

## Swap modelu

Pro návrat na base model nebo nasazení v2:

```python
# app/services/openai_vision_service.py, řádek 31
OPENAI_MODEL = "gpt-4o"                    # base model
OPENAI_MODEL = "ft:gpt-4o-...:gestima-v1"  # fine-tuned v1
OPENAI_MODEL = "ft:gpt-4o-...:gestima-v2"  # fine-tuned v2 (budoucí)
```

Restartovat server po změně.

---

## Monitoring

```bash
export $(grep OPENAI_API_KEY .env | xargs)

# Stav jobu
openai api fine_tuning.jobs.retrieve -i ftjob-m1pQY7gnSuzTUHC7aF5hr5Q2

# Nový fine-tuning (v2)
openai api fine_tuning.jobs.create -m gpt-4o-2024-08-06 -F file-Fw2WQDA1rRGPcrRCjBuLQq -s gestima-v2
```

---

## Známé problémy

1. **4 výkresy blokované safety filtrem**: 10138363, JR 811198, PDM-280739, JR 810952
2. **55 příkladů je minimum** — ideálně 200+ pro vision fine-tuning
3. **A/B test neproveden** — zatím nemáme porovnání base vs fine-tuned na stejných výkresech
4. **Overfit riziko** — training accuracy 97% ale bez validation setu

---

## Budoucí kroky

1. **A/B test** — porovnat base vs fine-tuned na stejných výkresech
2. **Více dat** — rozšířit dataset na 100+ výkresů, iterovat v2
3. **Prompt optimalizace** — experimentovat s ještě kratším FT promptem
4. **Validation set** — při v2 oddělit 10% dat pro validaci
