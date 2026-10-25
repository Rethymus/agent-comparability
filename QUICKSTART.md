# Quickstart (30 seconds, zero network/credentials/Docker)

```bash
pip install -e .            # core has zero dependencies
python -c "
from agent_comparability import adjudicate
cdr = adjudicate({'id':'demo','records':[
  {'task_id':'t','harness':'h1','model':'m','reward':1.0,'reward_status':'verified'},
  {'task_id':'t','harness':'h2','model':'m','reward':0.0,'reward_status':'unresolved_zero'}]},
  'score_compare')
print(cdr.admissibility, cdr.supported_claims)"
# → PARTIAL ['per_status_stratified_rate(verified_zero/unresolved_zero 分列)']
```

Full suite: `pip install -e .[suite] && python conformance/run_suite.py`
Adapters: `pip install -e .[inspect]` / `.[pydantic]`, then run files in `adapters/`.
