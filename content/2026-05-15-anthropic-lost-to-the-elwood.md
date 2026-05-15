Title: Anthropic Lost to the Elwood
Date: 2026-05-15 12:00:00
Category: reverse-engineering
Slug: anthropic-lost-to-the-elwood
Summary: How I built a drop-in replacement for the official Anthropic agent SDK by using Babel AST to instrument the Claude Code CLI bundle directly — no subprocess, no API key, 100% API parity.

*How I scaled the AST techniques from my previous investigation into a full SDK replacement that calls agentLoop in-process — no subprocess spawning, no separate billing, 362 tests passing.*

**Repository:** [github.com/secemp9/elwood](https://github.com/secemp9/elwood)
**npm:** [@secemp/elwood](https://www.npmjs.com/package/@secemp/elwood)

---

## Yet Again, We Meet

Yet again, we see each other. Yes, you — provider-customer mismatch, they call it.

Anyway, if you haven't been living under a rock (or, you know, if you're as terminally online as I am), you've probably heard that Anthropic plans to fiddle with the usage of `claude -p` in general. Probably not disabling it outright, but incurring separate costs or something, I don't know the specifics.

Honestly, I get their agenda, and I'm not here to disparage them or litigate the decision. I thought I'd do something more productive with my time instead. You know, like scaling what I did in my [last blog post](https://secemp.blog/2026/01/29/anthropic-doesnt-know-how-to-yield/) and building a replacement with close parity to the official Anthropic SDK.

Enter **elwood**.

---

## What I Did Then vs. Now

The way I envisioned this is pretty in-line with the previous blog. If you read that one you'd have the full context, but let me summarize the progression:

In the last post, I used Babel AST scripting to split and instrument a minified 11MB bundle — different AST-level tricks to deeply understand the UI freezing and performance issues, and provide concrete fixes that worked for me at the time on the version I was working with.

However.

A thought came to mind: "oh, but the official Anthropic SDK (`@anthropic-ai/claude-agent-sdk`) is just calling the installed Claude Code binary through subprocess and depending on IPC JSON streaming... but

![we can scale this](/images/sunglasses-meme.png)

...we can scale this."

Indeed we can. By using Babel AST to instrumentalize the *entire* stack that gets called and used by the official SDK, and by directly importing the functions, methods, and classes from the installed Claude Code "binary" (if you can even call it that — it's not compiled, it's just minified JavaScript, eh).

This doesn't just unlock faster usage since there's no subprocess overhead. You also unlock the plethora of everything else the Claude Code binary has to offer — the full `agentLoop`, the permission system, the MCP transport layer, session management, all of it. Running in-process.

---

## How It Works

The official `@anthropic-ai/claude-agent-sdk` works like this: you call `query()`, it spawns `claude -p` as a child process, and then streams JSON back and forth over stdin/stdout via IPC. Your code talks to a subprocess. The subprocess talks to the API.

Elwood removes the subprocess entirely. Here's what happens when you call `query()`:

1. **Locate** the installed Claude Code CLI (`cli.js` — that 13MB bundle)
2. **Parse** the entire bundle into an AST with Babel
3. **Fingerprint** internal functions via evidence-based pattern matching (looking for `agentLoop`, `appStateFactory`, `permissionChecker`, etc.)
4. **Inject** instrumentation hooks — additive, non-destructive, single-pass
5. **Import** the instrumented bundle and call `agentLoop()` directly in-process

The instrumentation is key. Every injection is a conditional expression that no-ops when hooks aren't installed, so the bundle behaves identically to the original unless you wire up hooks. Original AST nodes are wrapped, never replaced.

### The Code Comparison

Here's what the official SDK looks like:

```js
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "What files are in this directory?",
  options: { allowedTools: ["Bash", "Glob"] }
})) {
  if ("result" in message) console.log(message.result);
}
```

Here's elwood:

```js
import { query } from "@secemp/elwood";

for await (const message of query({
  prompt: "What files are in this directory?",
  options: { allowedTools: ["Bash", "Glob"], maxTurns: 3 }
})) {
  if ("result" in message) console.log(message.result);
}
```

Same API. Same `for await` loop. Same message shape. No subprocess. No separate API key needed if you're logged in via `claude login` (Pro/Max subscription works).

The full API surface is there — `query()`, `tool()`, `createSdkMcpServer()`, hooks (`PreToolUse`, `PostToolUse`, etc.), session resume/continue/fork, MCP servers (stdio, HTTP, SDK transport), subagents, permission modes, the V2 session API. All of it.

---

## The Numbers

- **362 tests** passing across query parity, hooks, MCP behavioral tests, and gap-fix validations
- **24 working examples** — direct equivalents of every official SDK example (basic queries, hooks, MCP, custom tools, session stores, subagents, V2 sessions)
- **100% API parity** with `@anthropic-ai/claude-agent-sdk` — same function signatures, same message types, same options
- Works with **all auth methods**: subscription (`claude login`), `ANTHROPIC_API_KEY`, OAuth, Bedrock, Vertex, Foundry

Install:

```bash
npm install @secemp/elwood
```

That's it. If Claude Code is installed globally, elwood finds it automatically.

---

## Try It, Break It, Tell Me

I included a bunch of examples in the [repo](https://github.com/secemp9/elwood). If you find issues, or something doesn't work for your case, let me know. I intend on accepting PRs and issues as needed.

---

## The Bigger Point

I want to be clear here. This isn't just me doing this out of frustration as usual (I do my best work when I'm frustrated or angry, for some reason). It's also a testament that the way they handled this is definitely questionable.

Not just because me or anyone else can circumvent it. But even if circumventing becomes harder, they need to understand that making Claude Code truly open source might be better long-term — just like OpenAI did with Codex. The competitive landscape is real. Cursor and Windsurf are growing, we have Gravity, OpenAI fully supports alternative agents through their subscription services. The moat was never in the tools.

Because at the end of the day, and as I said before:

***"if it can be executed, then it can be parsed"***

So it's mostly a cat and mouse game, and thus, a waste of time on both sides.

---

*Previous post: [Anthropic Doesn't Know How to Yield](https://secemp.blog/2026/01/29/anthropic-doesnt-know-how-to-yield/)*
