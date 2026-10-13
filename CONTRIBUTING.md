# Contributing

Useful changes preserve the distinction between nominal samples, interval evidence and physical validation. Include a concrete request and explain the expected behavior. Keep an ambiguous or budget-limited check unresolved, and retain strict workload and input limits.

```sh
python -m pip install -r requirements.lock .
python -m unittest discover -s tests -v
node --test tests/*.test.mjs
python scripts/installed_check.py
```

Potential contributions include independent interval controls, better fitting seeds, accessible canvas alternatives, CAD import validation and evidence-backed topology extensions. A new topology or body model needs matching clearance and export geometry. Do not submit generated performance, physical-safety or novelty claims without a reproducible comparison.

Clearly identify AI assistance where material and take responsibility for the actual change. Contributors must understand and be able to explain the calculations they submit.
