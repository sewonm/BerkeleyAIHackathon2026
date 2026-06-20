# Quick Start: Advanced Compression Agent

## ⚡ **Run the Demo**

```bash
python -m app.compression.demo_advanced_compression
```

## ✅ **Run the Tests**

```bash
pytest tests/test_advanced_compression.py -v
```

**Result:** 10/10 tests passing

## 📊 **What It Does**

```
Raw Evidence (1000+ tokens)
    ↓
Claim Extraction (Claude or heuristic)
    ↓
Evidence Graph (nodes + edges)
    ↓
Consensus Clustering (merge similar claims)
    ↓
Information-Value Scoring (rank by decision value)
    ↓
Compressed Context (~600 tokens)
```

## 🎯 **Key Features**

- ✅ **Graph-consensus compression** (not just token-based)
- ✅ **Structured claim extraction** with YES/NO/NEUTRAL direction
- ✅ **Evidence graph** with supports/opposes/conflicts relationships
- ✅ **Consensus clustering** with entropy measurement
- ✅ **Information-value scoring** (8-factor formula)
- ✅ **Contradiction detection**
- ✅ **Missing information identification**
- ✅ **Claude integration** with graceful fallback
- ✅ **Works offline** (no Redis or API keys required)
- ✅ **Deployable to Agentverse** as standalone uAgent

## 📁 **Key Files**

- `app/compression/schemas_advanced.py` - Pydantic models
- `app/compression/extractors.py` - Claim extractors (Claude + heuristic)
- `app/compression/graph_builder.py` - Graph construction & clustering
- `app/compression/information_value.py` - Info-value scorer
- `app/compression/advanced_compressor.py` - Main pipeline
- `app/compression/demo_advanced_compression.py` - Local demo
- `uagents_deploy/compression_agent_advanced.py` - uAgent wrapper
- `tests/test_advanced_compression.py` - 10 tests (all passing)
- `app/compression/README_ADVANCED.md` - Full documentation
- `COMPRESSION_AGENT_SUMMARY.md` - Implementation summary

## 🚀 **Deploy to Agentverse**

```bash
cd uagents_deploy
python compression_agent_advanced.py
```

Then follow [AGENTVERSE_DEPLOYMENT.md](AGENTVERSE_DEPLOYMENT.md)

## 📖 **Full Documentation**

See [COMPRESSION_AGENT_SUMMARY.md](COMPRESSION_AGENT_SUMMARY.md)
