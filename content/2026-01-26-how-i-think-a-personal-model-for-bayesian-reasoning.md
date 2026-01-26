Title: Being Wrong Faster
Date: 2026-01-26 10:38:02
Category: misc
Slug: how-i-think-a-personal-model-for-bayesian-reasoning
Image: images/rd7loe.png

Everyone builds a model of the world in their head. Kids do it when they learn that dropped things fall. Adults do it when they pick up a new tool and start predicting what buttons do before pressing them. It's automatic - you observe, you predict, you update.

The interesting part isn't that we do this. It's *what kind of observations* actually improve the model.

Confirmation feels good. You predict something, it happens, you feel smart. But confirmation doesn't teach you much - you already knew that. The observations that actually update your model are the ones where you predict one thing and something else happens. Being wrong is where the information lives.

This leads to a counterintuitive heuristic: **if you want to learn faster, be wrong faster.**

Not wrong on purpose - that's just noise. But deliberately putting yourself in situations that are hard to predict, where your current model is likely to break. For a chef, that might be weird flavor combinations. For a trader, unfamiliar market conditions. The goal is to find the edges of what you understand.

---

## A Case Study

Here's how this played out for me recently.

I was working on rerollouts - regenerating training data with a different model. Before writing code, I made predictions about what would break:

**Prediction 1:** Can't parallelize conversation turns. You'd lose context.
*Result: Correct.*

**Prediction 2:** The model might mess up tool calls. Built a fallback.
*Result: Correct.*

**Prediction 3:** Ray will hang somewhere. Built checkpointing before I needed it.
*Result: Correct. It did hang. Restarted from checkpoint.*

**Prediction 4:** ...didn't make one.
*Result: Some samples had no system prompt. Model hallucinated. Had to add a fallback I hadn't anticipated.*

The predictions I got right were the obvious ones - stuff I already understood. The thing that broke was something I didn't even know to ask about. That's the edge of my model. That's where I learned something.

The checkpointing saved the project. But I didn't build checkpointing because I'm good at predicting - I built it because I assume I'm going to be wrong about *something*, and I'd rather find out cheap.

---

## The Heuristic

The principle generalizes: design for fast feedback on your wrongness.

- Ship small. See what breaks before you've invested too much.
- Build recovery mechanisms (checkpoints, rollbacks, fallbacks) before you need them.
- Treat predictions not as things to defend, but as hypotheses to test.

This is basically [Bayesian reasoning](https://en.wikipedia.org/wiki/Bayesian_inference) - hold beliefs loosely, update on evidence. The only addition is being intentional about *seeking* the evidence that would prove you wrong. That's where the learning is.

---

The goal isn't to be right. It's to be wrong faster.
