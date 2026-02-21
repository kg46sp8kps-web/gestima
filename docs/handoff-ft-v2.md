# Handoff: FT v2 — Technology Builder Fine-Tuning

## Stav k 2026-02-19

### Co je hotové
- **1,017 training samples** vygenerováno a uploadováno na OpenAI (`file-6JZtdHf6WQw8fJkggxyD2S`)
- **FT job na GPT-4.1** vytvořen: `ftjob-3FJpSmVWYPYreT9e7FgJO0tD`
- **JSONL:** `data/ft_v2_training.jsonl` (955 MB, 1,017 samples s výkresy jako base64 PNG)
- **ADR-047** aktualizován na finální stav
- **System prompt** opraven: material (ne material_norm), NLX (2 vřetena), NZX (samostatný stroj), strojní čas (celkový na stroji), VS20 (většinou)

### BLOKUJÍCÍ PROBLÉM
FT job pravděpodobně selže na **billing quota** — gpt-4o job selhal se zprávou:
```
exceeded_quota: Cost of job $126.09, Quota remaining: $3.65
```
→ **Uživatel musí navýšit billing limit** na https://platform.openai.com/settings/organization/billing (potřeba ~$150+)

### Co dělat dál

1. **Zkontrolovat FT job status:**
```python
from dotenv import load_dotenv
import os
load_dotenv()
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
job = client.fine_tuning.jobs.retrieve('ftjob-3FJpSmVWYPYreT9e7FgJO0tD')
print(f'Status: {job.status}')
print(f'Model: {job.fine_tuned_model}')
print(f'Error: {job.error}')
```

2. **Pokud failed na kvótu** — po navýšení limitu spustit znovu:
```python
job = client.fine_tuning.jobs.create(
    training_file='file-6JZtdHf6WQw8fJkggxyD2S',
    model='gpt-4.1-2025-04-14',
    suffix='gestima-v2',
    hyperparameters={'n_epochs': 2, 'batch_size': 2, 'learning_rate_multiplier': 1.0}
)
```

3. **Po úspěšném FT** — aktualizovat `CLAUDE.local.md`:
```
- ai_provider: `openai_ft` (fine-tuned) nebo `openai` (base)
- Fine-tuned model: ft:gpt-4.1-2025-04-14:kovo-rybka:gestima-v2:XXXXX
```

4. **Testování FT modelu:**
```bash
python scripts/test_ft_v2_prompt.py --model ft:gpt-4.1-2025-04-14:kovo-rybka:gestima-v2:XXXXX
```
- Porovnat MAPE s baseline (33%)
- Cíl: MAPE < 15%

5. **Integrace do Technology Builder:**
- `POST /api/technology/generate` — přepojit na nový FT model
- Parsování `material` pole (už ne `material_norm`) přes převodní tabulku material_norms
- Test: vygenerovat technologii pro díl, porovnat s produkčními daty

### Klíčové soubory
| Soubor | Účel |
|--------|------|
| `scripts/generate_ft_v2_data.py` | GT výpočet + JSONL generátor |
| `data/ft_v2_training.jsonl` | Training data (955 MB) |
| `data/ft_v2_training_meta.json` | Metadata |
| `docs/ADR/047-ft-v2-technology-builder.md` | Kompletní dokumentace |
| `scripts/test_ft_v2_prompt.py` | Test/benchmark script |

### Klíčová rozhodnutí z této session
1. **PDF kvalita:** 77% skenovaných PDF — nevadí, Vision FT vidí obrázek, ne text
2. **CV filtrování:** Nefiltrujeme. Trimmed mean 10% je dostatečně robustní. Víc dat > čistší data.
3. **NZX 2000:** Samostatný stroj (ne mapovaný na NLX). 33 samples v datasetu.
4. **`material` místo `material_norm`:** Model vrací materiál jak je na výkresu. Technology Builder parsuje.
5. **Strojní čas:** Celkový čas na stroji per kus (řez + přejezdy + výměny + upínání). NE setup stroje.
6. **GPT-4.1 místo GPT-4o:** Novější, lepší model. Podporuje vision FT.
