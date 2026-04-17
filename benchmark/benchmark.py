"""Webshocket Ultimate Benchmark Suite

Produces four focused bar charts, each isolating a single variable while
comparing the default asyncio event loop against an optimized loop
(winloop on Windows, uvloop on Linux/macOS).

Graphs:
    1. RPC Throughput  vs  Payload Size
    2. RPC Latency     vs  Payload Size
    3. Streaming Data Throughput  vs  Chunk Size
    4. Streaming Data Throughput  vs  Chunks per Stream
"""

import sys
import asyncio
import time
import logging
import os

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

import webshocket
from webshocket.rpc import rpc_method

logging.getLogger("webshocket").setLevel(logging.ERROR)
logging.getLogger("picows").setLevel(logging.ERROR)

console = Console()

CONCURRENCY = 50
DURATION = 5  # seconds per test


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------
class BenchHandler(webshocket.WebSocketHandler):
    @rpc_method()
    async def echo(self, connection: webshocket.ClientConnection, data: str):
        return data

    @rpc_method()
    async def stream(self, connection: webshocket.ClientConnection, size: int, count: int):
        chunk = "x" * size
        for _ in range(count):
            yield chunk


# ---------------------------------------------------------------------------
# Benchmark runners
# ---------------------------------------------------------------------------
async def bench_rpc(payload_size: int, host: str, port: int, loop_name: str) -> dict | None:
    """Measure RPC throughput and latency for a given payload size."""
    try:
        async with webshocket.WebSocketClient(f"ws://{host}:{port}") as client:
            payload = "a" * payload_size
            for _ in range(50):
                await client.send_rpc("echo", "warmup")

            count = 0
            start = time.perf_counter()
            deadline = start + DURATION

            async def worker():
                nonlocal count
                while time.perf_counter() < deadline:
                    try:
                        await client.send_rpc("echo", payload)
                        count += 1
                    except Exception:
                        break

            await asyncio.gather(*[asyncio.create_task(worker()) for _ in range(CONCURRENCY)])

            elapsed = time.perf_counter() - start
            return {
                "loop": loop_name,
                "payload": format_size(payload_size),
                "payload_bytes": payload_size,
                "throughput": count / elapsed,
                "latency_ms": (elapsed * CONCURRENCY / count) * 1000 if count else 0,
            }
    except Exception as e:
        console.print(f"[red]RPC error: {e}[/red]")
        return None


async def bench_stream(chunk_size: int, chunks_per_stream: int, host: str, port: int, loop_name: str) -> dict | None:
    """Measure streaming throughput for a given chunk configuration."""
    try:
        async with webshocket.WebSocketClient(f"ws://{host}:{port}") as client:
            for _ in range(3):
                async for _ in client.stream_rpc("stream", chunk_size, chunks_per_stream):
                    pass

            streams = 0
            chunks = 0
            start = time.perf_counter()
            deadline = start + DURATION

            async def consume_one_stream():
                received = 0
                async for _ in client.stream_rpc("stream", chunk_size, chunks_per_stream):
                    received += 1
                return received

            async def worker():
                nonlocal streams, chunks
                while time.perf_counter() < deadline:
                    try:
                        received = await asyncio.wait_for(consume_one_stream(), timeout=10.0)
                        chunks += received
                        streams += 1
                    except (TimeoutError, Exception):
                        break

            await asyncio.gather(*[asyncio.create_task(worker()) for _ in range(CONCURRENCY)])

            elapsed = time.perf_counter() - start
            total_mb = (chunks * chunk_size) / (1024 * 1024)
            return {
                "loop": loop_name,
                "chunk_size": format_size(chunk_size),
                "chunk_bytes": chunk_size,
                "chunks_per_stream": chunks_per_stream,
                "throughput_mb": total_mb / elapsed if elapsed else 0,
                "streams_s": streams / elapsed if elapsed else 0,
            }
    except Exception as e:
        console.print(f"[red]Stream error: {e}[/red]")
        return None


# ---------------------------------------------------------------------------
# Suite runner
# ---------------------------------------------------------------------------
_port_counter = 5010


async def run_suite(loop_name: str) -> tuple[list[dict], list[dict], list[dict]]:
    global _port_counter
    host, port = "127.0.0.1", _port_counter
    _port_counter += 1

    server = webshocket.WebSocketServer(host, port, clientHandler=BenchHandler)
    await server.start()

    # --- 1) RPC: vary payload size ---
    rpc_results = []
    payload_sizes = [64, 256, 1024, 4096, 16384, 65536, 262144]

    console.print(f"  [cyan]RPC vs Payload Size ({loop_name})[/cyan]")
    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as p:
        t = p.add_task("Running...", total=len(payload_sizes))
        for size in payload_sizes:
            r = await bench_rpc(size, host, port, loop_name)
            if r:
                rpc_results.append(r)
            p.advance(t)

    # --- 2) Streaming: vary chunk size (fixed 32 chunks/stream) ---
    stream_by_chunk = []
    chunk_sizes = [1024, 4096, 16384, 32768, 65536]

    console.print(f"  [cyan]Streaming vs Chunk Size ({loop_name})[/cyan]")
    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as p:
        t = p.add_task("Running...", total=len(chunk_sizes))
        for size in chunk_sizes:
            r = await bench_stream(size, 32, host, port, loop_name)
            if r:
                stream_by_chunk.append(r)
            p.advance(t)

    # --- 3) Streaming: vary chunks/stream (fixed 16KB chunk) ---
    stream_by_count = []
    chunk_counts = [8, 16, 32, 64, 128, 256]

    console.print(f"  [cyan]Streaming vs Chunks/Stream ({loop_name})[/cyan]")
    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as p:
        t = p.add_task("Running...", total=len(chunk_counts))
        for count in chunk_counts:
            r = await bench_stream(16384, count, host, port, loop_name)
            if r:
                stream_by_count.append(r)
            p.advance(t)

    await server.close()
    return rpc_results, stream_by_chunk, stream_by_count


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def format_size(b: int) -> str:
    if b >= 1024 * 1024:
        return f"{b / (1024*1024):.0f} MB"
    if b >= 1024:
        return f"{b / 1024:.0f} KB"
    return f"{b} B"


def print_tables(rpc: list[dict], by_chunk: list[dict], by_count: list[dict]):
    t1 = Table(title=f"RPC Throughput vs Payload Size (concurrency={CONCURRENCY})", header_style="bold magenta")
    t1.add_column("Loop")
    t1.add_column("Payload")
    t1.add_column("Throughput (RPCs/s)", justify="right")
    t1.add_column("Latency (ms)", justify="right")
    for r in rpc:
        t1.add_row(r["loop"], r["payload"], f"{r['throughput']:,.0f}", f"{r['latency_ms']:.2f}")
    console.print("\n")
    console.print(t1)

    t2 = Table(title=f"Streaming vs Chunk Size (32 chunks/stream, concurrency={CONCURRENCY})", header_style="bold green")
    t2.add_column("Loop")
    t2.add_column("Chunk Size")
    t2.add_column("Data Throughput (MB/s)", justify="right")
    for r in by_chunk:
        t2.add_row(r["loop"], r["chunk_size"], f"{r['throughput_mb']:.1f}")
    console.print("\n")
    console.print(t2)

    t3 = Table(title=f"Streaming vs Stream Length (16 KB chunks, concurrency={CONCURRENCY})", header_style="bold blue")
    t3.add_column("Loop")
    t3.add_column("Chunks/Stream")
    t3.add_column("Data Throughput (MB/s)", justify="right")
    for r in by_count:
        t3.add_row(r["loop"], str(r["chunks_per_stream"]), f"{r['throughput_mb']:.1f}")
    console.print("\n")
    console.print(t3)


def plot_results(rpc: list[dict], by_chunk: list[dict], by_count: list[dict]):
    sns.set_theme(style="whitegrid")
    palette = sns.color_palette("muted", n_colors=2)

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle(
        f"Webshocket v0.5.2 Performance Benchmark  (concurrency={CONCURRENCY}, {DURATION}s/test)",
        fontsize=15, fontweight="bold",
    )

    df_rpc = pd.DataFrame(rpc)

    # Sort payload by actual size for correct x-axis ordering
    payload_order = df_rpc.sort_values("payload_bytes")["payload"].unique().tolist()

    # --- 1) RPC Throughput ---
    ax = axes[0][0]
    sns.barplot(data=df_rpc, x="payload", y="throughput", hue="loop", order=payload_order, palette=palette, ax=ax)
    ax.set_title("RPC Throughput vs Payload Size")
    ax.set_xlabel("Payload Size")
    ax.set_ylabel("Throughput (RPCs/s)")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(title="Event Loop")

    # --- 2) RPC Latency ---
    ax = axes[0][1]
    sns.barplot(data=df_rpc, x="payload", y="latency_ms", hue="loop", order=payload_order, palette=palette, ax=ax)
    ax.set_title("RPC Latency vs Payload Size")
    ax.set_xlabel("Payload Size")
    ax.set_ylabel("Avg Latency (ms)")
    ax.legend(title="Event Loop")

    # --- 3) Streaming vs Chunk Size ---
    df_chunk = pd.DataFrame(by_chunk)
    chunk_order = df_chunk.sort_values("chunk_bytes")["chunk_size"].unique().tolist()

    ax = axes[1][0]
    sns.barplot(data=df_chunk, x="chunk_size", y="throughput_mb", hue="loop", order=chunk_order, palette=palette, ax=ax)
    ax.set_title("Streaming Throughput vs Chunk Size (32 chunks/stream)")
    ax.set_xlabel("Chunk Size")
    ax.set_ylabel("Data Throughput (MB/s)")
    ax.legend(title="Event Loop")

    # --- 4) Streaming vs Chunks/Stream ---
    df_count = pd.DataFrame(by_count)

    ax = axes[1][1]
    sns.barplot(data=df_count, x="chunks_per_stream", y="throughput_mb", hue="loop", palette=palette, ax=ax)
    ax.set_title("Streaming Throughput vs Stream Length (16 KB chunks)")
    ax.set_xlabel("Chunks per Stream")
    ax.set_ylabel("Data Throughput (MB/s)")
    ax.legend(title="Event Loop")

    plt.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "benchmark_results.png")
    plt.savefig(out, dpi=300)
    console.print(f"\n[bold green]Graph saved to {out}[/bold green]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    console.print(f"\n[bold magenta]--- Webshocket Ultimate Benchmark ---[/bold magenta]")
    console.print(f"Concurrency: {CONCURRENCY}  |  Duration: {DURATION}s per test\n")

    all_rpc, all_chunk, all_count = [], [], []

    # Pass 1: standard asyncio
    console.print("[bold]Pass 1: asyncio[/bold]")
    rpc, chunk, count = asyncio.run(run_suite("asyncio"))
    all_rpc.extend(rpc)
    all_chunk.extend(chunk)
    all_count.extend(count)

    # Pass 2: optimized loop
    loop_name = None
    try:
        if sys.platform == "win32":
            import winloop
            winloop.install()
            loop_name = "winloop"
        else:
            import uvloop
            uvloop.install()
            loop_name = "uvloop"
    except ImportError:
        console.print("\n[yellow]Optimized loop not installed -- skipping second pass.[/yellow]")

    if loop_name:
        console.print(f"\n[bold]Pass 2: {loop_name}[/bold]")
        rpc, chunk, count = asyncio.run(run_suite(loop_name))
        all_rpc.extend(rpc)
        all_chunk.extend(chunk)
        all_count.extend(count)

    print_tables(all_rpc, all_chunk, all_count)
    plot_results(all_rpc, all_chunk, all_count)


if __name__ == "__main__":
    main()
