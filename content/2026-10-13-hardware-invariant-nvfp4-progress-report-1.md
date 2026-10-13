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
*Progress report 1, with numbers as of 5 October 2026. The whole-model evaluation on the 3090 is still running, so there's no final quality or speed table in here yet, and the code isn't public yet either. Both come with report 2, once the evals are done, and after that the plan is a paper. Some of this will change when the run finishes.*

NVFP4 is NVIDIA's 4-bit floating-point format. Each weight is E2M1, a 4-bit float with two exponent bits and one mantissa bit, so the largest value it can hold is 6. Every block of 16 weights shares an 8-bit E4M3 scale, and the whole tensor gets one FP32 scale on top, which works out to 4.5 bits per weight. Blackwell's tensor cores [run it natively](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/).

![NVFP4 block layout](images/hint4-progress-report-1/fig01_nvfp4_layout.png)
*The NVFP4 layout.*

I wanted it on a 3090. Sadly, I learned at the time that Ampere doesn't have native FP4. The FP4 forms of [`mma`](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#warp-level-matrix-instructions-mma), the PTX instruction that drives the tensor cores, need sm_120a, which is consumer Blackwell. Datacenter Blackwell does FP4 through a different instruction family, and nothing older has it at all.

NVFP4 checkpoints still run on Ampere, weight-only. The kernel unpacks the 4-bit weights into 16-bit floats in registers and does the multiply on the half-precision tensor cores. That path is called NVFP4A16, for NVFP4 weights with 16-bit activations. The weights stay small in memory, but every multiply waits on a decode first.

I assumed that had to be slower than a format the tensor cores understand directly, though I hadn't measured anything yet.

## Integer instead

Ampere does have integer tensor cores, for INT8 and even INT4. My first idea, before I'd read the PTX docs properly, was a straight swap: INT4 wherever NVFP4 has FP4, INT8 wherever FP8 would go, keep the block scales, and run the whole thing on integer `mma`. I figured the integer part of the tensor core would be the part every generation keeps.

Then I found a paper that had already done the numerics. [Chen et al.](https://arxiv.org/abs/2510.25602) define NVINT4, which is NVFP4's exact structure with the E2M1 grid swapped for symmetric INT4, and their abstract says:

> for 4-bit formats, FP (e.g., MXFP4, NVFP4) often holds an accuracy advantage, though we show that NVINT4 can surpass NVFP4 when outlier-mitigation techniques like Hadamard rotation are applied.

Without rotation, NVINT4 lost to NVFP4 on all twelve models they tested. With random Hadamard rotation it won all twelve. Their code only simulates the quantization, and the hardware half of the paper is a gate-level area and energy model of multipliers nobody has built yet. It mostly answers the accuracy question, with a rotation attached, but the hardware argument is about chips that don't exist yet, and I have a 3090. I also don't love the name. NVINT4 sounds like something NVIDIA ships, and it's a format from a paper.

![NVINT4 vs NVFP4 wins out of 12 models](images/hint4-progress-report-1/fig02_nvint4_wins.png)
*From Table 3 of Chen et al.*

Do I emulate, and pay for a decode before every multiply, or go integer and trust that the instructions I need exist on every card I care about?

Integer also fit the other thing I wanted, PTX that compiles to the same native instruction on every GPU generation. I didn't want an `if ampere / elif ada / elif hopper` in every kernel, or a separate copy of each kernel per generation that I'd have to keep in sync by hand. If that works it should be fast, and it's a lot less to maintain. I started calling it hardware-invariant, which is where the H in HINT4 comes from.

## Which integer mma?

PTX has both integer forms, the 4-bit `mma` and the 8-bit one, and [both are legal on anything from sm_80 up](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#warp-level-matrix-instructions-mma). Ampere runs both natively, so the first kernel used the 4-bit one, and on Ampere the SASS, the machine code ptxas actually emits, showed the real 4-bit instruction. My first README even put it in the name, Hardware-Invariant Native INT4 Microscaling, and claimed native INT4 tensor cores on Ampere and everything newer, Hopper included. Then I compiled the same kernel for sm_90 and looked at the SASS.

```
                     sm_80 / sm_86 / sm_89     sm_90
mma m16n8k32 .s4     IMMA.16832.S4.S4  x1      IMMA.16816.S8.S8  x2
mma m16n8k64 .s4     IMMA.16864.S4.S4  x1      IMMA.16832.S8.S8  x2
```

Where did the 4-bit instruction go?

Hopper doesn't have one. IMMA is the integer tensor core instruction, and in these kernels ptxas splits each 4-bit one into two 8-bit ones that each cover half the K dimension, with shifts and LOP3 logic ops in front to sign-extend the nibbles. It still runs on the tensor cores and still gets the right answer, but it isn't the instruction I wrote, and the extra work costs throughput. NVIDIA's own [table of tensor core input types](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html#compute-capabilities-table-tensor-core-data-types-per-compute-capability) agrees. INT4 is there through compute capability 8.9 and gone from Hopper on, and INT8 is there on every row, every Blackwell part included.

![Excerpt of NVIDIA's Table 33](images/hint4-progress-report-1/fig03_table33.png)
*Excerpt from Table 33 of NVIDIA's CUDA programming guide.*

Everything builds on the 8-bit `mma` instead, `mma.sync.aligned.m16n8k32` with signed bytes, which is native on every target I compile for, sm_80 through sm_120. The weights stay 4-bit in memory and get widened to signed bytes in registers right before the multiply. On Hopper, ptxas was doing more or less the same thing anyway. Now it happens in my source, the same way on every target.

Nine days after the first commit, the README title went from Hardware-Invariant Native INT4 Microscaling to Hardware-Invariant Native Integer-Tensor-Core 4-bit Microscaling. It's longer, and it doesn't promise 4-bit math anymore.

![The old 4-bit kernels compiled per target](images/hint4-progress-report-1/fig04_s4_lowering.png)
*The old 4-bit kernels compiled per target. On sm_90 each of the 19 needed between 30 and 95 extra LOP3s.*

After that I mostly trusted NVIDIA's table. This month I finally read the whole PTX ISA manual, both version 9.3 and the 8.7 one that shipped with CUDA 12.8, to see whether anything newer brings 4-bit integer math back.

Nothing does. Hopper's `wgmma` takes 8-bit integers and a 1-bit mode, and no 4-bit. Blackwell's `tcgen05` has one integer kind, `i8`, and the manual only lists it for sm_100a and sm_110a. The new `mma` kinds on consumer Blackwell are all floating point, FP4 included. The 8.7 manual even calls 4-bit `wmma` a preview feature with "no guarantees of backward compatibility on future PTX ISA versions or SM architectures". The 9.3 manual dropped that label.

![What the PTX manual offers per target](images/hint4-progress-report-1/fig05_ptx_targets.png)
*Per target, from the PTX ISA 9.3 manual, plus what I saw in SASS on sm_90.*

The native FP4 paths don't get around this either. They all need architecture-specific `a` targets or family-specific `f` targets. In the manual's words, code built for an `a` target "cannot be run on later generation devices", and `f` code only runs within its own family.

Nothing 4-bit, integer or FP4, runs as one native instruction from Ampere to Blackwell, which means the first README's title was wrong. My own 3090 does have native INT4 tensor cores, it's everything after Ada that doesn't. HINT4 ended up as 4-bit weights on native integer tensor cores everywhere, with the math done in 8 bits.

## Activations and decode

An 8-bit `mma` needs both operands in INT8, so the activations get quantized to INT8 on the fly, on every call, with their own scales. The products accumulate in INT32, and the weight and activation scales get applied to those integer sums.

Decode is different. When you generate one token at a time, the activation matrix has a single row, M=1, and an `mma` tile wants 16 rows, so fifteen of them would be padding. Small M goes through [DP4A](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#integer-arithmetic-instructions-dp4a) instead, a four-way byte dot product on the regular CUDA cores, so the batch-one path doesn't use the tensor cores at all.

![HINT4 data path](images/hint4-progress-report-1/fig06_datapath.png)
*The data path, from checkpoint to output.*

## The scales are FP8 too

The block scales are still E4M3, same as NVFP4, and Ampere has no FP8 either. The `cvt` instructions that convert E4M3 [need sm_89](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#data-movement-and-conversion-instructions-cvt) or newer, so on the 3090 the compiler inlines a software decode instead, around forty instructions per scale byte where Ada does it in one. One of my older kernels did that decode inside the main loop over K, where it costs the most.

I moved the decode out of the kernels. The scales get decoded once, before inference, and the prepared kernels never touch an FP8 byte.

![FP8 scale decode cost on Ampere](images/hint4-progress-report-1/fig07_fp8_decode.png)
*The same older kernel compiled for sm_86 and sm_89, and where the E4M3 conversions sat in each kernel family before the decode moved out.*

## Does the model still work?

The quantizer I started with is the naive one, round-to-nearest with absmax block scales. The first real test was Kimi-Linear 48B on an 8×H100 machine, since a 48B model doesn't fit on a 3090, and WikiText-2 perplexity went from 6.41 in BF16 to 6.54.

The usual fixes are [GPTQ](https://arxiv.org/abs/2210.17323), [AWQ](https://arxiv.org/abs/2306.00978) and rotation like [QuaRot](https://arxiv.org/abs/2404.00456), and I tried all three. Rotation wasn't drop-in. Kimi-Linear has linear attention with recurrent state, and a rotation only stays exact where you can fold it into the neighboring weights without crossing a nonlinearity or the recurrence, so the Kimi port only rotated where that held.

![Kimi-Linear 48B perplexity by preparation](images/hint4-progress-report-1/fig08_kimi_ppl.png)
*Kimi-Linear 48B on WikiText-2, by preparation. The dashed line is BF16.*

Rotation alone made it worse, and adding AWQ on top barely moved it. Which is funny after the NVINT4 paper, where rotation is the whole reason integer wins. My own simulation had agreed with the paper, too. On synthetic tensors a Hadamard rotation was worth more than 3 dB of SNR on a heavy-tailed one, more than 5 on one with outlier channels, and nothing at all on a plain Gaussian, since a rotated Gaussian is still Gaussian.

Rotation takes the few huge values that set a block's scale and spreads them across the block, so the grid stops spending its steps on one outlier. It needs a tail to work on. When I measured Kimi's MoE weights before any rotation, most of them had a kurtosis between 3 and 3.7, and a Gaussian's kurtosis is 3.

Why would it hurt instead of just doing nothing, though? Reconstruction SNR with and without rotation was within a few hundredths of a dB, and perplexity and KL both got worse anyway. My guess is the error moved somewhere the model is more sensitive to, but I haven't checked where.

Chen et al. quantize every matmul in the forward pass, activations included, and rotate both sides of each one. These runs kept activations in BF16, so I think whether rotation helped came down to the geometry of the weights alone.

GPTQ did help. It closed about a third of the gap to BF16, which was most of what the full stack managed. An older report of mine said "about 80%" here because it mixed up those two denominators, so don't trust that number if you've seen it. GPTQ also needed 128 calibration sequences of 2048 tokens and a bit over two hours on the 8×H100.

## Weights only

I didn't keep any of it. GPTQ and AWQ need calibration data, and rotation changes the network instead of just packing the weights. I wanted something that takes a checkpoint and nothing else, so in September I ripped out GPTQ, AWQ, rotation and the calibration code, even though GPTQ had helped.

The old 4-bit MMA kernels, the floating-point comparison kernels and an experimental 2:4 sparse family went out in the same cleanup. I also found a preset with rotation in its name that didn't rotate anything. It had been running as plain group-32 the whole time. Now it raises an error.

## What's left to tune

Absmax isn't the lowest-error scale for a block, so the packer tries a range of candidate scales and keeps whichever gives the lowest squared error, using nothing but the weights. E4M3 also rounds the scale itself. If it rounds down, the block's largest weight gets clipped, so the encoder rounds up in that case.

Some blocks fit an evenly spaced INT4 grid better and some fit FP4's uneven one, and I don't actually have to pick. Double every E2M1 magnitude and you get 0, 1, 2, 3, 4, 6, 8 and 12, which are all integers, so an FP4 block can go through the same INT8 `mma` with no error, just a different lookup when the nibbles get widened. E4M3 scales are always positive, which leaves their sign bit free, and I use it to mark which grid each block came from. I call this dual grid.

![The two 4-bit grids on real weights](images/hint4-progress-report-1/fig09_dual_grid.png)
*Two real blocks from the first query projection of Llama-3.2-1B, one where each grid wins. Across that whole tensor, the FP4 grid wins about 40 percent of blocks.*

On Kimi, BBH logical deduction came out far below BF16, and below NVFP4 too. My first guess was that my weights reconstructed worse, so I measured every quantized tensor against BF16, more than 20,000 of them, and mine beat NVFP4's on all but 9. Then what was broken?

I started swapping things back. Put the BF16 weights back into one group of modules, leave everything else quantized, rerun the task, repeat. Putting all the attention weights back recovered nearly the whole gap on the five-object variant, and putting back only the output projection recovered most of it by itself. Storing that one projection as signed bytes, W8, together with the scale and grid changes above, closed the gap on that task.

![Logical deduction swap runs](images/hint4-progress-report-1/fig10_logical_deduction.png)
*Putting one group of Kimi's modules back in BF16 at a time, then the fused kernel before and after the 8-bit output projection.*

Smaller groups mean lower error, which is why NVFP4 uses 16, and so does classic HINT4, the plain version with one E4M3 scale per 16 INT4 weights. The 8-bit `mma` works through 32 weights at a time along K, though, so a scale every 16 weights means splitting every multiply in two.

TL, for two-level, is how I get around that. Each pair of 16-weight groups shares one E4M3 scale, and each group gets a small integer multiplier from one to eight, which gets folded into the weight bytes before the multiply. A 4-bit weight times eight still fits in a signed byte, so the math stays exact and one `mma` covers both groups, at the same 4.5 bits per weight as classic. Multiplier zero is reserved to mark an FP4 block, so dual grid still works inside TL.

![TL scale layout](images/hint4-progress-report-1/fig11_tl_layout.png)
*Two 16-weight groups under one shared scale.*

The scales themselves can be compressed too. Classic DQ, short for double quantization, quantizes the group scales again with a small palette and a second level of scales, which gets classic under 4.5 bits. TL-DQ is a different thing despite the name. It's a dictionary over the final TL scale words, and expanding it gives back the exact TL scale stream, byte for byte, so it adds no error on top of TL. On Kimi it matched TL exactly with a checkpoint about a gigabyte smaller.

![Stored bits per weight by format](images/hint4-progress-report-1/fig12_bits_per_weight.png)
*Stored bits per weight by format and group size. The diamonds are prepared DQ once it's sitting in GPU memory.*

## Downstream tasks

Up to here I'd been scoring formats on reconstruction error and perplexity, and after logical deduction I didn't trust that much. In August I ran Llama-3.2-1B-Instruct through 19 tasks on an RTX A6000 with four configurations: BF16, TL-DQ, classic, and NVFP4A16. Every layer was 4-bit in those runs, which isn't true of the current default anymore.

![Llama-3.2-1B task results](images/hint4-progress-report-1/fig13_llama_tasks.png)
*Llama-3.2-1B-Instruct on an A6000, 17 August, with four of the 19 tasks broken out.*

All three quantized models landed below BF16, and NVFP4A16 had the best quantized average, a third of a point above TL-DQ. Most of that lead comes from IFEval, whose scorer turned out to be nondeterministic on a rerun, and without IFEval the gap is under a tenth of a point. Per task it goes both ways. TL-DQ was ahead on ARC-Challenge, HellaSwag, BoolQ and GSM8K.

Reconstruction error would have predicted the opposite. On this model NVFP4's best-reconstructed tensor was worse than classic's worst, and NVFP4A16 still beat classic, on the average and on six separate downstream measurements across three harnesses. I still use reconstruction error to rank variants within one format family, but I don't trust it across families anymore.

I can't run paired significance tests on any of this, because only the aggregate result files survived.

## Is it faster?

The A6000 has the same architecture as the 3090, but I wanted speed numbers from the card this is actually for. In September I timed 144 isolated matrix multiplies on the 3090: three layer shapes, six values of M, eight methods. At M=1, the decode case, TL-DQ was about twice as fast as FP16 on all three shapes.

![FP16 time over TL-DQ time on the 3090](images/hint4-progress-report-1/fig14_dense_heatmap.png)
*FP16 time over TL-DQ time on the 3090. Green means TL-DQ was faster.*

The rest of the table is less fun. At M=8 TL-DQ was slower than FP16 on all three shapes, from 32 to 512 it depends on the shape, and by 1024 it's roughly even. Why would M=8 be slower everywhere when M=1 is twice as fast? I don't know yet. My guess is that batch one is waiting on memory, so moving about a quarter of the weight bytes pays off. Past that, FP16 on a 3090 is a strong baseline, and my kernel has to unpack weights and quantize activations on top.

Against my own earlier build it's worse too. Every non-DQ decode case got slower, by up to 44 percent, and the two builds were timed in separate runs instead of side by side, so I can't tell which change did it.

And a matrix multiply benchmark has no attention, KV cache or scheduler in it, so the real answer has to come from the whole-model run.

## Prepared DQ

The raw classic DQ kernels rebuild the scales from the palette and the second-level scales on every single call.

Prepared DQ does that once, at load time, and keeps the decoded scales as plain FP32 next to the packed weights. In the same binary on identical inputs, prefill came out about 6 to 13 times faster across 54 model-sized cases, and small decode cases got slightly faster. Every output matched the raw path bit for bit, both eagerly and inside CUDA graphs. The preparation time itself isn't in those numbers.

It costs memory, though. Four bits per weight plus an FP32 scale per group comes to 6 bits per weight at group size 16, 5 at 32 and 4.5 at 64, while the DQ checkpoint on disk is under 4.5 at every group size.

![Prepared DQ speed and memory](images/hint4-progress-report-1/fig15_prepared_dq.png)
*Prepared over raw DQ, one point per case, and what it costs in GPU memory.*

## The call path

With prepared weights, the GPU work got short enough that the Python side of each call started to show up in the timings.

The next round of work was all host code. I added a handle that owns its own prepared copy of the weights, made warm DQ calls dispatch faster, cut down the routing work for small MoE batches, and gave quantized activations their own buffers. Across 70 comparisons, the time to launch a warm call dropped by about 30 to 55 percent, while GPU time inside a captured CUDA graph moved less than three percent either way.

![Call path change per case](images/hint4-progress-report-1/fig16_callpath.png)
*One point per case, measured on the new handle.*

The older API lets you change weights in place, so it can't just hold a snapshot and still has to track versions, storage, aliases and invalidation. Eight of its cases ended up with 15 host timings that got noticeably worse, and three large dense cases briefly used about 800 KiB more memory at peak. I kept the change anyway.

## One rounding decision

The next change I kept was much smaller, one rounding decision in the batch-one matrix-vector kernel.

Quantizing an activation means computing 127·v/s and rounding to an integer. The kernel does that with a fast reciprocal estimate and a multiply, which can round the wrong way when the exact value sits right on a .5. In this kernel the inputs are FP16 and the scales are ordinary positive FP16 values, and the midpoint that matters has a simple test: if 2·|v| equals s, the exact value is 63.5, round-to-nearest-even gives 64, and the new midpoint helper checks for that case.

The fix itself is a few lines, and most of the time went into checking it. On the CPU I checked every possible FP16 input, and on the GPU I compared the new helper with the old one almost a million times, about a third of those against an FP64 reference, without a single mismatch.

![Midpoint helper timing](images/hint4-progress-report-1/fig17_midpoint.png)
*The midpoint helper on four decode cases. The red markers are host timings that were still flagged as slower.*

In the timing runs, GPU time on four classic group-16 decode cases dropped 6 to 8 percent, under two microseconds each. Some host-side timings were still flagged in both the original and the repeat run, the controls included, so I'm only claiming the GPU side, for this one kernel.

## The census

A few lines in one helper end up compiled into a lot of kernels across six targets, and a change like that can move instructions in kernels I never meant to touch. How would I even notice?

Builds get a census now. I disassemble every kernel for sm_80, 86, 89, 90, 100 and 120 and look at the SASS. HMMA, the half-precision tensor core instruction, can't appear anywhere, so nothing falls back to FP16 math. 4-bit and sparse MMAs can't appear either, and every MMA has to match the one I wrote in the PTX, with the same operand types and shape.

For the midpoint build, four kernels per target changed, the four I meant to change, and every other kernel matched the previous build instruction for instruction, control bits included.

![Six-target census](images/hint4-progress-report-1/fig18_census.png)
*The 10 September build on all six targets.*

The census only reads binaries. The 3090 is the only GPU that has run and timed this build, and for Blackwell all I have is compiled binaries with the right instructions in them.

I also wanted outputs to match across GPUs, and getting the same instructions everywhere isn't enough for that. I made activation rounding exact, pinned the dense kernel schedule to one profile that matches the 3090, so a GPU with more SMs can't pick a different K split or reduction order, and fixed the order MoE outputs get added up in. SiLU still uses the hardware's approximate exponential, though, so I can't promise bit-identical whole-model outputs across GPUs.

## What didn't ship

With the census and side-by-side timing both in place, a change could get rejected for being slower or for changing compiled code it shouldn't have touched, and several did.

| Change | What happened | Decision |
|---|---|---|
| Two-stripe GEMV | slower in 58 of 98 GPU timings | kept the old default |
| Compact DQ, lower prequant threshold | median got worse in 16 to 34 of 60 cases, depending on the timer | kept the old path and threshold |
| Split activation allocation | 2 MiB more reserved memory in 6 of 9 comparisons | rejected |
| Midpoint helper for TL and TL-DQ | 4.6% better median, but 2 of 12 cases missed the minimum gain and some host timings got worse | rejected |
| Midpoint helper for W8 | changed 66 kernels on both Blackwell targets that weren't supposed to change | rejected before timing |

The TL version of the midpoint helper came closest. Before the run I'd written down that every affected case had to clear a minimum gain, and two of the twelve didn't, so it stayed out even with a better median. The W8 version never got timed at all, so I don't know whether it would have been faster.

## Where the numbers come from

My own numbers have been wrong before on this project. An earlier report of mine republished old results as if I'd just measured them, and the instruction counts in the docs once drifted away from the binary they described. Everything measured in this post comes from a saved result file, slow cases included.

## The evaluator

The 3090 is shared with other jobs, so a whole-model run needs the card to itself before its numbers mean anything. I started from apaz's [gpumutex](https://github.com/apaz-cli/libgpumutex), which intercepts CUDA initialization and makes processes wait in line for a GPU. I run a pinned fork of it that gives up after a bounded wait and checks that its lock files are set up correctly before anything starts. That only keeps well-behaved processes off the card, so the evaluator also holds its own lease on the GPU, and the run checks that lease.

Each task run loads one model and sends the same fixed requests through it twice, in two separately supervised passes, and a shard of results only gets saved once both passes finish and agree. Scoring happens later, on the CPU, by replaying each task's scorer over the saved responses. When a worker dies, the next run picks up after the last complete shard, so nothing before that point needs the GPU again. The downside is that the campaign's progress counter can sit still while finished GPU work waits to be scored.

![Evaluator flow](images/hint4-progress-report-1/fig19_evaluator_flow.png)
*How a shard becomes a score, and where a crashed run picks back up.*

The live run broke the evaluator a few times:

1. Recovery recomputed a growing prefix of results for every saved shard, so restarts got slower the longer the run went. Now each result gets computed once.
2. Startup had to check more than 73,000 saved records, recover the checkpoints and load the model, all under one timeout. Those are separate steps now, each with its own limit, and they keep the same process and GPU lease the whole way through.
3. The finish check and the CPU scoring couldn't always tell a live process from the saved record of a finished one, once systemd had cleaned up the old cgroup or the lock had been renewed.
4. One MMLU question didn't fit. In the 8B BF16 run its four answer requests needed 672 blocks of KV cache together and there were only 575, and splitting a batch further can't help when it's already down to one question. For a case like that, the runner now caps how many requests run at once while still sending the same requests in one call. Three at a time needed 504 blocks. It goes back to the normal limit once the engine drains, and checks that both passes still agree.

## Where it is right now

As of 5 October 2026, 03:00 UTC.

The plan covers 17 configurations, 3 of Llama-3.1-8B-Instruct and 14 of Llama-3.2-1B-Instruct. Eight of them get the full set of tasks, and the other nine skip the tasks but still go through the format, perplexity and speed checks.

![Campaign progress snapshot](images/hint4-progress-report-1/fig20_progress.png)
*Accepted work per stage of the plan.*

The 1B TL-DQ run has finished both passes on every shard, the 8B BF16 run is about 40 percent through, and CPU scoring has accepted one shard so far. Full perplexity, speed, memory and the final comparison haven't run yet.

DQ can only be evaluated as a whole model through plain Hugging Face Transformers for now, since vLLM can't load it yet. Kimi doesn't fit in 24 GiB at all, so it isn't part of the same-card comparison.

When the run finishes, report 2 gets perplexity with exact token counts, task scores from one setup, prefill and decode timings at fixed shapes, and peak memory, all from the same 3090.

## Open questions

A few things I don't know yet:

- Is the 8-bit `mma.sync` fast enough on datacenter Blackwell, where the fast path is `tcgen05` and `.kind::i8` isn't even listed for sm_103a? Nothing here has run on Blackwell yet.
- Is a native INT4 path for sm_80 through sm_89 worth breaking the one-kernel rule? It would have to bring 4-bit activations with it, since the 4-bit `mma` wants both operands in 4 bits.
- PTX 9.3 added an `mma_throughput` pragma that's "Supported on all target architectures". Does it help these kernels? I haven't tried it.

## Thanks

I did this as part of my RL Residency at [Prime Intellect](https://www.primeintellect.ai/), and I couldn't be more thankful to everyone there for the generous support, the compute and the reviews. Honorable mention to siro [@m_sirovatka](https://x.com/m_sirovatka), xeo [@xeophon](https://x.com/xeophon) and snimu [@omouamoua](https://x.com/omouamoua).
