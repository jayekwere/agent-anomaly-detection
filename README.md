**Anomaly Detection on AI-Agent Access Behavior**
Detecting when an AI agent's access behavior looks anomalous — a sign of a compromised, misconfigured, or misbehaving agent. Built by a security engineer -vulnerability management / technical support on BeyondTrust's Pathfinder identity-security stack, which now governs AI-agent identities) applying ML to a problem adjacent to my day work.

**The honest story (this is the point)**
This project is as much about not fooling yourself as it is about the model.

**Day 1 — the trap.** I generated synthetic agent sessions and injected obvious anomalies (a clean escalate → bulk_export → delete chain) plus a feature that fired only on attacks. Isolation Forest scored ROC-AUC 0.99. That looked great — and meant almost nothing. The model wasn't detecting subtle bad behavior; it was reading a neon sign I'd painted on every attack.

**Day 2 — making it real.** I rewrote the data so anomalies are subtle: only a mildly elevated escalation rate and sensitive actions scattered through an otherwise-normal session. I dropped the giveaway feature and replaced it with matters-of-degree signals (escalation rate, export rate, transition entropy) that also occur in normal traffic. On this fair test the score honestly dropped to ROC-AUC ~0.75, with low precision/recall on the anomaly class and heavily overlapping score distributions.


**That drop is the result.** A 0.75 on a fair problem is worth more than a 0.99 on a rigged one. It shows there's real signal — subtle behavioral anomalies are detectable better than chance — but that simple frequency features and an unsupervised baseline only get you so far. That's a true finding, not a failure.

**What's here**
agent_anomaly_detection.ipynb — the full arc: synthetic data generators (easy + hard), sequence-level feature engineering, Isolation Forest baseline, and honest evaluation comparing both versions.

**Run it**
Open in Google Colab → Run all. No external data; synthetic throughout.

**Honest limitations**

**Synthetic data.** Results demonstrate an approach; they are not real-world performance. The realism of the generator is the main limitation.

**Unsupervised baseline.** Isolation Forest with the true contamination rate supplied — in production you wouldn't know that rate.

**Simple features.** Frequency + a couple of sequence signals; richer transition modeling is unexplored here.

**Next steps (Day 3+)**
Add an autoencoder and compare against Isolation Forest; n-gram transition-probability features; threshold selection without supplying the true anomaly rate; and, ultimately, validation against real (non-synthetic) agent logs.
