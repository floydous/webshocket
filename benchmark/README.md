# Webshocket Benchmarks

This directory contains the performance benchmark for the webshocket framework.

## Running the Benchmark

```bash
uv run benchmark/benchmark.py
```

This runs a full test matrix comparing the standard `asyncio` event loop against
an optimized loop (`winloop` on Windows, `uvloop` on Linux/macOS). Results are
printed as tables and exported as a bar chart to `benchmark_results.png`.

## Choosing the Right Event Loop

No single event loop is universally faster. The best choice depends on your
workload profile.

### Use default `asyncio` when:

- Your app sends **small, frequent messages** (chat, commands, telemetry, game ticks)
- Your RPC handlers process **many short requests** concurrently
- Your streaming RPCs produce **many chunks per stream** (100+)
- You want **predictable, stable throughput** regardless of payload shape

asyncio's pure-Python scheduler has very low per-task overhead. In benchmarks,
it sustains ~47,000 RPCs/s with 64-byte payloads, and its streaming throughput
stays rock-solid at ~280-295 MB/s regardless of stream length.

### Use `winloop` / `uvloop` when:

- Your app transfers **large payloads** (file sync, media, bulk data)
- Your streaming RPCs produce **few, large chunks** per stream
- Your workload is **I/O-bound**, not scheduling-bound

These loops wrap libuv (a C library) which excels at buffer management and write
coalescing for bulk transfers. In benchmarks, winloop reaches ~750 MB/s streaming
throughput with short streams and ~8,000 RPCs/s with 64KB payloads — roughly
2-3x faster than asyncio for I/O-heavy work.

### Why the difference?

Every RPC round-trip and every `yield` in a streaming RPC is a full pass through
the event loop scheduler. With small payloads, the bottleneck is **scheduling
overhead** (coroutine switching), not I/O. asyncio's scheduler is implemented in
pure Python with minimal per-switch cost. winloop/uvloop cross a Python-to-C FFI
boundary on every scheduling decision, which adds a small constant overhead that
accumulates fast when each unit of work is tiny.

With large payloads, the bottleneck shifts to **actual I/O**: buffer allocation,
write batching, and syscall count. libuv's internal write queue coalesces
multiple writes into fewer kernel calls, and its buffer pooling reduces
allocation pressure. The FFI overhead is amortized over the large data volume.

### Quick reference

| Workload | Recommended Loop | Why |
|---|---|---|
| Chat / commands / telemetry | `asyncio` | Low per-task scheduling cost |
| High-frequency small RPCs | `asyncio` | ~2x faster at < 4KB payloads |
| File transfer / media streaming | `winloop` / `uvloop` | ~2-3x faster bulk I/O |
| Long streaming RPCs (100+ chunks) | `asyncio` | Stable throughput, no degradation |
| Short streaming RPCs (< 32 chunks) | `winloop` / `uvloop` | Peak throughput ~750 MB/s |
| Mixed / unknown workload | `asyncio` | Most predictable performance |

### Installing an optimized loop

```bash
# Windows
pip install winloop

# Linux / macOS
pip install uvloop
```

Then activate it before starting your server:

```python
import sys

if sys.platform == "win32":
    import winloop
    winloop.install()
else:
    import uvloop
    uvloop.install()
```
