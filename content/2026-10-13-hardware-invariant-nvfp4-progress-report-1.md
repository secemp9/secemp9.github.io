---
title: 'Towards a hardware-invariant NVFP4 for GPUs without FP4: progress report 1'
date: 2026-10-13T15:59+02:00
status: hidden
slug: hardware-invariant-nvfp4-progress-report-1
tags: []
cssclasses:
- blog-post
summary: 4-bit weights on the INT8 tensor cores every NVIDIA GPU from Ampere to Blackwell has, how the format got here, and where the evaluation is right now.
---
*Progress report 1, with numbers as of 5 October 2026. The whole-model evaluation on the 3090 is still running, so there's no final quality or speed table here yet, and the code isn't public yet either. Both come with report 2, once the evals are done, and after that the plan is a paper. Some of this will change when the run finishes.*

NVFP4 is NVIDIA's 4-bit floating-point format. Each weight is an E2M1 float that tops out at 6, every block of 16 weights shares an E4M3 scale, and one FP32 scale covers the whole tensor, which works out to 4.5 bits per weight. Blackwell's tensor cores [run it natively](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/).

![NVFP4 block layout](images/hint4-progress-report-1/fig01_nvfp4_layout.png)
*The NVFP4 layout.*

I wanted it on a 3090. Sadly, I learned at the time that Ampere doesn't have native FP4. The FP4 forms of [`mma`](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#warp-level-matrix-instructions-mma) need sm_120a, datacenter Blackwell does FP4 through a different instruction family, and nothing older has it at all.

NVFP4 checkpoints do still run on Ampere, weight-only. The kernel unpacks the 4-bit weights to 16-bit floats in registers and does the multiply on the half-precision tensor cores, which is what NVFP4A16 means, NVFP4 weights with 16-bit activations. The weights stay small in memory, but every multiply has to wait for a decode first.

My gut said that had to be slower than a format the tensor cores understand natively, though I hadn't measured anything yet.

## Integer instead

Ampere does have integer tensor cores, INT8 and even INT4. My first idea, before I'd read the PTX docs properly, was a straight swap: INT4 wherever NVFP4 has FP4, INT8 wherever FP8 would go, keep the block scales, and run the whole thing on integer `mma`. I was betting that the integer part of the tensor core is the part every generation keeps.

Then I found out the numerics side already had a paper. [Chen et al.](https://arxiv.org/abs/2510.25602) define NVINT4, which is NVFP4's exact structure with the E2M1 grid swapped for symmetric INT4, and their abstract says:

> for 4-bit formats, FP (e.g., MXFP4, NVFP4) often holds an accuracy advantage, though we show that NVINT4 can surpass NVFP4 when outlier-mitigation techniques like Hadamard rotation are applied.

Without rotation, NVINT4 lost to NVFP4 on all twelve models they tested, and with random Hadamard rotation it won all twelve. Their code does fake quantization, and the hardware half of the paper is a gate-level area and energy model of multiply units nobody has built yet. The numerics question was answered, with a rotation attached, but the hardware argument is about future accelerators, which doesn't do much for me on a 3090. I'm also not a fan of the name, since NVINT4 reads like something NVIDIA ships and it's really a format from a paper.

![NVINT4 vs NVFP4 wins out of 12 models](images/hint4-progress-report-1/fig02_nvint4_wins.png)
*From Table 3 of Chen et al.*

Do I emulate, and pay for a decode before every multiply, or go integer and trust that the instructions I need exist on every card I care about?

Integer also fit the other thing I wanted, PTX that lowers to the same native instruction on every target. One kernel family, no `if ampere / elif ada / elif hopper` branches, and no per-generation copies slowly drifting apart. If that works it should be fast, and it's a lot less to maintain. I started calling that hardware-invariant, which is where the H in HINT4 comes from.

## Which integer mma?

The PTX docs have both integer forms, the 4-bit `mma` and the 8-bit one, and [both are legal on anything from sm_80 up](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#warp-level-matrix-instructions-mma). Ampere runs both natively, so the first kernel used the 4-bit one, and on Ampere the SASS showed the real 4-bit instruction. My first README even put it in the name, Hardware-Invariant Native INT4 Microscaling, and claimed native INT4 tensor cores on Ampere and everything newer, Hopper included. Then I compiled the same kernel for sm_90 and looked at the SASS.

```
                     sm_80 / sm_86 / sm_89     sm_90
mma m16n8k32 .s4     IMMA.16832.S4.S4  x1      IMMA.16816.S8.S8  x2
mma m16n8k64 .s4     IMMA.16864.S4.S4  x1      IMMA.16832.S8.S8  x2
```

Where did the 4-bit instruction go?

Hopper doesn't have one. In these kernels ptxas splits each 4-bit MMA into two 8-bit MMAs at half the K, and adds shifts and LOP3s in front to sign-extend the nibbles. It still runs on the tensor cores and it still gets the right answer, it's just not the instruction I wrote, and the extra work costs throughput. NVIDIA's own [table of tensor core input types](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html#compute-capabilities-table-tensor-core-data-types-per-compute-capability) says the same thing. INT4 is there through compute capability 8.9 and gone from Hopper on, while INT8 is there on every row, every Blackwell part included.

![Excerpt of NVIDIA's Table 33](images/hint4-progress-report-1/fig03_table33.png)
*Excerpt from Table 33 of NVIDIA's CUDA programming guide.*

Everything builds on the 8-bit `mma` instead, `mma.sync.aligned.m16n8k32` with signed bytes, which is native on every target I compile for, sm_80 through sm_120. The weights stay 4-bit in memory and get widened to signed bytes in registers right before the multiply, which is more or less what ptxas was doing on Hopper behind my back anyway. I'd rather do it on purpose, in the source, where the instruction stream is the same on every target.

Nine days after the first commit, the README title went from Hardware-Invariant Native INT4 Microscaling to Hardware-Invariant Native Integer-Tensor-Core 4-bit Microscaling, which is a mouthful, but it stopped promising 4-bit math.

![The old 4-bit kernels compiled per target](images/hint4-progress-report-1/fig04_s4_lowering.png)
*The old 4-bit kernels compiled per target. On sm_90 each of the 19 needed between 30 and 95 extra LOP3s.*

I'd mostly taken NVIDIA's table at its word after that. This month I finally read the whole PTX ISA, the 9.3 manual and the 8.7 one that shipped with CUDA 12.8, to see whether anything newer brings 4-bit integer math back.

Nothing does. Hopper's `wgmma` takes 8-bit integers plus a 1-bit mode, and no 4-bit. Blackwell's `tcgen05` has exactly one integer kind, `i8`, and even that is only listed for sm_100a and sm_110a. The new `mma` kinds on consumer Blackwell are all floating point, FP4 included. The 8.7 manual even labels 4-bit `wmma` a preview feature with "no guarantees of backward compatibility on future PTX ISA versions or SM architectures", and the 9.3 manual drops the label.

![What the PTX manual offers per target](images/hint4-progress-report-1/fig05_ptx_targets.png)
*Per target, from the PTX ISA 9.3 manual, plus what I saw in SASS on sm_90.*

The native FP4 paths don't get around it either. They all need architecture-specific `a` or family-specific `f` targets, and the manual is blunt about those: code built for an `a` target "cannot be run on later generation devices", and `f` code only runs within its own family.

Nothing 4-bit, integer or FP4, runs as one native instruction from Ampere to Blackwell, which rules out the thing the first README was named after. My own 3090 does have native INT4 tensor cores, it's everything after Ada that doesn't. HINT4 ended up as 4-bit weights on native integer tensor cores everywhere, with the math done in 8 bits.

## Activations and decode

An 8-bit `mma` wants both operands in INT8, so the activations get quantized to INT8 on the fly, on every call, with their own scales. The products accumulate as INT32, and both sets of float scales get applied around that.

Decode is a different shape. At batch one M is 1, and an `mma` tile wants 16 rows, so fifteen of them would be padding. Small M goes through [DP4A](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#integer-arithmetic-instructions-dp4a) instead, a four-way byte dot product on the regular CUDA cores, so the batch-one path doesn't touch the tensor cores at all.

![HINT4 data path](images/hint4-progress-report-1/fig06_datapath.png)
*The data path, from checkpoint to output.*

## The scales are FP8 too

The block scales are still E4M3, same as NVFP4, and Ampere has no FP8 either. The `cvt` forms that convert E4M3 [need sm_89](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#data-movement-and-conversion-instructions-cvt) or newer, so on the 3090 the compiler inlines a software decode instead, around forty instructions for every scale byte where Ada does it in one. One of my older kernels did that decode inside the K loop, which is about the worst place it could be.

I moved the decode out of the kernels. The scales get decoded once, before inference, and the prepared kernels read them already decoded, without ever converting an FP8 byte.

![FP8 scale decode cost on Ampere](images/hint4-progress-report-1/fig07_fp8_decode.png)
*The same older kernel compiled for sm_86 and sm_89, and where the E4M3 conversions sat in each kernel family before the decode moved out.*

## Does the model still work?

The quantizer I started with is the naive one, round-to-nearest with absmax block scales. The first real test was Kimi-Linear 48B, on an 8×H100 machine because a 48B model doesn't fit on a 3090, and WikiText-2 perplexity went from 6.41 in BF16 to 6.54.

The standard fixes are [GPTQ](https://arxiv.org/abs/2210.17323), [AWQ](https://arxiv.org/abs/2306.00978) and rotation like [QuaRot](https://arxiv.org/abs/2404.00456), and I tried all three. Rotation wasn't drop-in. Kimi-Linear has linear attention with recurrent state, and a rotation only stays exact where you can fold it through without crossing a nonlinearity or the recurrence, so the Kimi port only rotated where that held.

![Kimi-Linear 48B perplexity by preparation](images/hint4-progress-report-1/fig08_kimi_ppl.png)
*Kimi-Linear 48B on WikiText-2, by preparation. The dashed line is BF16.*

Rotation alone made it worse, and adding AWQ on top barely moved it. Which is funny after the NVINT4 paper, where rotation is the whole reason integer wins. My own simulation agreed with the paper, too. On synthetic tensors a Hadamard rotation was worth more than 3 dB of SNR on a heavy-tailed one, more than 5 on one with outlier channels, and nothing at all on a plain Gaussian, since a rotated Gaussian is still Gaussian.

Rotation takes the few huge values that set a block's scale and spreads them across the block, so the grid stops spending its steps on one outlier. It needs a tail to work on, and when I measured Kimi's MoE weights before any rotation, most of them had a kurtosis between 3 and 3.7, barely above a Gaussian's 3.

But why would it hurt, instead of just doing nothing? Reconstruction SNR with and without rotation came out within a few hundredths of a dB, and perplexity and KL both got worse anyway. My guess is the error moved somewhere the model is more sensitive to, but I haven't checked where.

Chen et al. quantize every forward GEMM, activations included, and rotate both sides of each one. These runs kept activations in BF16, so whether rotation helped came down to the geometry of the weights alone.

GPTQ actually helped. It closed about a third of the gap to BF16, which was most of what the full stack managed. An older report of mine said "about 80%" here and mixed up those two denominators, so don't trust that number if you've seen it. GPTQ also needed 128 calibration sequences of 2048 tokens and a bit over two hours on the 8×H100 to build.

## Weights only

I still didn't keep any of it. GPTQ and AWQ need calibration data. Rotation doesn't, but it changes the network instead of just packing the weights. I wanted something that takes a checkpoint and nothing else, so in September I ripped out GPTQ, AWQ, rotation and the calibration APIs, knowing GPTQ had helped.

The old 4-bit MMA kernels, the floating-point comparison kernels and an experimental 2:4 sparse family went out in the same cleanup. I also found a preset with rotation in its name that didn't rotate anything. It had been running as plain group-32 the whole time, and now it raises an error instead.

## What's left to tune

Absmax isn't the lowest-error scale for a block, so the packer tries candidate scales and keeps whichever gives the lowest squared error, using nothing but the weights. E4M3 also rounds the scale itself, and if it rounds down, the block's largest weight gets clipped, so the encoder rounds up when that would happen.

Some blocks fit an evenly spaced INT4 grid better and some fit FP4's uneven one, and it turns out I don't have to pick. Double every E2M1 magnitude and you get 0, 1, 2, 3, 4, 6, 8 and 12, which are just integers, so an FP4 block can go through the same INT8 `mma`, exactly, with a different lookup when the nibbles get widened. E4M3 scales are always positive, so their sign bit is free, and I use it to record which grid each block came from. I call that dual grid.

![The two 4-bit grids on real weights](images/hint4-progress-report-1/fig09_dual_grid.png)
*Two real blocks from the first query projection of Llama-3.2-1B, one where each grid wins. Across that whole tensor, the FP4 grid wins about 40 percent of blocks.*

On Kimi, BBH logical deduction came out far below BF16, and below NVFP4 too. My first guess was that my weights reconstructed worse, so I measured every quantized tensor against BF16, more than 20,000 of them, and mine beat NVFP4's on all but 9. Then what was broken?

I started swapping things back. Put the BF16 weights back into one group of modules, leave everything else quantized, rerun the task, repeat. Putting all the attention weights back recovered nearly the whole gap on the five-object variant, and putting back only the output projection recovered most of it by itself. Storing that one projection as signed bytes, W8, together with the scale and grid changes above, closed the gap on that task.

![Logical deduction swap runs](images/hint4-progress-report-1/fig10_logical_deduction.png)
*Putting one group of Kimi's modules back in BF16 at a time, then the fused kernel before and after the 8-bit output projection.*

Smaller groups also mean lower error, which is why NVFP4 uses 16, but the 8-bit `mma` takes K in chunks of 32, so a scale every 16 weights means splitting every multiply in two.

TL is my way around that. Each pair of 16-weight groups shares one E4M3 scale, and each group gets its own small integer multiplier, one through eight, which gets folded straight into the weight bytes before the multiply. A 4-bit weight times eight still fits in a signed byte, so the math stays exact and one `mma` covers both groups, at the same 4.5 bits per weight as plain group-16. A zero multiplier is reserved to mark an FP4 block, so dual grid still works inside TL.

![TL scale layout](images/hint4-progress-report-1/fig11_tl_layout.png)
*Two 16-weight groups under one shared scale.*

The scales themselves can be compressed too. Classic DQ quantizes the group scales with a small palette plus a second level of scales, which gets classic E4M3 under 4.5 bits. TL-DQ is a different thing despite the name. It's a dictionary over the final TL scale words, and expanding it gives back the exact TL scale stream, byte for byte, so it's lossless with respect to TL while TL itself is still lossy with respect to the model. On Kimi it matched TL exactly with a checkpoint about a gigabyte smaller.

![Stored bits per weight by format](images/hint4-progress-report-1/fig12_bits_per_weight.png)
*Stored bits per weight by format and group size. The diamonds are prepared DQ once it's sitting in GPU memory.*

## Downstream tasks

Up to here I'd been scoring formats on reconstruction error and perplexity, and after logical deduction I didn't trust that much. In August I ran Llama-3.2-1B-Instruct through 19 tasks on an RTX A6000, with four arms: BF16, TL-DQ, classic, and NVFP4A16, the weight-only NVFP4 path. These were August's all-4-bit configurations, from before the current mixed precision policy.

![Llama-3.2-1B four-arm evaluation](images/hint4-progress-report-1/fig13_llama_tasks.png)
*Llama-3.2-1B-Instruct on an A6000, 17 August, with four of the 19 tasks broken out.*

All three quantized arms landed below BF16, and NVFP4A16 had the best quantized average, a third of a point above TL-DQ. Most of that lead comes from IFEval, whose scorer turned out to be nondeterministic when it was rerun, and without IFEval the gap is under a tenth of a point. Per task it goes both ways. TL-DQ was ahead on ARC-Challenge, HellaSwag, BoolQ and GSM8K.

The weird part is the reconstruction numbers. On this model every classic tensor reconstructed better than every NVFP4 tensor, NVFP4's best one was below classic's worst, and NVFP4A16 still beat classic on the average and on six separate downstream measurements across three harnesses. I still rank variants inside one codec family by reconstruction error, but I've stopped trusting it across families.

I don't have paired significance tests for any of this. The aggregate result files survived, and recomputing the means from them matches the report to four decimals, but the per-item outputs didn't.

## Is it faster?

The A6000 shares the 3090's architecture, but I wanted speed numbers from the card this is actually for, so in September I timed 144 isolated matrix multiplies on the 3090 itself, three layer shapes at six values of M for eight methods. At M=1, TL-DQ was about twice as fast as FP16 on all three shapes, which is the decode case.

![FP16 time over TL-DQ time on the 3090](images/hint4-progress-report-1/fig14_dense_heatmap.png)
*FP16 time over TL-DQ time on the 3090. Green means TL-DQ was faster.*

The rest of the table is less fun. At M=8 TL-DQ lost to FP16 on all three shapes, from 32 to 512 it depends on the shape, and by 1024 it's roughly even. Why does M=8 fall below FP16 everywhere when M=1 is twice as fast? I haven't pinned that down. My read on the overall shape is that batch one is waiting on memory, so moving about a quarter of the weight bytes pays off, and past that FP16 on a 3090 is a strong baseline while my kernel still has to unpack weights and quantize activations.

It also looks worse against my own earlier build, where every non-DQ decode cell got slower, by up to 44 percent. Those came from separate campaigns instead of one paired run, so I can't tell you which change did it.

And a matrix multiply benchmark has no attention, KV cache or scheduler in it, so the real answer has to come from the whole-model run.

## Prepared DQ

The raw classic DQ path rebuilds the scales from the palette and the second-level scales inside the kernel, on every single call.

Prepared DQ does that work once, at load time, and keeps a plain FP32 scale plane next to the packed weights. I compared the two paths in the same binary on identical inputs, and prefill came out about 6 to 13 times faster across 54 model-sized cases, with small decode cases slightly faster. Every output matched the raw path bit for bit, both eager and inside CUDA graphs. The preparation itself isn't in those timings.

It costs memory, though. Four bits per weight plus an FP32 scale per group comes to 6 bits per weight at group size 16, 5 at 32 and 4.5 at 64, while the DQ checkpoint on disk is under 4.5 at every group size.

![Prepared DQ speed and memory](images/hint4-progress-report-1/fig15_prepared_dq.png)
*Prepared over raw DQ, one point per case, and what it costs in GPU memory.*

## The call path

With prepared calls, the GPU work got short enough that the Python side of the call started to matter.

The next round of work was all host code. I added an owned handle that keeps its own prepared snapshot, made warm dispatch for DQ faster, cut down the routing work for small MoE batches, and gave quantized activations their own storage. Across 70 comparisons, the time to enqueue a warm call dropped by about 30 to 55 percent, while GPU time inside a captured graph moved less than three percent either way.

![Call path change per cell](images/hint4-progress-report-1/fig16_callpath.png)
*One point per cell, owned prepared API only.*

The older mutable API can't just hold a snapshot, because it still has to track versions, storage, aliases and invalidation. Eight of its cells ended up with 15 host timings that got meaningfully worse, and three large dense cases had a transient peak around 800 KiB higher, with the live bytes unchanged. I kept the change anyway.

## One rounding decision

The next change I kept was much smaller, one rounding decision in the M=1 GEMV.

Quantizing an activation means computing 127·v/s and rounding to an integer. The kernel does that with a fast reciprocal estimate and a multiply, which can land on the wrong side of a midpoint. In this caller the inputs are FP16 and the scales are ordinary positive FP16 values, and the midpoint that matters has a simple test: if 2·|v| equals s, the exact value is 63.5, round-to-nearest-even gives 64, and the helper now checks for exactly that case.

The change is a few lines. Most of the work was checking it. On the CPU I proved it over every FP16 encoding, and on the GPU I compared the new helper with the old one almost a million times, about a third of those against an FP64 reference, without a single mismatch.

![Midpoint helper timing](images/hint4-progress-report-1/fig17_midpoint.png)
*The midpoint helper on four decode cases. The red markers are the host timing flags that stayed.*

In the timing runs, graph latency on four classic group-16 decode cases dropped 6 to 8 percent, under two microseconds each. The host-side timings still had flags in both the original and the confirmation run, including in the controls, so I'm only claiming the GPU side, for this one caller.

## The census

A few lines in one helper still end up in a lot of kernels across six targets, and a change like that can move instructions in kernels I never meant to touch. How would I even notice?

Builds get a census now. I disassemble every entry function for sm_80, 86, 89, 90, 100 and 120 and check each one: no HMMA anywhere, so nothing falls back to half precision, no 4-bit or sparse MMA, and every MMA in the SASS has to match the one I wrote in the PTX, with the same operand types and the same shape.

For the midpoint build, four entries per target changed, the four I meant to change, and every other entry matched the previous build instruction for instruction, control bits included.

![Six-target census](images/hint4-progress-report-1/fig18_census.png)
*The 10 September build on all six targets.*

The census only reads the binaries. The only GPU that has actually run and timed this build is the 3090, and on Blackwell all I have is cubins with the right instructions in them.

I also wanted outputs to match across GPUs, and the instructions alone don't get you that. I made activation rounding exact, pinned the dense schedule to one reference profile that matches the 3090 so a GPU with more SMs can't pick a different K split or reduction order, and fixed the order MoE outputs get combined in. SiLU still goes through the hardware's approximate exponential, though, so I can't promise bit-identical whole-model outputs across GPUs.

## What didn't ship

With the census and paired timing both running, a change could get rejected for being slower or for touching compiled code it had no business touching, and several did.

| Candidate | What happened | Decision |
|---|---|---|
| Two-stripe GEMV | 58 graph regressions in 98 cells | kept the old default |
| Compact DQ, lower prequant threshold | 16 graph, 26 completion, 34 enqueue median losses in 60 cells | kept the old path and threshold |
| Split activation allocation | 2 MiB more reserved memory in 6 of 9 matched histories | rejected |
| Midpoint helper for TL and TL-DQ | median graph time 4.6% better, per-row floors cleared in only 10 of 12 rows, host regressions | rejected |
| Midpoint helper for W8 | 66 protected kernel bodies changed on SM100 and on SM120 | rejected before timing |

The TL version of the midpoint helper came closest. Its median graph time got better, but before the run I'd written down that every affected row had to clear a minimum gain, two rows didn't, and two host timings got worse, so it stayed out.

The W8 version never even got timed. It changed instructions in dozens of kernels on both Blackwell targets that weren't supposed to change at all, which fails the census, so I don't know whether it would have been faster.

## Where the numbers come from

I've been burned by my own numbers on this project. An earlier report of mine republished old results as if I'd just measured them, and the instruction counts in the docs once drifted away from the binary they described.

Every number in this post comes from a saved result file, and the timing tables keep the slow cells next to the build that produced them.

## The evaluator

The 3090 is shared with other jobs, so before a whole-model run can mean anything it needs the card to itself. I started from apaz's [gpumutex](https://github.com/apaz-cli/libgpumutex), which intercepts CUDA initialization and makes processes wait in line for a GPU, and I keep a pinned fork of it that gives up after a bounded wait and checks that its lock files are set up correctly before anything starts. That only keeps well-behaved processes off the card, so the evaluator also holds its own lease on the GPU, and the run goes by that lease.

Each task epoch loads one model and runs the same frozen requests through it twice, as two separately supervised passes. A shard only gets written as a read-only checkpoint once both passes are complete and check out against each other, and scoring happens later, on the CPU, by replaying the task's scorer over the saved responses. If a worker dies, the next epoch checks the chain of checkpoints and picks up after the last complete shard, so anything after that point gets redone but nothing before it ever needs the GPU again. It also means the campaign's progress counter can sit still while checkpointed GPU work piles up underneath it.

![Evaluator flow](images/hint4-progress-report-1/fig19_evaluator_flow.png)
*How a shard becomes a score, and where a crashed run picks back up.*

The live run broke the evaluator a few times:

1. Recovery recomputed a growing prefix of results for every saved shard, so it got slower the longer the run went. Now each row gets derived once.
2. Cold start had to check more than 73,000 saved runtime records, recover the checkpoints and load the model, all under one readiness deadline. Those are separate phases now, each with its own limit, and they keep the same child process and GPU lease the whole way through.
3. The finish check and the CPU replay couldn't always tell a live process from the saved record of a finished one, once systemd had cleaned up the old cgroup or the lock had been renewed.
4. One MMLU document didn't fit. In the 8B BF16 arm, its four answer requests needed 672 KV-cache blocks together and the epoch only had 575, and splitting documents can't help when you're already down to one. At a leaf like that the runner now caps how many requests run at once while still submitting the same frozen requests in one call, and three at a time needed 504 blocks. It restores the normal limit once the engine drains, and checks that both passes agree.

## Where it is right now

As of 5 October 2026, 03:00 UTC.

The plan has 17 configurations, three Llama-3.1-8B-Instruct arms and fourteen Llama-3.2-1B-Instruct arms, and eight of them get the full task suite while the other nine still go through format, perplexity and performance gates.

![Campaign progress snapshot](images/hint4-progress-report-1/fig20_progress.png)
*Accepted work per stage of the plan.*

The 1B TL-DQ default arm has finished both passes on every shard, the 8B BF16 arm is about 40 percent through, and CPU scoring has accepted exactly one shard. Full perplexity, performance, memory and the final comparison haven't run yet.

DQ can only be evaluated as a whole model through Hugging Face directly for now, since vLLM can't load it yet. Kimi doesn't fit in 24 GiB at all, so it's not in the same-card comparison.

When the run finishes, report 2 gets perplexity with exact scored-token counts, task scores from one setup, prefill and decode timings at fixed shapes, and peak memory, all from the same 3090.

## Open questions

A few things I don't know yet:

- Is the 8-bit `mma.sync` fast enough on datacenter Blackwell, where the fast path is `tcgen05` and `.kind::i8` isn't even listed for sm_103a? Nothing here has run on Blackwell yet.
- Is an INT4 fast path for sm_80 through sm_89 worth breaking the one-kernel rule for? It would have to bring 4-bit activations with it, since 4-bit `mma` wants both operands in 4 bits.
- PTX 9.3 added an `mma_throughput` pragma that's "Supported on all target architectures". Does it help these kernels? I haven't tried it.

## Thanks

I did this as part of my RL Residency at [Prime Intellect](https://www.primeintellect.ai/), and I couldn't be more thankful to everyone there for the generous support, the compute and the reviews. Honorable mention to siro [@m_sirovatka](https://x.com/m_sirovatka), xeo [@xeophon](https://x.com/xeophon) and snimu [@omouamoua](https://x.com/omouamoua).
